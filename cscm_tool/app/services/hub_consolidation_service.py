"""Hub Controller -> Main Controller consolidation (I-36, assumption A-008 in 03-srs.md).

If the Hub Controller leaves the hardware setup, its codes are defined anew on the Main
Controller side. This supports that move **without renumbering anything**:

1. "Create MC draft from this HC code" - copies the descriptive fields into a new Draft in a
   chosen Main Controller group/subgroup. The new MC number is allocated at Submit for Review
   like for any code; the HC identifier is kept as the legacy reference; a mapping row links
   the two. The draft is an ordinary CR (type NEW) with the full governance cycle.
2. The mapping report - every HC code, its replacement and how far that replacement is.
3. Bulk deprecation - once an HC code's replacement is Released, a deprecation request
   ("replaced by StCd-...") can be opened for all such codes of a Hub group at once; each is
   again an ordinary deprecation CR needing review and approval.

Hub groups are ordinary data throughout (`lookup_functional_system_group.controller_type =
'HUB'`); when every HC code is deprecated an Administrator retires the group in Lookup
Administration."""

from app.domain.authz import require_roles
from app.domain.errors import DomainError, InvalidTransitionError, NotFoundError
from app.extensions import db
from app.models.change_request import ChangeRequest
from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup
from app.models.operations import HubMcMapping
from app.models.status_code import StatusCode, StatusCodeRevision
from app.repositories.status_code_repository import StatusCodeRepository
from app.services.audit_service import AuditService
from app.services.lookup_service import LookupService
from app.services.status_code_service import (
    StatusCodeService,
    ValidationFailed,
    _revision_snapshot,
    revision_to_data,
)
from app.utils import utcnow_iso

_repo = StatusCodeRepository()
_LIVE = ("RELEASED", "APPROVED")


def _label(code: StatusCode) -> str:
    return code.status_code_identifier or f"draft #{code.id}"


class HubConsolidationService:
    @staticmethod
    def hub_groups() -> list[LookupFunctionalSystemGroup]:
        return (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(LookupFunctionalSystemGroup.controller_type == "HUB")
            .order_by(LookupFunctionalSystemGroup.sort_order)
            .all()
        )

    @staticmethod
    def main_groups() -> list[LookupFunctionalSystemGroup]:
        return (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(
                LookupFunctionalSystemGroup.controller_type == "MAIN",
                LookupFunctionalSystemGroup.is_active == 1,
            )
            .order_by(LookupFunctionalSystemGroup.sort_order)
            .all()
        )

    @staticmethod
    def create_mc_draft(
        hub_status_code_id: int, group_id: int, subgroup_id: int, actor
    ) -> tuple[StatusCodeRevision, HubMcMapping]:
        require_roles(actor, "ADMINISTRATOR", "ENGINEER")
        hub = _repo.get_or_404(hub_status_code_id)
        if hub.functional_system_group.controller_type != "HUB":
            raise DomainError("This is not a Hub Controller code.")
        if db.session.query(HubMcMapping).filter_by(hub_status_code_id=hub.id).first():
            raise InvalidTransitionError("This Hub Controller code already has an MC replacement.")
        base = _repo.get_latest_revision_in_states(hub.id, ("RELEASED", "APPROVED"))
        if base is None:
            raise InvalidTransitionError(
                "Only an Approved or Released Hub Controller code can be carried over."
            )
        try:
            group = LookupService.get_by_id(LookupFunctionalSystemGroup, group_id)
            subgroup = LookupService.get_by_id(LookupFunctionalSubgroup, subgroup_id)
        except ValueError as exc:
            raise ValidationFailed([{"field": "functional_subgroup", "message": str(exc)}]) from exc
        if group.controller_type != "MAIN":
            raise ValidationFailed(
                [{"field": "functional_system_group", "message": "Choose a Main Controller group."}]
            )
        if subgroup.functional_system_group_id != group.id:
            raise ValidationFailed(
                [
                    {
                        "field": "functional_subgroup",
                        "message": "Subgroup does not belong to the selected group.",
                    }
                ]
            )

        data = revision_to_data(base)
        data["functional_system_group"] = group.id
        data["functional_subgroup"] = subgroup.id
        data["legacy_reference_number"] = hub.status_code_identifier
        data["justification"] = (
            f"Replaces Hub Controller code {hub.status_code_identifier} "
            f"(Hub -> Main Controller consolidation, A-008)."
        )
        revision = StatusCodeService._build_revision(
            data, actor, is_sandbox=False, status_code_id=None, revision_number=1
        )
        db.session.add(
            ChangeRequest(
                status_code_revision_id=revision.id,
                cr_type="NEW",
                requested_by=actor.id,
                justification=data["justification"],
                state="DRAFT",
            )
        )
        mapping = HubMcMapping(
            hub_status_code_id=hub.id,
            mc_status_code_id=revision.status_code_id,
            created_by=actor.id,
            created_at=utcnow_iso(),
        )
        db.session.add(mapping)
        AuditService.log(
            "StatusCode",
            revision.status_code_id,
            "HUB_MC_DRAFT_CREATE",
            actor=actor,
            after={**_revision_snapshot(revision), "replaces": hub.status_code_identifier},
        )
        db.session.commit()
        return revision, mapping

    @staticmethod
    def mapping_report(group_id: int | None = None) -> dict:
        """Every Hub code with the state of its replacement."""
        query = (
            db.session.query(StatusCode)
            .join(
                LookupFunctionalSystemGroup,
                LookupFunctionalSystemGroup.id == StatusCode.functional_system_group_id,
            )
            .filter(
                LookupFunctionalSystemGroup.controller_type == "HUB", StatusCode.is_sandbox == 0
            )
        )
        if group_id is not None:
            query = query.filter(StatusCode.functional_system_group_id == group_id)
        rows, tally = [], {"OPEN": 0, "MAPPED_DRAFT": 0, "MAPPED_LIVE": 0, "HUB_RETIRED": 0}
        for hub in query.order_by(StatusCode.status_code_identifier, StatusCode.id):
            current = _repo.get_current_revision(hub.id)
            if current is None:
                continue
            mapping = db.session.query(HubMcMapping).filter_by(hub_status_code_id=hub.id).first()
            mc = db.session.get(StatusCode, mapping.mc_status_code_id) if mapping else None
            mc_revision = _repo.get_current_revision(mc.id) if mc else None
            if current.lifecycle_status in ("DEPRECATED", "ARCHIVED"):
                state = "HUB_RETIRED"
            elif mc is None:
                state = "OPEN"
            elif mc_revision is not None and mc_revision.lifecycle_status == "RELEASED":
                state = "MAPPED_LIVE"
            else:
                state = "MAPPED_DRAFT"
            tally[state] += 1
            rows.append(
                {
                    "hub_status_code_id": hub.id,
                    "hub_identifier": hub.status_code_identifier,
                    "hub_title": current.title,
                    "hub_lifecycle": current.lifecycle_status,
                    "legacy_reference_number": hub.legacy_reference_number,
                    "mc_status_code_id": mc.id if mc else None,
                    "mc_identifier": mc.status_code_identifier if mc else None,
                    "mc_lifecycle": mc_revision.lifecycle_status if mc_revision else None,
                    "state": state,
                }
            )
        total = sum(tally.values())
        return {
            "total": total,
            "tally": tally,
            "ready_to_retire": total > 0
            and tally["OPEN"] == 0
            and tally["MAPPED_DRAFT"] == 0
            and tally["MAPPED_LIVE"] == 0,
            "items": rows,
        }

    @staticmethod
    def request_hub_deprecation(group_id: int, actor) -> dict:
        """Open deprecation requests for every Released Hub code of the group whose MC
        replacement is Released. Each is an ordinary DEPRECATION CR."""
        require_roles(actor, "ADMINISTRATOR")
        group = db.session.get(LookupFunctionalSystemGroup, group_id)
        if group is None:
            raise NotFoundError("Functional System Group not found")
        if group.controller_type != "HUB":
            raise DomainError("This is not a Hub Controller group.")
        created, skipped = [], []
        for item in HubConsolidationService.mapping_report(group_id)["items"]:
            label = item["hub_identifier"] or f"#{item['hub_status_code_id']}"
            if item["state"] != "MAPPED_LIVE":
                reason = {
                    "OPEN": "no MC replacement yet",
                    "MAPPED_DRAFT": "the MC replacement is not Released yet",
                    "HUB_RETIRED": "already deprecated",
                }.get(item["state"], item["state"])
                skipped.append({"hub_identifier": label, "reason": reason})
                continue
            if item["hub_lifecycle"] != "RELEASED":
                skipped.append(
                    {"hub_identifier": label, "reason": f"state is {item['hub_lifecycle']}"}
                )
                continue
            try:
                StatusCodeService.create_deprecation_request(
                    item["hub_status_code_id"],
                    f"Replaced by {item['mc_identifier']} "
                    "(Hub -> Main Controller consolidation, A-008).",
                    item["mc_status_code_id"],
                    actor,
                    acknowledge_dependants=True,
                )
            except (DomainError, ValidationFailed) as exc:
                db.session.rollback()
                skipped.append({"hub_identifier": label, "reason": str(exc)})
            else:
                created.append(label)
        AuditService.log(
            "LookupFunctionalSystemGroup",
            group.id,
            "HUB_BULK_DEPRECATION",
            actor=actor,
            after={"created": len(created), "skipped": len(skipped)},
        )
        db.session.commit()
        return {"created": created, "skipped": skipped}

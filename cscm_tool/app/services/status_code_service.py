"""Status Code creation and lifecycle. FR-020-FR-029, FR-053-FR-056, BR-001-BR-003.

Every non-sandbox creation also creates a wrapping ChangeRequest (FR-030);
sandbox creation deliberately does not (docs/08-system-architecture.md §5.4
sequence diagram shows no ChangeRequest in the sandbox create/delete path —
sandbox codes bypass the governance workflow entirely by design)."""

from app.domain.errors import (
    DomainError,
    InvalidTransitionError,
    NotFoundError,
    SegregationOfDutiesViolation,
)
from app.extensions import db
from app.models.change_request import ChangeRequest
from app.models.lookup import (
    LookupAccessRights,
    LookupAlarmBehaviour,
    LookupAvailabilityGroup,
    LookupBrakeProgram,
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
    LookupOperationalState,
    LookupResetProgram,
    LookupStatusCategory,
    LookupTurbinePlatform,
)
from app.models.status_code import StatusCode, StatusCodeRevision, StatusCodeRevisionPlatform
from app.repositories.status_code_repository import StatusCodeRepository
from app.services.audit_service import AuditService
from app.services.lookup_service import LookupService
from app.services.numbering_service import NumberingService
from app.services.validation import validate_revision_fields
from app.utils import utcnow_iso

VIEWER_VISIBLE_STATES = ("APPROVED", "RELEASED", "DEPRECATED", "ARCHIVED")


class ValidationFailed(DomainError):
    def __init__(self, field_errors: list[dict]):
        super().__init__("Validation failed")
        self.field_errors = field_errors


class StatusCodeService:
    _repo = StatusCodeRepository()

    @staticmethod
    def create_draft(data: dict, actor_user) -> StatusCodeRevision:
        """FR-020: Engineer or Administrator creates a new Status Code as a
        Draft revision. No identifier is assigned (FR-021); a wrapping
        ChangeRequest (cr_type=NEW) is created alongside it (FR-030)."""
        revision = StatusCodeService._build_revision(
            data, actor_user, is_sandbox=False, status_code_id=None, revision_number=1
        )
        status_code = revision.status_code

        cr = ChangeRequest(
            status_code_revision_id=revision.id,
            cr_type="NEW",
            requested_by=actor_user.id,
            justification=data.get("justification"),
            state="DRAFT",
        )
        db.session.add(cr)

        AuditService.log(
            "StatusCode",
            status_code.id,
            "CREATE",
            actor=actor_user,
            after=_revision_snapshot(revision),
        )
        db.session.commit()
        return revision

    @staticmethod
    def create_revision(status_code_id: int, data: dict, actor_user) -> StatusCodeRevision:
        """Opens a new Draft revision (copy-on-write) against an existing
        code (FR-025). BR-003: rejected if an open revision already exists."""
        status_code = StatusCodeService._repo.get_or_404(status_code_id)
        if StatusCodeService._repo.get_open_revision(status_code_id) is not None:
            raise InvalidTransitionError(
                "An open Draft/Review/PendingApproval revision already exists (BR-003)."
            )

        next_number = max((r.revision_number for r in status_code.revisions), default=0) + 1
        revision = StatusCodeService._build_revision(
            data,
            actor_user,
            is_sandbox=bool(status_code.is_sandbox),
            status_code_id=status_code_id,
            revision_number=next_number,
        )

        cr = ChangeRequest(
            status_code_revision_id=revision.id,
            cr_type="REVISION",
            requested_by=actor_user.id,
            justification=data.get("justification"),
            state="DRAFT",
        )
        db.session.add(cr)

        AuditService.log(
            "StatusCode",
            status_code.id,
            "CREATE",
            actor=actor_user,
            after=_revision_snapshot(revision),
        )
        db.session.commit()
        return revision

    @staticmethod
    def create_sandbox(data: dict, actor_user) -> StatusCodeRevision:
        """FR-053: Administrator-only. Identifier is allocated immediately
        (not deferred to Submit-for-Review) from the isolated StCd-T#####
        band; no ChangeRequest is created."""
        revision = StatusCodeService._build_revision(
            data, actor_user, is_sandbox=True, status_code_id=None, revision_number=1
        )
        status_code = revision.status_code
        status_code.status_code_identifier = NumberingService.allocate_next_sandbox_identifier()

        AuditService.log(
            "StatusCode",
            status_code.id,
            "SANDBOX_CREATE",
            actor=actor_user,
            after={
                **_revision_snapshot(revision),
                "status_code_identifier": status_code.status_code_identifier,
            },
        )
        db.session.commit()
        return revision

    @staticmethod
    def update_draft(revision_id: int, data: dict, actor_user) -> StatusCodeRevision:
        """FR-024/FR-025: unlimited saves while Draft; rejected outside
        Draft (the DB trigger trg_prevent_edit_locked_revision is
        defense-in-depth for the locked states; DRAFT itself needs an
        explicit application-level check since the trigger doesn't cover
        it). Accepts the same field set as creation.

        Note: docs/artifacts/openapi.yaml's StatusCodeRevisionUpdate schema
        lists only `expected_updated_at` for optimistic concurrency, but
        status_code_revision has no updated_at/version column in
        docs/artifacts/schema.sql to back that check — so it is accepted
        (for forward API compatibility) but not currently enforced. Adding
        real optimistic concurrency needs its own schema migration."""
        revision = db.session.get(StatusCodeRevision, revision_id)
        if revision is None:
            raise NotFoundError(f"Revision {revision_id} not found")
        if revision.lifecycle_status != "DRAFT":
            raise InvalidTransitionError("Only a Draft revision may be edited in place (FR-025).")
        if revision.created_by != actor_user.id and actor_user.role_code != "ADMINISTRATOR":
            raise SegregationOfDutiesViolation(
                "Only the owning Engineer or an Administrator may edit this Draft."
            )

        field_errors = validate_revision_fields(data)
        if field_errors:
            raise ValidationFailed(field_errors)

        before = _revision_snapshot(revision)
        _apply_revision_fields(revision, data)
        if data.get("turbine_platforms") is not None:
            _set_platforms(revision, data["turbine_platforms"])

        AuditService.log(
            "StatusCodeRevision",
            revision.id,
            "EDIT",
            actor=actor_user,
            before=before,
            after=_revision_snapshot(revision),
        )
        db.session.commit()
        return revision

    @staticmethod
    def get_current_revision(status_code_id: int, actor_user) -> StatusCodeRevision:
        revision = StatusCodeService._repo.get_current_revision(status_code_id)
        if revision is None or not StatusCodeService._is_visible(revision, actor_user):
            raise NotFoundError(f"Status Code {status_code_id} not found")
        return revision

    @staticmethod
    def list_revision_history(status_code_id: int, actor_user) -> list[StatusCodeRevision]:
        status_code = StatusCodeService._repo.get_or_404(status_code_id)
        return [r for r in status_code.revisions if StatusCodeService._is_visible(r, actor_user)]

    @staticmethod
    def search(actor_user, **filters) -> tuple[list[StatusCodeRevision], int]:
        visible_states = VIEWER_VISIBLE_STATES if actor_user.role_code == "VIEWER" else None
        return StatusCodeService._repo.search_current_revisions(
            visible_lifecycle_statuses=visible_states, **filters
        )

    @staticmethod
    def preview_next_identifier(
        functional_system_group_code: str, functional_subgroup_code: str | None
    ) -> str:
        group = LookupService.get_by_code(LookupFunctionalSystemGroup, functional_system_group_code)
        subgroup_id = None
        if functional_subgroup_code:
            subgroup_id = LookupService.get_by_code(
                LookupFunctionalSubgroup, functional_subgroup_code
            ).id
        return NumberingService.preview_next_identifier(group.id, subgroup_id)

    @staticmethod
    def delete_sandbox(status_code_id: int, actor_user) -> None:
        """FR-055/FR-056: permanently delete a sandbox code, writing a
        SANDBOX_DELETE audit entry with a full pre-delete snapshot in the
        same transaction. trg_prevent_nonsandbox_delete is defense-in-depth
        if this service-layer check is ever bypassed."""
        status_code = StatusCodeService._repo.get_or_404(status_code_id)
        if not status_code.is_sandbox:
            raise DomainError("Only sandbox status codes may be deleted (FR-055).")

        snapshot = {
            "status_code_identifier": status_code.status_code_identifier,
            "functional_system_group": status_code.functional_system_group.code,
            "revisions": [_revision_snapshot(r) for r in status_code.revisions],
        }
        AuditService.log(
            "StatusCode", status_code.id, "SANDBOX_DELETE", actor=actor_user, before=snapshot
        )
        for revision in list(status_code.revisions):
            db.session.query(StatusCodeRevisionPlatform).filter(
                StatusCodeRevisionPlatform.status_code_revision_id == revision.id
            ).delete()
            db.session.delete(revision)
        db.session.delete(status_code)
        db.session.commit()

    @staticmethod
    def _is_visible(revision: StatusCodeRevision, actor_user) -> bool:
        """BR-009: Draft/Review/PendingApproval data is hidden from Viewers."""
        if actor_user.role_code == "VIEWER":
            return revision.lifecycle_status in VIEWER_VISIBLE_STATES
        return True

    @staticmethod
    def _build_revision(
        data: dict,
        actor_user,
        *,
        is_sandbox: bool,
        status_code_id: int | None,
        revision_number: int,
    ) -> StatusCodeRevision:
        if is_sandbox and actor_user.role_code != "ADMINISTRATOR":
            raise SegregationOfDutiesViolation("Only an Administrator may create a sandbox code.")

        field_errors = validate_revision_fields(data)
        if field_errors:
            raise ValidationFailed(field_errors)

        group = LookupService.get_by_code(
            LookupFunctionalSystemGroup, data["functional_system_group"]
        )
        subgroup = None
        subgroup_code = data.get("functional_subgroup")
        if subgroup_code:
            subgroup = LookupService.get_by_code(LookupFunctionalSubgroup, subgroup_code)
            if subgroup.functional_system_group_id != group.id:
                raise ValidationFailed(
                    [
                        {
                            "field": "functional_subgroup",
                            "message": "Subgroup does not belong to the selected Functional Group.",
                        }
                    ]
                )

        now = utcnow_iso()
        if status_code_id is None:
            status_code = StatusCode(
                functional_system_group_id=group.id,
                functional_subgroup_id=subgroup.id if subgroup else None,
                is_sandbox=1 if is_sandbox else 0,
                owner_id=actor_user.id,
                created_at=now,
            )
            db.session.add(status_code)
            db.session.flush()
        else:
            existing = db.session.get(StatusCode, status_code_id)
            if existing is None:
                raise NotFoundError(f"Status Code {status_code_id} not found")
            status_code = existing

        revision = StatusCodeRevision(
            status_code_id=status_code.id,
            revision_number=revision_number,
            is_current=1,
            owner_id=actor_user.id,
            lifecycle_status="DRAFT",
            created_by=actor_user.id,
            created_at=now,
        )
        _apply_revision_fields(revision, data)
        db.session.add(revision)
        db.session.flush()
        _set_platforms(revision, data.get("turbine_platforms") or [])
        return revision


def _apply_revision_fields(revision: StatusCodeRevision, data: dict) -> None:
    revision.title = data["title"]
    revision.description = data["description"]
    revision.status_category_id = LookupService.get_by_code(
        LookupStatusCategory, data["status_category"]
    ).id
    revision.availability_group_id = LookupService.get_by_code(
        LookupAvailabilityGroup, data["availability_group"]
    ).id
    revision.brake_program_id = LookupService.get_by_code(
        LookupBrakeProgram, data.get("brake_program", "BP-NONE")
    ).id
    revision.reset_program_id = LookupService.get_by_code(
        LookupResetProgram, data["reset_program"]
    ).id
    revision.software_version = data["software_version"]
    revision.operational_state_id = LookupService.get_by_code(
        LookupOperationalState, data["operational_state"]
    ).id
    # SEC-013/FR-025a: Engineer-proposed here; only authoritative once the
    # Administrator's Review sign-off confirms it (see change_request_service).
    revision.access_rights_id = LookupService.get_by_code(
        LookupAccessRights, data.get("access_rights", "SERVICE")
    ).id
    revision.delay_before_alarm_seconds = data.get("delay_before_alarm_seconds", 0)
    revision.delay_before_reset_seconds = data.get("delay_before_reset_seconds", 0)
    revision.alarm_behaviour_id = LookupService.get_by_code(
        LookupAlarmBehaviour, data["alarm_behaviour"]
    ).id


def _set_platforms(revision: StatusCodeRevision, platform_codes: list[str]) -> None:
    db.session.query(StatusCodeRevisionPlatform).filter(
        StatusCodeRevisionPlatform.status_code_revision_id == revision.id
    ).delete()
    for code in platform_codes:
        platform = LookupService.get_by_code(LookupTurbinePlatform, code)
        db.session.add(
            StatusCodeRevisionPlatform(
                status_code_revision_id=revision.id, turbine_platform_id=platform.id
            )
        )


def _revision_snapshot(revision: StatusCodeRevision) -> dict:
    return {
        "title": revision.title,
        "description": revision.description,
        "status_category": revision.status_category.code,
        "lifecycle_status": revision.lifecycle_status,
        "turbine_platforms": sorted(p.turbine_platform.code for p in revision.platforms),
    }

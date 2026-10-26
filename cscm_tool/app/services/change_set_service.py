"""Change sets (I-11): the CRs that ship with one controller software release, shown and
queued together so reviewers see the whole package and the Chief Engineer can work
through it in one sitting.

This bundles *presentation and queueing only*. A bulk action calls the ordinary
single-CR decision service once per CR, so every CR still gets its own segregation-of-
duties check, its own comment, its own audit entry and - for the sign-offs - its own
step-up password check. A CR the actor may not decide (for instance one they wrote)
is reported as skipped with the reason; it never blocks the others."""

from app.domain.errors import DomainError, ForbiddenError, NotFoundError
from app.extensions import db
from app.models.change_request import ChangeRequest, ChangeSet
from app.models.lookup import LookupControllerSoftwareVersion
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.bulk_service import BulkService
from app.services.change_request_service import ChangeRequestService
from app.services.sla_service import SlaService
from app.utils import utcnow_iso

_OPEN_STATES = ("DRAFT", "REVIEW", "PENDING_APPROVAL")
_STEP_STATE = {"reviewer": "REVIEW", "admin": "REVIEW", "chief-engineer": "PENDING_APPROVAL"}


class ChangeSetService:
    @staticmethod
    def create(name: str, description: str | None, software_version, actor) -> ChangeSet:
        if actor.role_code not in ("ADMINISTRATOR", "ENGINEER", "CHIEF_ENGINEER"):
            raise ForbiddenError("SEC-010: your role cannot create change sets.")
        name = (name or "").strip()
        if not 1 <= len(name) <= 120:
            raise ValueError("A change set needs a name of 1-120 characters.")
        if db.session.query(ChangeSet).filter(ChangeSet.name == name).first():
            raise DomainError(f"A change set named '{name}' already exists.")
        version_id = None
        if software_version not in (None, ""):
            query = db.session.query(LookupControllerSoftwareVersion)
            version = (
                query.get(int(software_version))
                if str(software_version).isdigit()
                else query.filter(LookupControllerSoftwareVersion.code == software_version).first()
            )
            if version is None:
                raise ValueError("Unknown controller software version.")
            version_id = version.id
        change_set = ChangeSet(
            name=name,
            description=(description or "").strip() or None,
            target_software_version_id=version_id,
            created_by=actor.id,
            created_at=utcnow_iso(),
        )
        db.session.add(change_set)
        db.session.flush()
        AuditService.log(
            "ChangeSet", change_set.id, "CHANGE_SET_CREATE", actor=actor, after={"name": name}
        )
        db.session.commit()
        return change_set

    @staticmethod
    def get(change_set_id: int) -> ChangeSet:
        change_set = db.session.get(ChangeSet, change_set_id)
        if change_set is None:
            raise NotFoundError("Change set not found")
        return change_set

    @staticmethod
    def list_all() -> list[ChangeSet]:
        return db.session.query(ChangeSet).order_by(ChangeSet.id.desc()).all()

    @staticmethod
    def add_cr(change_set_id: int, cr_id: int, actor) -> ChangeSet:
        change_set = ChangeSetService.get(change_set_id)
        cr = db.session.get(ChangeRequest, cr_id)
        if cr is None:
            raise NotFoundError("Change request not found")
        if actor.id != cr.requested_by and actor.role_code != "ADMINISTRATOR":
            raise ForbiddenError("Only the author of the CR or an Administrator may group it.")
        if change_set.status != "OPEN":
            raise DomainError("The change set is closed.")
        if cr.revision.lifecycle_status not in _OPEN_STATES:
            raise DomainError("Only a CR that is still open can join a change set.")
        if cr.change_set_id not in (None, change_set.id):
            raise DomainError(f"The CR already belongs to change set #{cr.change_set_id}.")
        cr.change_set_id = change_set.id
        AuditService.log(
            "ChangeSet", change_set.id, "CHANGE_SET_ADD_CR", actor=actor, after={"cr_id": cr.id}
        )
        db.session.commit()
        return change_set

    @staticmethod
    def remove_cr(change_set_id: int, cr_id: int, actor) -> ChangeSet:
        change_set = ChangeSetService.get(change_set_id)
        cr = db.session.get(ChangeRequest, cr_id)
        if cr is None or cr.change_set_id != change_set.id:
            raise NotFoundError("The CR is not part of this change set")
        if actor.id != cr.requested_by and actor.role_code != "ADMINISTRATOR":
            raise ForbiddenError("Only the author of the CR or an Administrator may ungroup it.")
        cr.change_set_id = None
        AuditService.log(
            "ChangeSet", change_set.id, "CHANGE_SET_REMOVE_CR", actor=actor, after={"cr_id": cr.id}
        )
        db.session.commit()
        return change_set

    @staticmethod
    def close(change_set_id: int, actor) -> ChangeSet:
        if actor.role_code != "ADMINISTRATOR":
            raise ForbiddenError("SEC-010: only an Administrator closes a change set.")
        change_set = ChangeSetService.get(change_set_id)
        if change_set.status != "CLOSED":
            change_set.status = "CLOSED"
            change_set.closed_at = utcnow_iso()
            AuditService.log("ChangeSet", change_set.id, "CHANGE_SET_CLOSE", actor=actor)
            db.session.commit()
        return change_set

    @staticmethod
    def overview(change_set_id: int) -> dict:
        """The package at a glance: each CR with its state and SLA, plus a tally."""
        change_set = ChangeSetService.get(change_set_id)
        thresholds = SlaService.thresholds()
        rows = []
        tally: dict[str, int] = {}
        for cr in change_set.change_requests:
            revision = cr.revision
            tally[revision.lifecycle_status] = tally.get(revision.lifecycle_status, 0) + 1
            rows.append(
                {
                    "cr": cr,
                    "identifier": revision.status_code.status_code_identifier,
                    "title": revision.title,
                    "state": revision.lifecycle_status,
                    "sla": SlaService.info(cr, thresholds=thresholds),
                }
            )
        return {"change_set": change_set, "rows": rows, "tally": tally}

    @staticmethod
    def bulk_decide(
        change_set_id: int,
        step: str,
        decision: str,
        comment: str | None,
        actor,
        reauth_password: str | None,
        cr_ids: list[int] | None = None,
        sample_id: int | None = None,
    ) -> list[dict]:
        """Decide several CRs of the set in one sitting. `step` is reviewer, admin or
        chief-engineer. Each CR goes through its own service call (see module docstring)."""
        if step not in _STEP_STATE:
            raise ValueError("step must be reviewer, admin or chief-engineer")
        change_set = ChangeSetService.get(change_set_id)
        # FR-180: more than a handful of codes need a passed sample inspection first
        sample = None
        if decision == "APPROVE":
            try:
                eligible = BulkService.eligible(change_set, step, actor, None, cr_ids)
            except ForbiddenError:
                eligible = []  # the single-CR checks report it per code
            sample = BulkService.require_sample(sample_id, change_set, step, actor, eligible)
        # One password check for the whole sitting; a wrong password counts once and aborts.
        AuthService.step_up(actor, reauth_password, f"BULK_{step.upper()}_DECISION")
        if sample is not None:
            comment = ((comment or "") + BulkService.sample_note(sample)).strip()
        wanted = set(cr_ids) if cr_ids else None
        results = []
        for cr in list(change_set.change_requests):
            if wanted is not None and cr.id not in wanted:
                continue
            if cr.revision.lifecycle_status != _STEP_STATE[step]:
                results.append(
                    {"cr_id": cr.id, "ok": False, "message": "Not waiting for this step."}
                )
                continue
            revision = cr.revision
            if (step == "reviewer" and revision.reviewer_signoff_by is not None) or (
                step == "admin" and revision.admin_signoff_by is not None
            ):
                results.append(
                    {"cr_id": cr.id, "ok": False, "message": "Already signed off for this step."}
                )
                continue
            try:
                if step == "reviewer":
                    ChangeRequestService.reviewer_signoff(
                        cr.id, actor, decision, comment, reauth_password=reauth_password
                    )
                elif step == "admin":
                    ChangeRequestService.admin_signoff(
                        cr.id, actor, decision, comment, reauth_password=reauth_password
                    )
                else:
                    ChangeRequestService.chief_engineer_decide(
                        cr.id, actor, decision, comment, reauth_password=reauth_password
                    )
            except (DomainError, ValueError) as exc:
                db.session.rollback()
                results.append({"cr_id": cr.id, "ok": False, "message": str(exc)})
            else:
                results.append({"cr_id": cr.id, "ok": True, "message": "Decision recorded."})
        BulkService._close(
            change_set, "BULK_DECISION", actor, results, sample, step=step, decision=decision
        )
        return results

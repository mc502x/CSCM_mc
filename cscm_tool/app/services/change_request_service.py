"""Implements the submit -> dual-review -> Chief-Engineer-approval workflow.
See docs/05-governance-handbook.md §7-8, BR-004/BR-005, and the sequence
diagrams in docs/08-system-architecture.md §5.1-5.3."""

from app.domain.errors import InvalidTransitionError, SegregationOfDutiesViolation
from app.extensions import db
from app.models.change_request import ChangeRequest
from app.models.status_code import StatusCodeRevisionPlatform
from app.repositories.change_request_repository import ChangeRequestRepository
from app.services.audit_service import AuditService
from app.services.domain_signoff_service import DomainSignoffService
from app.services.numbering_service import NumberingService
from app.utils import utcnow_iso


class ChangeRequestService:
    """Implements docs/05-governance-handbook.md §7-8, BR-004/BR-005."""

    _repo = ChangeRequestRepository()

    @staticmethod
    def submit(cr_id: int, actor) -> ChangeRequest:
        """FR-031: Draft -> Review. Allocates the identifier (FR-021) and
        requires all Cross-Domain Sign-Offs (FR-029) and at least one
        Turbine Platform (FR-023a) first."""
        cr = ChangeRequestService._repo.get_or_404(cr_id)
        revision = cr.revision
        status_code = revision.status_code

        if actor.id != cr.requested_by:
            raise SegregationOfDutiesViolation("Only the requesting Engineer may submit this CR.")
        if revision.lifecycle_status != "DRAFT":
            raise InvalidTransitionError(
                f"Cannot submit a revision in state {revision.lifecycle_status}"
            )
        if not revision.platforms:
            raise ValueError(
                "At least one Turbine Platform is required before Submit for Review (FR-023a)."
            )

        DomainSignoffService.assert_all_required_domains_signed(cr, actor.engineering_domain_codes)

        identifier = NumberingService.allocate_next_identifier(
            status_code.functional_system_group_id, status_code.functional_subgroup_id
        )
        status_code.status_code_identifier = identifier
        revision.lifecycle_status = "REVIEW"
        cr.state = "REVIEW"
        cr.submitted_at = utcnow_iso()

        AuditService.log(
            "StatusCodeRevision",
            revision.id,
            "SUBMIT_FOR_REVIEW",
            actor=actor,
            after={"status_code_identifier": identifier},
        )
        db.session.commit()
        return cr

    @staticmethod
    def reviewer_signoff(cr_id: int, actor, decision: str, comment: str | None) -> ChangeRequest:
        """FR-033."""
        return ChangeRequestService._dual_signoff(cr_id, actor, decision, comment, role="REVIEWER")

    @staticmethod
    def admin_signoff(cr_id: int, actor, decision: str, comment: str | None) -> ChangeRequest:
        """FR-034: approving also confirms the Engineer-proposed
        access_rights value (SEC-013) — nothing to do here beyond the
        sign-off itself, since the proposed value is already what's stored;
        admin_signoff_at becoming non-null IS the confirmation per
        docs/06-data-dictionary.md §2."""
        return ChangeRequestService._dual_signoff(cr_id, actor, decision, comment, role="ADMIN")

    @staticmethod
    def _dual_signoff(
        cr_id: int, actor, decision: str, comment: str | None, role: str
    ) -> ChangeRequest:
        """`role` is "REVIEWER" or "ADMIN" — a label for decision/audit
        codes (docs/12-audit-compliance.md §2: ADMIN_SIGNOFF, not
        ADMINISTRATOR_SIGNOFF), independent of the RBAC role name
        ("ADMINISTRATOR") already checked by the route decorator."""
        cr = ChangeRequestService._repo.get_or_404(cr_id)
        revision = cr.revision

        if actor.id == cr.requested_by:
            raise SegregationOfDutiesViolation("BR-005: cannot sign off own change request.")
        if revision.lifecycle_status != "REVIEW":
            raise InvalidTransitionError(
                f"Cannot sign off a revision in state {revision.lifecycle_status}"
            )
        if decision == "REJECT" and not comment:
            raise ValueError("Rejection requires a comment.")

        decision_code = f"{role}_APPROVE" if decision == "APPROVE" else f"{role}_REJECT"
        ChangeRequestService._repo.add_comment(
            cr,
            author=actor,
            text=comment or "Approved with no additional comment.",
            decision=decision_code,
        )

        before_status = revision.lifecycle_status
        if decision == "REJECT":
            ChangeRequestService._repo.clear_review_signoffs(revision)
            revision.lifecycle_status = "DRAFT"
            cr.state = "DRAFT"
        else:
            now = utcnow_iso()
            if role == "REVIEWER":
                revision.reviewer_signoff_by, revision.reviewer_signoff_at = actor.id, now
                other_signed = revision.admin_signoff_by is not None
            else:
                revision.admin_signoff_by, revision.admin_signoff_at = actor.id, now
                other_signed = revision.reviewer_signoff_by is not None
            if other_signed:
                revision.lifecycle_status = "PENDING_APPROVAL"
                cr.state = "PENDING_APPROVAL"

        AuditService.log(
            "StatusCodeRevision",
            revision.id,
            f"{role}_SIGNOFF",
            actor=actor,
            before={"lifecycle_status": before_status},
            after={"lifecycle_status": revision.lifecycle_status},
        )
        db.session.commit()
        return cr

    @staticmethod
    def chief_engineer_decide(
        cr_id: int, actor, decision: str, comment: str | None
    ) -> ChangeRequest:
        """FR-036/FR-037: actor must not be the requester, Reviewer
        sign-off, or Administrator sign-off on this CR (BR-005)."""
        cr = ChangeRequestService._repo.get_or_404(cr_id)
        revision = cr.revision

        blocked = {cr.requested_by, revision.reviewer_signoff_by, revision.admin_signoff_by}
        if actor.id in blocked:
            raise SegregationOfDutiesViolation(
                "BR-005: segregation of duties across all three decision points."
            )
        if revision.lifecycle_status != "PENDING_APPROVAL":
            raise InvalidTransitionError(
                f"Cannot decide a revision in state {revision.lifecycle_status}"
            )
        if decision == "REJECT" and not comment:
            raise ValueError("Rejection requires a comment.")

        decision_code = (
            "CHIEF_ENGINEER_APPROVE" if decision == "APPROVE" else "CHIEF_ENGINEER_REJECT"
        )
        ChangeRequestService._repo.add_comment(
            cr,
            author=actor,
            text=comment or "Approved with no additional comment.",
            decision=decision_code,
        )

        if decision == "APPROVE":
            revision.chief_engineer_approved_by = actor.id
            revision.chief_engineer_approval_date = utcnow_iso()
            revision.lifecycle_status = "APPROVED"
            cr.state = "APPROVED"
        else:
            ChangeRequestService._repo.clear_review_signoffs(revision)
            revision.lifecycle_status = "DRAFT"
            cr.state = "DRAFT"

        cr.chief_engineer_decided_by = actor.id
        cr.chief_engineer_decided_at = utcnow_iso()

        AuditService.log(
            "StatusCodeRevision",
            revision.id,
            decision_code,
            actor=actor,
            before={"lifecycle_status": "PENDING_APPROVAL"},
            after={"lifecycle_status": revision.lifecycle_status},
        )
        db.session.commit()
        return cr

    @staticmethod
    def add_comment(cr_id: int, actor, text: str) -> ChangeRequest:
        """FR-038: a plain comment, no decision, at any stage."""
        cr = ChangeRequestService._repo.get_or_404(cr_id)
        ChangeRequestService._repo.add_comment(cr, author=actor, text=text, decision=None)
        AuditService.log("ChangeRequest", cr.id, "COMMENT", actor=actor)
        db.session.commit()
        return cr

    @staticmethod
    def withdraw(cr_id: int, actor) -> None:
        """FR-026. Deletes the withdrawn Draft/Review/PendingApproval
        revision and its wrapping CR. The status_code row itself is never
        deleted, even for a withdrawn NEW-type CR that leaves it with zero
        revisions: `trg_prevent_nonsandbox_delete` (docs/artifacts/schema.sql)
        unconditionally blocks deleting any non-sandbox status_code, and
        status_code_identifier is still NULL at this point (an unsubmitted
        NEW-type CR never allocated one), so nothing is actually consumed —
        the orphaned row is harmless and invisible to search (which joins on
        a current revision that no longer exists). A withdrawn REVISION-type
        CR against an existing code simply leaves that code's prior
        `is_current` revision untouched."""
        cr = ChangeRequestService._repo.get_or_404(cr_id)
        revision = cr.revision

        if actor.id != cr.requested_by:
            raise SegregationOfDutiesViolation("Only the requesting Engineer may withdraw this CR.")
        if revision.lifecycle_status not in ("DRAFT", "REVIEW", "PENDING_APPROVAL"):
            raise InvalidTransitionError(
                f"Cannot withdraw a CR in state {revision.lifecycle_status}"
            )

        AuditService.log("ChangeRequest", cr.id, "WITHDRAW", actor=actor)

        ChangeRequestService._repo.delete_with_children(cr)
        db.session.query(StatusCodeRevisionPlatform).filter(
            StatusCodeRevisionPlatform.status_code_revision_id == revision.id
        ).delete()
        db.session.delete(revision)
        db.session.commit()

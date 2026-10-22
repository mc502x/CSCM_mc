"""Implements the submit -> dual-review -> Chief-Engineer-approval workflow.
See docs/05-governance-handbook.md §7-8, BR-004/BR-005, and the sequence
diagrams in docs/08-system-architecture.md §5.1-5.3."""

from app.domain.authz import require_roles
from app.domain.errors import InvalidTransitionError, SegregationOfDutiesViolation
from app.extensions import db
from app.models.change_request import ChangeRequest, ReviewComment
from app.models.status_code import StatusCodeRevision, StatusCodeRevisionPlatform
from app.models.user import User
from app.repositories.change_request_repository import ChangeRequestRepository
from app.services.audit_service import AuditService
from app.services.domain_signoff_service import DomainSignoffService
from app.services.numbering_service import NumberingService
from app.services.status_code_service import apply_access_overrides
from app.utils import utcnow_iso


class ChangeRequestService:
    """Implements docs/05-governance-handbook.md §7-8, BR-004/BR-005."""

    _repo = ChangeRequestRepository()

    @staticmethod
    def submit(
        cr_id: int,
        actor,
        identifier_override: str | None = None,
        override_reason: str | None = None,
    ) -> ChangeRequest:
        """FR-031: Draft -> Review. Allocates the identifier (FR-021) and
        requires all Cross-Domain Sign-Offs (FR-029) and at least one
        Turbine Platform (FR-023a) first. FR-021a: an Administrator may
        instead supply `identifier_override` for a documented
        migration/reservation case; a reason is mandatory and logged."""
        require_roles(actor, "ADMINISTRATOR", "ENGINEER")
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

        if status_code.status_code_identifier is not None:
            # BR-001 / FR-021: allocated exactly once. A CR that was rejected
            # back to Draft (or a new revision of an existing code) keeps the
            # identifier it already has.
            if identifier_override:
                raise ValueError(
                    "FR-021a: this status code already has an identifier; it cannot be overridden."
                )
            identifier = status_code.status_code_identifier
        elif identifier_override:
            if actor.role_code != "ADMINISTRATOR":
                raise SegregationOfDutiesViolation(
                    "FR-021a: only an Administrator may override the identifier."
                )
            if not (override_reason or "").strip():
                raise ValueError("FR-021a: an identifier override requires a documented reason.")
            identifier = NumberingService.validate_manual_identifier(
                identifier_override,
                status_code.functional_system_group_id,
                status_code.functional_subgroup_id,
            )
        else:
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
        if identifier_override:
            AuditService.log(
                "StatusCode",
                status_code.id,
                "IDENTIFIER_OVERRIDE",
                actor=actor,
                after={"status_code_identifier": identifier, "reason": override_reason},
            )
        db.session.commit()
        return cr

    @staticmethod
    def reviewer_signoff(cr_id: int, actor, decision: str, comment: str | None) -> ChangeRequest:
        """FR-033."""
        require_roles(actor, "REVIEWER")
        return ChangeRequestService._dual_signoff(cr_id, actor, decision, comment, role="REVIEWER")

    @staticmethod
    def admin_signoff(
        cr_id: int,
        actor,
        decision: str,
        comment: str | None,
        access_overrides: dict | None = None,
    ) -> ChangeRequest:
        """FR-034 / SEC-013 / BR-012: approving confirms the eight
        Engineer-proposed audience-access fields (admin_signoff_at becoming
        non-null IS the confirmation, docs/06-data-dictionary.md §2), and
        `access_overrides` lets the Administrator change any of them in the
        same atomic action. Overrides are ignored on a rejection, which
        sends the revision back to the Engineer anyway."""
        require_roles(actor, "ADMINISTRATOR")
        return ChangeRequestService._dual_signoff(
            cr_id, actor, decision, comment, role="ADMIN", access_overrides=access_overrides
        )

    @staticmethod
    def _dual_signoff(
        cr_id: int,
        actor,
        decision: str,
        comment: str | None,
        role: str,
        access_overrides: dict | None = None,
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
        if decision not in ("APPROVE", "REJECT"):
            raise ValueError("decision must be APPROVE or REJECT.")
        if decision == "REJECT" and not comment:
            raise ValueError("Rejection requires a comment.")
        if (
            role == "REVIEWER"
            and cr.assigned_reviewer_id is not None
            and cr.assigned_reviewer_id != actor.id
        ):
            raise SegregationOfDutiesViolation(
                "FR-039: this change request is assigned to a different Reviewer."
            )

        access_before: dict = {}
        access_after: dict = {}
        if role == "ADMIN" and decision == "APPROVE" and access_overrides:
            access_before, access_after = apply_access_overrides(revision, access_overrides)

        decision_code = f"{role}_APPROVE" if decision == "APPROVE" else f"{role}_REJECT"
        recorded = ChangeRequestService._repo.add_comment(
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
            before={
                "lifecycle_status": before_status,
                **{f"override:{k}": v for k, v in access_before.items()},
            },
            after={
                "lifecycle_status": revision.lifecycle_status,
                "comment_id": recorded.id,
                "comment": recorded.comment_text,
                **{f"override:{k}": v for k, v in access_after.items()},
            },
        )
        db.session.commit()
        return cr

    @staticmethod
    def chief_engineer_decide(
        cr_id: int, actor, decision: str, comment: str | None
    ) -> ChangeRequest:
        """FR-036/FR-037: actor must not be the requester, Reviewer
        sign-off, or Administrator sign-off on this CR (BR-005)."""
        require_roles(actor, "CHIEF_ENGINEER")
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
        recorded = ChangeRequestService._repo.add_comment(
            cr,
            author=actor,
            text=comment or "Approved with no additional comment.",
            decision=decision_code,
        )

        if decision == "APPROVE":
            revision.chief_engineer_approved_by = actor.id
            revision.chief_engineer_approval_date = utcnow_iso()
            # DEPRECATION-type CRs (docs/05-governance-handbook.md §5:
            # Released -> Deprecated via the full cycle) land on DEPRECATED
            # rather than APPROVED — deprecation is a terminal decision, not
            # a step toward Release.
            revision.lifecycle_status = "DEPRECATED" if cr.cr_type == "DEPRECATION" else "APPROVED"
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
            after={
                "lifecycle_status": revision.lifecycle_status,
                "comment_id": recorded.id,
                "comment": recorded.comment_text,
            },
        )
        if decision == "APPROVE" and cr.cr_type == "DEPRECATION":
            # Distinct DEPRECATE entry (docs/12-audit-compliance.md §2) is
            # the timestamp source StatusCodeService.archive() relies on for
            # the minimum-retention-period check (BR-006) — there is no
            # deprecated_at column on status_code_revision.
            AuditService.log(
                "StatusCodeRevision",
                revision.id,
                "DEPRECATE",
                actor=actor,
                after={
                    "deprecated_reason": revision.deprecated_reason,
                    "superseded_by_status_code_id": revision.superseded_by_status_code_id,
                },
            )
        db.session.commit()
        return cr

    @staticmethod
    def assign_reviewer(cr_id: int, reviewer_id: int | None, actor) -> ChangeRequest:
        """FR-039: an Administrator assigns, reassigns or (reviewer_id=None)
        unassigns the Reviewer for a CR that has not yet been decided.
        An assigned CR can only be signed off by that Reviewer."""
        require_roles(actor, "ADMINISTRATOR")
        cr = ChangeRequestService._repo.get_or_404(cr_id)
        if cr.revision.lifecycle_status not in ("DRAFT", "REVIEW"):
            raise InvalidTransitionError(
                f"Cannot reassign a Reviewer in state {cr.revision.lifecycle_status}"
            )
        if cr.revision.reviewer_signoff_by is not None:
            raise InvalidTransitionError("The Reviewer has already signed off this CR.")

        if reviewer_id is not None:
            reviewer = db.session.get(User, reviewer_id)
            if reviewer is None or not reviewer.is_active or reviewer.role.code != "REVIEWER":
                raise ValueError("reviewer_id must be an active user with the Reviewer role.")
            if reviewer.id == cr.requested_by:
                raise SegregationOfDutiesViolation(
                    "BR-005: the author cannot be assigned as Reviewer."
                )

        before = cr.assigned_reviewer_id
        cr.assigned_reviewer_id = reviewer_id
        AuditService.log(
            "ChangeRequest",
            cr.id,
            "REVIEWER_ASSIGN",
            actor=actor,
            before={"assigned_reviewer_id": before},
            after={"assigned_reviewer_id": reviewer_id},
        )
        db.session.commit()
        return cr

    @staticmethod
    def decision_history(status_code_id: int, actor) -> list[dict]:
        """Every comment and decision on every change request of a status code, oldest
        first, with the CR and revision it belongs to. Review discussion is
        working-role data (BR-009), so Viewers get nothing."""
        require_roles(actor, "ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")
        rows = (
            db.session.query(ReviewComment, ChangeRequest, StatusCodeRevision)
            .join(ChangeRequest, ReviewComment.change_request_id == ChangeRequest.id)
            .join(
                StatusCodeRevision, ChangeRequest.status_code_revision_id == StatusCodeRevision.id
            )
            .filter(StatusCodeRevision.status_code_id == status_code_id)
            .order_by(ReviewComment.created_at, ReviewComment.id)
            .all()
        )
        return [
            {
                "when": comment.created_at,
                "cr_id": cr.id,
                "cr_type": cr.cr_type,
                "revision_number": revision.revision_number,
                "author_id": comment.author_id,
                "decision": comment.decision,
                "comment": comment.comment_text,
            }
            for comment, cr, revision in rows
        ]

    @staticmethod
    def add_comment(cr_id: int, actor, text: str) -> ChangeRequest:
        """FR-038: a plain comment, no decision, at any stage."""
        require_roles(actor, "REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER")
        text = (text or "").strip()
        if not text or len(text) > 4000:
            raise ValueError("A comment must be between 1 and 4000 characters.")
        cr = ChangeRequestService._repo.get_or_404(cr_id)
        recorded = ChangeRequestService._repo.add_comment(
            cr, author=actor, text=text, decision=None
        )
        AuditService.log(
            "ChangeRequest",
            cr.id,
            "COMMENT",
            actor=actor,
            after={"comment_id": recorded.id, "comment": recorded.comment_text},
        )
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
        (or DEPRECATION-type) CR against an existing code restores that
        code's prior revision to is_current=1, since opening the withdrawn
        revision (copy-on-write in _build_revision) had flipped it off."""
        require_roles(actor, "ADMINISTRATOR", "ENGINEER")
        cr = ChangeRequestService._repo.get_or_404(cr_id)
        revision = cr.revision

        if actor.id != cr.requested_by:
            raise SegregationOfDutiesViolation("Only the requesting Engineer may withdraw this CR.")
        if revision.lifecycle_status not in ("DRAFT", "REVIEW", "PENDING_APPROVAL"):
            raise InvalidTransitionError(
                f"Cannot withdraw a CR in state {revision.lifecycle_status}"
            )

        prior_revision = None
        if revision.revision_number > 1:
            prior_revision = (
                db.session.query(StatusCodeRevision)
                .filter(
                    StatusCodeRevision.status_code_id == revision.status_code_id,
                    StatusCodeRevision.revision_number == revision.revision_number - 1,
                )
                .one_or_none()
            )

        # Withdrawing deletes the CR and its comment rows, so the review
        # discussion is preserved in the (append-only) audit entry instead.
        AuditService.log(
            "ChangeRequest",
            cr.id,
            "WITHDRAW",
            actor=actor,
            before={
                "revision_id": revision.id,
                "revision_number": revision.revision_number,
                "title": revision.title,
                "status_code_identifier": revision.status_code.status_code_identifier,
                "lifecycle_status": revision.lifecycle_status,
                "comments": [
                    {
                        "id": c.id,
                        "author_id": c.author_id,
                        "decision": c.decision,
                        "comment": c.comment_text,
                        "at": c.created_at,
                    }
                    for c in cr.comments
                ],
                "domain_signoffs": [
                    {
                        "domain": d.engineering_domain.code,
                        "by": d.signed_off_by,
                        "at": d.signed_off_at,
                    }
                    for d in cr.domain_signoffs
                ],
            },
        )

        ChangeRequestService._repo.delete_with_children(cr)
        db.session.query(StatusCodeRevisionPlatform).filter(
            StatusCodeRevisionPlatform.status_code_revision_id == revision.id
        ).delete()
        db.session.delete(revision)
        if prior_revision is not None:
            # ux_revision_current_per_code allows only one is_current=1 row
            # per status_code; flush the deletion above before restoring it.
            db.session.flush()
            prior_revision.is_current = 1
        db.session.commit()

"""Field-level review comments and review checklists (I-23).

* A Reviewer, Administrator or Chief Engineer comments on one specific field while a
  CR is in Review or Pending Approval; the author sees the open comments inline on
  the Draft once the CR is sent back, and marks them resolved.
* An Administrator maintains a review checklist per Functional System Group (or for
  all groups). A Reviewer approving a CR must confirm every active item that applies;
  the wording confirmed is stored with the sign-off, so later edits of the checklist
  never rewrite history. With no checklist items configured nothing changes."""

from app.domain.errors import ForbiddenError, InvalidTransitionError, NotFoundError
from app.extensions import db
from app.models.change_request import (
    ChangeRequest,
    CrChecklistConfirmation,
    FieldComment,
    ReviewChecklistItem,
)
from app.services.audit_service import AuditService
from app.utils import utcnow_iso

COMMENTABLE_FIELDS = (
    "functional_subgroup",
    "turbine_platforms",
    "legacy_reference_number",
    "title",
    "description",
    "software_version",
    "status_category",
    "available_group",
    "alarm_flag",
    "set_delay",
    "reset_delay",
    "up_down_counter",
    "trigger_snapshot",
    "loadless_spinning_permitted",
    "number_of_times_repeated",
    "repeated_over_the_course",
    "status_code_for_repeated_error",
    "yaw_program",
    "manual_reset_program",
    "auto_reset_program",
    "converter_reactive_power_program",
    "brake_program",
    "umrichterprogramm_gsc",
    "umrichterprogramm_msc",
    "yaw_bearing_lubrication_program",
    "development_access",
    "sales_access",
    "tcc_access",
    "service_access",
    "turbine_operator_package_access",
    "grid_operator_access",
    "service_partner_access",
    "customer_access",
    "remedy_text",
    "affected_component",
    "related_status_codes",
    "standard_references",
    "applies_from_version",
    "applies_to_version",
    "planned_effective_date",
    "planned_deprecation_date",
)

_COMMENT_STATES = ("REVIEW", "PENDING_APPROVAL")


def _can_comment(actor) -> bool:
    return any(actor.can_act_as(r) for r in ("REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER"))


class FieldReviewService:
    # ------------------------------------------------------------ field comments
    @staticmethod
    def add_field_comment(cr_id: int, field_name: str, text: str, actor) -> FieldComment:
        if not _can_comment(actor):
            raise ForbiddenError("SEC-010: only reviewing roles may comment on a field.")
        cr = db.session.get(ChangeRequest, cr_id)
        if cr is None:
            raise NotFoundError("Change request not found")
        if field_name not in COMMENTABLE_FIELDS:
            raise ValueError(f"'{field_name}' is not a reviewable field.")
        text = (text or "").strip()
        if not text or len(text) > 2000:
            raise ValueError("A field comment must be between 1 and 2000 characters.")
        if cr.revision.lifecycle_status not in _COMMENT_STATES:
            raise InvalidTransitionError(
                "Field comments can be added while the CR is in Review or Pending Approval."
            )
        comment = FieldComment(
            change_request_id=cr.id,
            field_name=field_name,
            author_id=actor.id,
            comment_text=text,
            created_at=utcnow_iso(),
        )
        db.session.add(comment)
        db.session.flush()
        AuditService.log(
            "ChangeRequest",
            cr.id,
            "FIELD_COMMENT",
            actor=actor,
            after={"comment_id": comment.id, "field": field_name, "comment": text},
        )
        db.session.commit()
        return comment

    @staticmethod
    def list_field_comments(cr_id: int, only_open: bool = False) -> list[FieldComment]:
        query = db.session.query(FieldComment).filter(FieldComment.change_request_id == cr_id)
        if only_open:
            query = query.filter(FieldComment.resolved_at.is_(None))
        return query.order_by(FieldComment.id).all()

    @staticmethod
    def open_comments_by_field(cr_id: int) -> dict[str, list[FieldComment]]:
        grouped: dict[str, list[FieldComment]] = {}
        for comment in FieldReviewService.list_field_comments(cr_id, only_open=True):
            grouped.setdefault(comment.field_name, []).append(comment)
        return grouped

    @staticmethod
    def resolve_field_comment(comment_id: int, actor) -> FieldComment:
        comment = db.session.get(FieldComment, comment_id)
        if comment is None:
            raise NotFoundError("Comment not found")
        cr = db.session.get(ChangeRequest, comment.change_request_id)
        if cr is None:
            raise NotFoundError("Change request not found")
        allowed = (
            actor.id in (comment.author_id, cr.requested_by) or actor.role_code == "ADMINISTRATOR"
        )
        if not allowed:
            raise ForbiddenError(
                "Only the commenter, the author of the CR or an Administrator may "
                "resolve a comment."
            )
        if comment.resolved_at is None:
            comment.resolved_by = actor.id
            comment.resolved_at = utcnow_iso()
            AuditService.log(
                "ChangeRequest",
                cr.id,
                "FIELD_COMMENT_RESOLVE",
                actor=actor,
                after={"comment_id": comment.id, "field": comment.field_name},
            )
            db.session.commit()
        return comment

    # ------------------------------------------------------------ checklists
    @staticmethod
    def list_items(include_inactive: bool = False) -> list[ReviewChecklistItem]:
        query = db.session.query(ReviewChecklistItem)
        if not include_inactive:
            query = query.filter(ReviewChecklistItem.is_active == 1)
        return query.order_by(ReviewChecklistItem.sort_order, ReviewChecklistItem.id).all()

    @staticmethod
    def items_for(cr: ChangeRequest) -> list[ReviewChecklistItem]:
        group_id = cr.revision.status_code.functional_system_group_id
        return [
            item
            for item in FieldReviewService.list_items()
            if item.functional_system_group_id in (None, group_id)
        ]

    @staticmethod
    def create_item(text: str, group_id: int | None, actor, sort_order: int = 0):
        if actor.role_code != "ADMINISTRATOR":
            raise ForbiddenError("SEC-010: only an Administrator maintains the review checklist.")
        text = (text or "").strip()
        if not 3 <= len(text) <= 300:
            raise ValueError("Checklist text must be between 3 and 300 characters.")
        item = ReviewChecklistItem(
            functional_system_group_id=group_id or None,
            text=text,
            sort_order=sort_order,
            created_at=utcnow_iso(),
        )
        db.session.add(item)
        db.session.flush()
        AuditService.log(
            "ReviewChecklistItem",
            item.id,
            "CHECKLIST_ITEM_CREATE",
            actor=actor,
            after={"text": text, "functional_system_group_id": group_id},
        )
        db.session.commit()
        return item

    @staticmethod
    def update_item(item_id: int, data: dict, actor) -> ReviewChecklistItem:
        if actor.role_code != "ADMINISTRATOR":
            raise ForbiddenError("SEC-010: only an Administrator maintains the review checklist.")
        item = db.session.get(ReviewChecklistItem, item_id)
        if item is None:
            raise NotFoundError("Checklist item not found")
        before = {"text": item.text, "is_active": item.is_active, "sort_order": item.sort_order}
        if "text" in data:
            text = (data["text"] or "").strip()
            if not 3 <= len(text) <= 300:
                raise ValueError("Checklist text must be between 3 and 300 characters.")
            item.text = text
        if "is_active" in data:
            item.is_active = 1 if data["is_active"] else 0
        if "sort_order" in data:
            item.sort_order = int(data["sort_order"])
        AuditService.log(
            "ReviewChecklistItem",
            item.id,
            "CHECKLIST_ITEM_UPDATE",
            actor=actor,
            before=before,
            after={"text": item.text, "is_active": item.is_active, "sort_order": item.sort_order},
        )
        db.session.commit()
        return item

    @staticmethod
    def assert_confirmed(cr: ChangeRequest, confirmed_ids) -> list[ReviewChecklistItem]:
        """Every applicable item must be confirmed; returns those items."""
        items = FieldReviewService.items_for(cr)
        try:
            confirmed = {int(i) for i in (confirmed_ids or [])}
        except (TypeError, ValueError) as exc:
            raise ValueError("checklist_confirmed must be a list of checklist item ids.") from exc
        missing = [item for item in items if item.id not in confirmed]
        if missing:
            raise ValueError(
                "Confirm every review checklist item before approving; still open: "
                + "; ".join(f'"{m.text}"' for m in missing[:5])
            )
        return items

    @staticmethod
    def record_confirmations(
        cr: ChangeRequest, items: list[ReviewChecklistItem], actor
    ) -> list[int]:
        now = utcnow_iso()
        for item in items:
            existing = (
                db.session.query(CrChecklistConfirmation)
                .filter(
                    CrChecklistConfirmation.change_request_id == cr.id,
                    CrChecklistConfirmation.checklist_item_id == item.id,
                )
                .first()
            )
            if existing is not None:
                existing.item_text, existing.confirmed_by, existing.confirmed_at = (
                    item.text,
                    actor.id,
                    now,
                )
            else:
                db.session.add(
                    CrChecklistConfirmation(
                        change_request_id=cr.id,
                        checklist_item_id=item.id,
                        item_text=item.text,
                        confirmed_by=actor.id,
                        confirmed_at=now,
                    )
                )
        return [i.id for i in items]

    @staticmethod
    def confirmations(cr_id: int) -> list[CrChecklistConfirmation]:
        return (
            db.session.query(CrChecklistConfirmation)
            .filter(CrChecklistConfirmation.change_request_id == cr_id)
            .order_by(CrChecklistConfirmation.id)
            .all()
        )

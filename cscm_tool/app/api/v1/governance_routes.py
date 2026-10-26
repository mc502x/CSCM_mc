"""Governance extras of the improvement pack: field comments and the review checklist
(I-23), evidence attachments (I-13), change sets (I-11), delegation (I-16), SLA views and
reviewer balancing (I-08, I-30), notifications and settings (I-08).

Every handler is thin: the service layer owns the rules and the exceptions it raises are
turned into responses by `error_response`."""

from flask import Response, jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1._errors import error_response
from app.api.v1.serializers import (
    attachment_payload,
    change_set_payload,
    checklist_item_payload,
    delegation_payload,
    field_comment_payload,
    notification_payload,
)
from app.auth.decorators import (
    current_user,
    login_required,
    require_role,
    require_role_or_delegate,
)
from app.auth.roles import OVERSIGHT_ROLES
from app.domain.errors import DomainError, NotFoundError
from app.extensions import db
from app.models.change_request import ChangeRequest
from app.services.attachment_service import AttachmentService
from app.services.change_request_service import ChangeRequestService
from app.services.change_set_service import ChangeSetService
from app.services.delegation_service import DelegationService
from app.services.field_review_service import FieldReviewService
from app.services.notification_service import NotificationService
from app.services.settings_service import SettingsService
from app.services.sla_service import SlaService

_WORKING = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")  # BR-009: never Viewers
_REVIEWING = ("REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER")


def _body() -> dict:
    return request.get_json(silent=True) or {}


# ---------------------------------------------------------------- field comments (I-23)
@api_v1_bp.get("/change-requests/<int:cr_id>/field-comments")
@require_role(*_WORKING)
def list_field_comments(cr_id: int):
    if db.session.get(ChangeRequest, cr_id) is None:
        return jsonify(error="not_found", message="Change request not found"), 404
    return jsonify(
        items=[field_comment_payload(c) for c in FieldReviewService.list_field_comments(cr_id)]
    )


@api_v1_bp.post("/change-requests/<int:cr_id>/field-comments")
@require_role_or_delegate(*_REVIEWING)
def add_field_comment(cr_id: int):
    body = _body()
    try:
        comment = FieldReviewService.add_field_comment(
            cr_id, body.get("field", ""), body.get("comment", ""), current_user
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(field_comment_payload(comment)), 201


@api_v1_bp.post("/field-comments/<int:comment_id>/resolve")
@require_role(*_WORKING)
def resolve_field_comment(comment_id: int):
    try:
        comment = FieldReviewService.resolve_field_comment(comment_id, current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(field_comment_payload(comment))


# ---------------------------------------------------------------- review checklist (I-23)
@api_v1_bp.get("/review-checklist-items")
@require_role(*_WORKING)
def list_checklist_items():
    include_inactive = request.args.get("include_inactive") == "true" and (
        current_user.role_code == "ADMINISTRATOR"
    )
    return jsonify(
        items=[
            checklist_item_payload(i)
            for i in FieldReviewService.list_items(include_inactive=include_inactive)
        ]
    )


@api_v1_bp.post("/review-checklist-items")
@require_role("ADMINISTRATOR")
def create_checklist_item():
    body = _body()
    try:
        item = FieldReviewService.create_item(
            body.get("text", ""),
            body.get("functional_system_group"),
            current_user,
            sort_order=int(body.get("sort_order", 0)),
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(checklist_item_payload(item)), 201


@api_v1_bp.patch("/review-checklist-items/<int:item_id>")
@require_role("ADMINISTRATOR")
def update_checklist_item(item_id: int):
    try:
        item = FieldReviewService.update_item(item_id, _body(), current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(checklist_item_payload(item))


@api_v1_bp.get("/change-requests/<int:cr_id>/review-checklist")
@require_role(*_WORKING)
def cr_review_checklist(cr_id: int):
    cr = db.session.get(ChangeRequest, cr_id)
    if cr is None:
        return jsonify(error="not_found", message="Change request not found"), 404
    return jsonify(
        items=[checklist_item_payload(i) for i in FieldReviewService.items_for(cr)],
        confirmations=[
            {
                "checklist_item_id": c.checklist_item_id,
                "item_text": c.item_text,
                "confirmed_by": c.confirmed_by,
                "confirmed_at": c.confirmed_at,
            }
            for c in FieldReviewService.confirmations(cr_id)
        ],
    )


# ---------------------------------------------------------------- attachments (I-13)
@api_v1_bp.get("/change-requests/<int:cr_id>/attachments")
@require_role(*_WORKING)
def list_attachments(cr_id: int):
    if db.session.get(ChangeRequest, cr_id) is None:
        return jsonify(error="not_found", message="Change request not found"), 404
    try:
        items = AttachmentService.list_for(cr_id, current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(items=[attachment_payload(a) for a in items])


@api_v1_bp.post("/change-requests/<int:cr_id>/attachments")
@require_role("ADMINISTRATOR", "ENGINEER")
def add_attachment(cr_id: int):
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return (
            jsonify(error="validation_error", message="A file upload named 'file' is required"),
            422,
        )
    try:
        attachment = AttachmentService.add(
            cr_id,
            upload.filename,
            upload.read(),
            request.form.get("description"),
            current_user,
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(attachment_payload(attachment)), 201


@api_v1_bp.get("/attachments/<int:attachment_id>")
@require_role(*_WORKING)
def download_attachment(attachment_id: int):
    try:
        path, attachment = AttachmentService.get_for_download(attachment_id, current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return Response(
        path.read_bytes(),
        mimetype=attachment.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{attachment.filename}"',
            "X-Content-SHA256": attachment.sha256,
        },
    )


@api_v1_bp.delete("/attachments/<int:attachment_id>")
@require_role("ADMINISTRATOR", "ENGINEER")
def delete_attachment(attachment_id: int):
    try:
        AttachmentService.delete(attachment_id, current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return "", 204


# ---------------------------------------------------------------- SLA and balancing (I-08, I-30)
@api_v1_bp.get("/change-requests/stalled")
@require_role("ADMINISTRATOR")
def stalled_change_requests():
    return jsonify(
        items=[
            {
                "change_request_id": cr.id,
                "title": cr.revision.title,
                "assigned_reviewer_id": (cr.assigned_reviewer_id),
                **info,
            }
            for cr, info in SlaService.stalled()
        ],
        thresholds=SlaService.thresholds(),
    )


@api_v1_bp.get("/change-requests/<int:cr_id>/sla")
@require_role(*_WORKING)
def change_request_sla(cr_id: int):
    cr = db.session.get(ChangeRequest, cr_id)
    if cr is None:
        return jsonify(error="not_found", message="Change request not found"), 404
    return jsonify(sla=SlaService.info(cr))


@api_v1_bp.get("/reviewers/workload")
@require_role("ADMINISTRATOR")
def reviewer_workload():
    return jsonify(
        items=[
            {"user_id": r["user"].id, "full_name": r["user"].full_name, "open_reviews": r["load"]}
            for r in ChangeRequestService.reviewer_workloads()
        ]
    )


@api_v1_bp.post("/change-requests/<int:cr_id>/reviewer-assignment/auto")
@require_role("ADMINISTRATOR")
def auto_assign_reviewer(cr_id: int):
    from app.api.v1.serializers import change_request_payload

    try:
        cr = ChangeRequestService.auto_assign_reviewer(cr_id, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Change request not found"), 404
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(change_request_payload(cr))


# ---------------------------------------------------------------- change sets (I-11)
@api_v1_bp.get("/change-sets")
@require_role(*OVERSIGHT_ROLES)
def list_change_sets():
    return jsonify(items=[change_set_payload(s) for s in ChangeSetService.list_all()])


@api_v1_bp.post("/change-sets")
@require_role("ADMINISTRATOR", "ENGINEER", "CHIEF_ENGINEER")
def create_change_set():
    body = _body()
    try:
        change_set = ChangeSetService.create(
            body.get("name", ""),
            body.get("description"),
            body.get("target_software_version"),
            current_user,
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(change_set_payload(change_set)), 201


@api_v1_bp.get("/change-sets/<int:change_set_id>")
@require_role(*OVERSIGHT_ROLES)
def get_change_set(change_set_id: int):
    try:
        overview = ChangeSetService.overview(change_set_id)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    payload = change_set_payload(overview["change_set"])
    payload["tally"] = overview["tally"]
    payload["items"] = [
        {
            "change_request_id": row["cr"].id,
            "status_code_identifier": row["identifier"],
            "title": row["title"],
            "state": row["state"],
            "sla": row["sla"],
        }
        for row in overview["rows"]
    ]
    return jsonify(payload)


@api_v1_bp.post("/change-sets/<int:change_set_id>/change-requests")
@require_role("ADMINISTRATOR", "ENGINEER")
def add_cr_to_change_set(change_set_id: int):
    try:
        change_set = ChangeSetService.add_cr(
            change_set_id, int(_body().get("change_request_id") or 0), current_user
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(change_set_payload(change_set))


@api_v1_bp.delete("/change-sets/<int:change_set_id>/change-requests/<int:cr_id>")
@require_role("ADMINISTRATOR", "ENGINEER")
def remove_cr_from_change_set(change_set_id: int, cr_id: int):
    try:
        ChangeSetService.remove_cr(change_set_id, cr_id, current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return "", 204


@api_v1_bp.post("/change-sets/<int:change_set_id>/close")
@require_role("ADMINISTRATOR")
def close_change_set(change_set_id: int):
    try:
        change_set = ChangeSetService.close(change_set_id, current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(change_set_payload(change_set))


@api_v1_bp.post("/change-sets/<int:change_set_id>/decisions")
@require_role_or_delegate(*_REVIEWING)
def decide_change_set(change_set_id: int):
    """Bulk presentation of single-CR decisions: each CR is decided by its own service
    call, with its own segregation-of-duties check and audit entry."""
    body = _body()
    try:
        results = ChangeSetService.bulk_decide(
            change_set_id,
            body.get("step", ""),
            body.get("decision", ""),
            body.get("comment"),
            current_user,
            body.get("current_password"),
            cr_ids=body.get("change_request_ids"),
            sample_id=body.get("sample_id"),
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(results=results)


# ---------------------------------------------------------------- delegation (I-16)
@api_v1_bp.get("/delegations")
@require_role("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER", "ENGINEER")
def list_delegations():
    include_inactive = request.args.get("include_inactive") == "true"
    return jsonify(
        items=[
            delegation_payload(d)
            for d in DelegationService.list_for(current_user, include_inactive=include_inactive)
        ]
    )


@api_v1_bp.post("/delegations")
@require_role("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER")
def create_delegation():
    body = _body()
    try:
        delegation = DelegationService.create(
            int(body.get("delegator_id") or current_user.id),
            int(body.get("delegate_id") or 0),
            body.get("valid_from", ""),
            body.get("valid_to", ""),
            current_user,
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(delegation_payload(delegation)), 201


@api_v1_bp.delete("/delegations/<int:delegation_id>")
@require_role("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER")
def revoke_delegation(delegation_id: int):
    try:
        DelegationService.revoke(delegation_id, current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return "", 204


# ---------------------------------------------------------------- notifications (I-08)
@api_v1_bp.get("/notifications")
@login_required
def list_notifications():
    unread_only = request.args.get("unread") == "true"
    return jsonify(
        items=[
            notification_payload(n)
            for n in NotificationService.list_for(current_user.id, unread_only=unread_only)
        ],
        unread=NotificationService.unread_count(current_user.id),
    )


@api_v1_bp.post("/notifications/read-all")
@login_required
def read_all_notifications():
    return jsonify(updated=NotificationService.mark_all_read(current_user))


@api_v1_bp.post("/notifications/<int:notification_id>/read")
@login_required
def read_notification(notification_id: int):
    try:
        notice = NotificationService.mark_read(notification_id, current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(notification_payload(notice))


# ---------------------------------------------------------------- settings (I-08, I-19, I-30)
@api_v1_bp.get("/settings")
@require_role("ADMINISTRATOR")
def get_settings():
    return jsonify(items=SettingsService.all())


@api_v1_bp.put("/settings")
@require_role("ADMINISTRATOR")
def update_settings():
    try:
        items = SettingsService.update(_body(), current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(items=items)

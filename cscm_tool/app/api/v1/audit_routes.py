"""FR-070-FR-071. See docs/artifacts/openapi.yaml /audit-log.
Administrator gets full access; Reviewer/Chief Engineer get a scoped
subset — see AuditService.search for the exact scoping rule chosen."""

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1.serializers import audit_log_entry_payload
from app.auth.decorators import current_user, require_role
from app.services.audit_service import AuditService


@api_v1_bp.get("/audit-log")
@require_role("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER")
def search_audit_log():
    # Contract quirk (docs/artifacts/openapi.yaml): unlike every other list
    # endpoint, /audit-log's 200 response is a plain array, not an
    # {items,total,page,page_size} envelope, even though page/page_size are
    # still accepted request parameters.
    page = request.args.get("page", 1, type=int)
    page_size = min(request.args.get("page_size", 50, type=int), 200)
    items, _total = AuditService.search(
        current_user,
        entity_type=request.args.get("entity_type"),
        entity_id=request.args.get("entity_id", type=int),
        actor_id=request.args.get("actor_id", type=int),
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
        page=page,
        page_size=page_size,
    )
    return jsonify([audit_log_entry_payload(e) for e in items])

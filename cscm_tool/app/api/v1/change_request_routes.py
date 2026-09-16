"""FR-031-FR-039. See docs/artifacts/openapi.yaml paths /change-requests*.
The segregation-of-duties check (actor != author/prior sign-offs) lives in
the service layer, not here — the decorator only checks role membership,
which is static (docs/18-claude-code-implementation-guide.md §3)."""

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1.serializers import change_request_payload
from app.auth.decorators import current_user, login_required, require_role
from app.domain.errors import (
    DomainError,
    InvalidTransitionError,
    NotFoundError,
    SegregationOfDutiesViolation,
)
from app.extensions import db
from app.models.change_request import ChangeRequest
from app.services.change_request_service import ChangeRequestService


def _decision_error_response(exc: Exception):
    if isinstance(exc, SegregationOfDutiesViolation):
        return jsonify(error="forbidden", message=str(exc)), 403
    if isinstance(exc, InvalidTransitionError):
        return jsonify(error="conflict", message=str(exc)), 409
    return jsonify(error="validation_error", message=str(exc)), 422


@api_v1_bp.get("/change-requests")
@login_required
def list_change_requests():
    page = request.args.get("page", 1, type=int)
    page_size = min(request.args.get("page_size", 50, type=int), 200)
    query = db.session.query(ChangeRequest)
    state = request.args.get("state")
    if state:
        query = query.filter(ChangeRequest.state == state)
    requested_by = request.args.get("requested_by", type=int)
    if requested_by is not None:
        query = query.filter(ChangeRequest.requested_by == requested_by)
    total = query.count()
    items = (
        query.order_by(ChangeRequest.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    )
    return jsonify(
        items=[change_request_payload(cr) for cr in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@api_v1_bp.get("/change-requests/<int:cr_id>")
@login_required
def get_change_request(cr_id: int):
    cr = db.session.get(ChangeRequest, cr_id)
    if cr is None:
        return jsonify(error="not_found", message="Change request not found"), 404
    return jsonify(change_request_payload(cr))


@api_v1_bp.post("/change-requests/<int:cr_id>/submit")
@require_role("ADMINISTRATOR", "ENGINEER")
def submit(cr_id: int):
    try:
        cr = ChangeRequestService.submit(cr_id, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Change request not found"), 404
    except SegregationOfDutiesViolation as exc:
        return jsonify(error="forbidden", message=str(exc)), 403
    except InvalidTransitionError as exc:
        return jsonify(error="conflict", message=str(exc)), 409
    except (DomainError, ValueError) as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return jsonify(change_request_payload(cr)), 200


@api_v1_bp.post("/change-requests/<int:cr_id>/reviewer-signoff")
@require_role("REVIEWER")
def reviewer_signoff(cr_id: int):
    body = request.get_json(silent=True) or {}
    try:
        cr = ChangeRequestService.reviewer_signoff(
            cr_id, current_user, body.get("decision", ""), body.get("comment")
        )
    except NotFoundError:
        return jsonify(error="not_found", message="Change request not found"), 404
    except (SegregationOfDutiesViolation, InvalidTransitionError, ValueError) as exc:
        return _decision_error_response(exc)

    return jsonify(change_request_payload(cr)), 200


@api_v1_bp.post("/change-requests/<int:cr_id>/admin-signoff")
@require_role("ADMINISTRATOR")
def admin_signoff(cr_id: int):
    body = request.get_json(silent=True) or {}
    try:
        cr = ChangeRequestService.admin_signoff(
            cr_id, current_user, body.get("decision", ""), body.get("comment")
        )
    except NotFoundError:
        return jsonify(error="not_found", message="Change request not found"), 404
    except (SegregationOfDutiesViolation, InvalidTransitionError, ValueError) as exc:
        return _decision_error_response(exc)

    return jsonify(change_request_payload(cr)), 200


@api_v1_bp.post("/change-requests/<int:cr_id>/chief-engineer-decide")
@require_role("CHIEF_ENGINEER")
def chief_engineer_decide(cr_id: int):
    body = request.get_json(silent=True) or {}
    try:
        cr = ChangeRequestService.chief_engineer_decide(
            cr_id, current_user, body.get("decision", ""), body.get("comment")
        )
    except NotFoundError:
        return jsonify(error="not_found", message="Change request not found"), 404
    except (SegregationOfDutiesViolation, InvalidTransitionError, ValueError) as exc:
        return _decision_error_response(exc)

    return jsonify(change_request_payload(cr)), 200


@api_v1_bp.post("/change-requests/<int:cr_id>/withdraw")
@require_role("ADMINISTRATOR", "ENGINEER")
def withdraw(cr_id: int):
    try:
        ChangeRequestService.withdraw(cr_id, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Change request not found"), 404
    except SegregationOfDutiesViolation as exc:
        return jsonify(error="forbidden", message=str(exc)), 403
    except InvalidTransitionError as exc:
        return jsonify(error="conflict", message=str(exc)), 409

    return jsonify(message="Withdrawn"), 200

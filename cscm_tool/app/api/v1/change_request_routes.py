"""FR-031-FR-039. See docs/artifacts/openapi.yaml paths /change-requests*.
The segregation-of-duties check (actor != author/prior sign-offs) lives in
the service layer, not here — the decorator only checks role membership,
which is static (docs/18-claude-code-implementation-guide.md §3)."""

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1.serializers import change_request_payload
from app.auth.decorators import current_user, require_role, require_role_or_delegate
from app.auth.roles import OVERSIGHT_ROLES
from app.domain.errors import (
    AccountLockedError,
    DomainError,
    ForbiddenError,
    InvalidTransitionError,
    NotFoundError,
    SegregationOfDutiesViolation,
    StepUpRequiredError,
)
from app.extensions import db
from app.models.change_request import ChangeRequest
from app.services.change_request_service import ChangeRequestService


def _decision_error_response(exc: Exception):
    if isinstance(exc, StepUpRequiredError):
        # I-17: not a role problem - the actor must confirm with their password.
        code = "step_up_failed" if exc.wrong_password else "step_up_required"
        return jsonify(error=code, message=str(exc)), 403
    if isinstance(exc, AccountLockedError):
        return jsonify(error="account_locked", message=str(exc)), 403
    if isinstance(exc, SegregationOfDutiesViolation | ForbiddenError):
        return jsonify(error="forbidden", message=str(exc)), 403
    if isinstance(exc, InvalidTransitionError):
        return jsonify(error="conflict", message=str(exc)), 409
    return jsonify(error="validation_error", message=str(exc)), 422


@api_v1_bp.get("/change-requests")
@require_role(*OVERSIGHT_ROLES)  # BR-009: never Viewers
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
@require_role(*OVERSIGHT_ROLES)  # BR-009: never Viewers
def get_change_request(cr_id: int):
    cr = db.session.get(ChangeRequest, cr_id)
    if cr is None:
        return jsonify(error="not_found", message="Change request not found"), 404
    return jsonify(change_request_payload(cr))


@api_v1_bp.post("/change-requests/<int:cr_id>/submit")
@require_role("ADMINISTRATOR", "ENGINEER")
def submit(cr_id: int):
    body = request.get_json(silent=True) or {}
    try:
        cr = ChangeRequestService.submit(
            cr_id,
            current_user,
            identifier_override=body.get("identifier_override"),
            override_reason=body.get("override_reason"),
        )
    except NotFoundError:
        return jsonify(error="not_found", message="Change request not found"), 404
    except SegregationOfDutiesViolation as exc:
        return jsonify(error="forbidden", message=str(exc)), 403
    except InvalidTransitionError as exc:
        return jsonify(error="conflict", message=str(exc)), 409
    except (DomainError, ValueError) as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    from app.services.status_code_service import StatusCodeService

    payload = change_request_payload(cr)
    payload["warnings"] = StatusCodeService.warnings_for(cr.revision)
    return jsonify(payload), 200


@api_v1_bp.post("/change-requests/<int:cr_id>/reviewer-signoff")
@require_role_or_delegate("REVIEWER")
def reviewer_signoff(cr_id: int):
    """I-17: body must carry `current_password`. I-23: `checklist_confirmed` lists the
    review-checklist item ids the Reviewer confirms (required when items apply)."""
    body = request.get_json(silent=True) or {}
    try:
        cr = ChangeRequestService.reviewer_signoff(
            cr_id,
            current_user,
            body.get("decision", ""),
            body.get("comment"),
            reauth_password=body.get("current_password"),
            checklist_confirmed=body.get("checklist_confirmed"),
        )
    except NotFoundError:
        return jsonify(error="not_found", message="Change request not found"), 404
    except (
        SegregationOfDutiesViolation,
        InvalidTransitionError,
        ValueError,
        StepUpRequiredError,
        AccountLockedError,
        ForbiddenError,
    ) as exc:
        return _decision_error_response(exc)

    return jsonify(change_request_payload(cr)), 200


@api_v1_bp.post("/change-requests/<int:cr_id>/admin-signoff")
@require_role_or_delegate("ADMINISTRATOR")
def admin_signoff(cr_id: int):
    body = request.get_json(silent=True) or {}
    try:
        cr = ChangeRequestService.admin_signoff(
            cr_id,
            current_user,
            body.get("decision", ""),
            body.get("comment"),
            access_overrides=body.get("access_overrides"),
            reauth_password=body.get("current_password"),
        )
    except NotFoundError:
        return jsonify(error="not_found", message="Change request not found"), 404
    except (
        SegregationOfDutiesViolation,
        InvalidTransitionError,
        ValueError,
        StepUpRequiredError,
        AccountLockedError,
        ForbiddenError,
    ) as exc:
        return _decision_error_response(exc)

    return jsonify(change_request_payload(cr)), 200


@api_v1_bp.post("/change-requests/<int:cr_id>/chief-engineer-decide")
@require_role_or_delegate("CHIEF_ENGINEER")
def chief_engineer_decide(cr_id: int):
    body = request.get_json(silent=True) or {}
    try:
        cr = ChangeRequestService.chief_engineer_decide(
            cr_id,
            current_user,
            body.get("decision", ""),
            body.get("comment"),
            reauth_password=body.get("current_password"),
        )
    except NotFoundError:
        return jsonify(error="not_found", message="Change request not found"), 404
    except (
        SegregationOfDutiesViolation,
        InvalidTransitionError,
        ValueError,
        StepUpRequiredError,
        AccountLockedError,
        ForbiddenError,
    ) as exc:
        return _decision_error_response(exc)

    return jsonify(change_request_payload(cr)), 200


@api_v1_bp.post("/change-requests/<int:cr_id>/comments")
@require_role("REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER")
def add_comment(cr_id: int):
    """FR-038: comment without a decision, at any stage."""
    body = request.get_json(silent=True) or {}
    try:
        cr = ChangeRequestService.add_comment(cr_id, current_user, body.get("comment", ""))
    except NotFoundError:
        return jsonify(error="not_found", message="Change request not found"), 404
    except ValueError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return jsonify(change_request_payload(cr)), 201


@api_v1_bp.put("/change-requests/<int:cr_id>/reviewer-assignment")
@require_role("ADMINISTRATOR")
def assign_reviewer(cr_id: int):
    """FR-039: body {"reviewer_id": <int>|null}; null unassigns."""
    body = request.get_json(silent=True) or {}
    try:
        cr = ChangeRequestService.assign_reviewer(cr_id, body.get("reviewer_id"), current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Change request not found"), 404
    except (SegregationOfDutiesViolation, InvalidTransitionError, ValueError) as exc:
        return _decision_error_response(exc)

    return jsonify(change_request_payload(cr)), 200


@api_v1_bp.post("/change-requests/withdraw")
@require_role("ADMINISTRATOR", "ENGINEER")
def withdraw_many():
    """Withdraw several of your own open change requests: `{cr_ids: [...]}`. 200 with one result per
    request; a request that cannot be withdrawn is reported in its result and the others go on."""
    body = request.get_json(silent=True) or {}
    cr_ids = body.get("cr_ids")
    if not (isinstance(cr_ids, list) and cr_ids and all(isinstance(i, int) for i in cr_ids)):
        return jsonify(error="validation_error", message="cr_ids must be a list of ids"), 422
    results = ChangeRequestService.withdraw_many(cr_ids, current_user)
    return jsonify(
        results=results,
        withdrawn=sum(1 for r in results if r["ok"]),
        failed=sum(1 for r in results if not r["ok"]),
    )


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

"""FR-020-FR-029, FR-053-FR-056, FR-060-FR-064. See docs/artifacts/openapi.yaml
paths /status-codes*."""

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1.serializers import revision_payload
from app.auth.decorators import current_user, login_required, require_role
from app.domain.errors import DomainError, NotFoundError
from app.services.status_code_service import StatusCodeService, ValidationFailed


def _validation_error_response(exc: ValidationFailed):
    return jsonify(error="validation_error", message=str(exc), field_errors=exc.field_errors), 422


@api_v1_bp.get("/status-codes")
@login_required
def list_status_codes():
    page = request.args.get("page", 1, type=int)
    page_size = min(request.args.get("page_size", 50, type=int), 200)
    items, total = StatusCodeService.search(
        current_user,
        q=request.args.get("q"),
        functional_system_group_code=request.args.get("functional_system_group"),
        functional_subgroup_code=request.args.get("functional_subgroup"),
        turbine_platform_code=request.args.get("turbine_platform"),
        lifecycle_status=request.args.get("lifecycle_status"),
        is_sandbox=request.args.get("is_sandbox", "false").lower() == "true",
        owner_id=request.args.get("owner_id", type=int),
        page=page,
        page_size=page_size,
        sort=request.args.get("sort"),
    )
    return jsonify(
        items=[revision_payload(r) for r in items], total=total, page=page, page_size=page_size
    )


@api_v1_bp.post("/status-codes")
@require_role("ADMINISTRATOR", "ENGINEER")
def create_status_code():
    body = request.get_json(silent=True) or {}
    is_sandbox = bool(body.get("is_sandbox", False))
    try:
        if is_sandbox:
            revision = StatusCodeService.create_sandbox(body, current_user)
        else:
            revision = StatusCodeService.create_draft(body, current_user)
    except ValidationFailed as exc:
        return _validation_error_response(exc)
    except (KeyError, ValueError) as exc:
        return jsonify(error="validation_error", message=str(exc)), 422
    except DomainError as exc:
        return jsonify(error="forbidden", message=str(exc)), 403

    return jsonify(revision_payload(revision)), 201


@api_v1_bp.get("/status-codes/next-available")
@login_required
def next_available_identifier():
    group_code = request.args.get("functional_system_group")
    if not group_code:
        return (
            jsonify(error="validation_error", message="functional_system_group is required"),
            422,
        )
    try:
        preview = StatusCodeService.preview_next_identifier(
            group_code, request.args.get("functional_subgroup")
        )
    except ValueError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422
    except DomainError as exc:
        return jsonify(error="capacity_exhausted", message=str(exc)), 422

    return jsonify(
        preview_identifier=preview,
        note=(
            "Not allocated until Submit for Review; "
            "another submission may claim this number first."
        ),
    )


@api_v1_bp.get("/status-codes/<int:status_code_id>")
@login_required
def get_status_code(status_code_id: int):
    try:
        revision = StatusCodeService.get_current_revision(status_code_id, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Status code not found"), 404
    return jsonify(revision_payload(revision))


@api_v1_bp.delete("/status-codes/<int:status_code_id>")
@require_role("ADMINISTRATOR")
def delete_sandbox_status_code(status_code_id: int):
    try:
        StatusCodeService.delete_sandbox(status_code_id, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Status code not found"), 404
    except DomainError as exc:
        return jsonify(error="forbidden", message=str(exc)), 403
    return "", 204


@api_v1_bp.get("/status-codes/<int:status_code_id>/revisions")
@login_required
def list_revisions(status_code_id: int):
    revisions = StatusCodeService.list_revision_history(status_code_id, current_user)
    return jsonify([revision_payload(r) for r in revisions])


@api_v1_bp.post("/status-codes/<int:status_code_id>/revisions")
@require_role("ADMINISTRATOR", "ENGINEER")
def create_revision(status_code_id: int):
    body = request.get_json(silent=True) or {}
    try:
        revision = StatusCodeService.create_revision(status_code_id, body, current_user)
    except ValidationFailed as exc:
        return _validation_error_response(exc)
    except (KeyError, ValueError) as exc:
        return jsonify(error="validation_error", message=str(exc)), 422
    except DomainError as exc:
        return jsonify(error="conflict", message=str(exc)), 409

    return jsonify(revision_payload(revision)), 201

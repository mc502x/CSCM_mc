"""FR-020-FR-029, FR-053-FR-056, FR-060-FR-064. See docs/artifacts/openapi.yaml
paths /status-codes*."""

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1.serializers import revision_payload
from app.auth.decorators import allow_token, current_user, login_required, require_role
from app.auth.roles import OVERSIGHT_ROLES
from app.domain.errors import DomainError, InvalidTransitionError, NotFoundError
from app.services.revision_diff_service import RevisionDiffService
from app.services.status_code_service import StatusCodeService, ValidationFailed


def _validation_error_response(exc: ValidationFailed):
    return jsonify(error="validation_error", message=str(exc), field_errors=exc.field_errors), 422


@api_v1_bp.get("/status-codes")
@allow_token("catalogue:read")
@login_required
def list_status_codes():
    page = request.args.get("page", 1, type=int)
    page_size = min(request.args.get("page_size", 50, type=int), 200)
    items, total = StatusCodeService.search(
        current_user,
        q=request.args.get("q"),
        functional_system_group_id=request.args.get("functional_system_group", type=int),
        functional_subgroup_id=request.args.get("functional_subgroup", type=int),
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

    warnings = [] if is_sandbox else StatusCodeService.warnings_for(revision)
    return jsonify(revision_payload(revision, warnings=warnings)), 201


@api_v1_bp.post("/status-codes/<int:status_code_id>/deprecation-requests")
@require_role("ADMINISTRATOR", "ENGINEER")
def create_deprecation_request(status_code_id: int):
    """FR-050: Released -> Deprecated via the full dual-review +
    Chief-Engineer-approval cycle (docs/05-governance-handbook.md §5)."""
    body = request.get_json(silent=True) or {}
    try:
        revision = StatusCodeService.create_deprecation_request(
            status_code_id,
            body.get("reason", ""),
            body.get("superseded_by_status_code_id"),
            current_user,
            acknowledge_dependants=bool(body.get("acknowledge_dependants", False)),
        )
    except NotFoundError:
        return jsonify(error="not_found", message="Status code not found"), 404
    except InvalidTransitionError as exc:
        return jsonify(error="conflict", message=str(exc)), 409
    except ValidationFailed as exc:
        return _validation_error_response(exc)

    return jsonify(revision_payload(revision)), 201


@api_v1_bp.post("/status-codes/<int:status_code_id>/archive")
@require_role("ADMINISTRATOR")
def archive_status_code(status_code_id: int):
    """FR-051/BR-006: direct Administrator action, no CR."""
    try:
        revision = StatusCodeService.archive(status_code_id, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Status code not found"), 404
    except InvalidTransitionError as exc:
        return jsonify(error="conflict", message=str(exc)), 409
    except DomainError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return jsonify(revision_payload(revision)), 200


@api_v1_bp.post("/status-codes/<int:status_code_id>/reinstate")
@require_role("ADMINISTRATOR")
def reinstate_status_code(status_code_id: int):
    """Deprecated -> Released, exceptional (docs/05-governance-handbook.md §5)."""
    body = request.get_json(silent=True) or {}
    try:
        revision = StatusCodeService.reinstate(status_code_id, body.get("reason", ""), current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Status code not found"), 404
    except InvalidTransitionError as exc:
        return jsonify(error="conflict", message=str(exc)), 409
    except ValidationFailed as exc:
        return _validation_error_response(exc)

    return jsonify(revision_payload(revision)), 200


@api_v1_bp.get("/status-codes/next-available")
@require_role("ADMINISTRATOR", "ENGINEER")
def next_available_identifier():
    """v3: both ids required — Functional Subgroup is mandatory, never
    optional (docs/artifacts/openapi.yaml)."""
    group_id = request.args.get("functional_system_group", type=int)
    subgroup_id = request.args.get("functional_subgroup", type=int)
    if not group_id or not subgroup_id:
        return (
            jsonify(
                error="validation_error",
                message="functional_system_group and functional_subgroup are required",
            ),
            422,
        )
    try:
        preview = StatusCodeService.preview_next_identifier(group_id, subgroup_id)
        capacity = StatusCodeService.capacity(group_id, subgroup_id)
    except ValueError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422
    except DomainError as exc:
        return jsonify(error="capacity_exhausted", message=str(exc)), 422

    return jsonify(
        preview_identifier=preview,
        capacity=capacity,
        note=(
            "Not allocated until Submit for Review; "
            "another submission may claim this number first."
        ),
    )


@api_v1_bp.get("/status-codes/similar")
@require_role("ADMINISTRATOR", "ENGINEER")
def similar_status_codes():
    """I-12: "did you mean to revise ...?" - existing codes of the subgroup with a similar title."""
    from app.services.duplicate_service import DuplicateService

    subgroup_id = request.args.get("functional_subgroup", type=int)
    title = (request.args.get("title") or "").strip()
    if not subgroup_id or not title:
        return (
            jsonify(error="validation_error", message="functional_subgroup and title are required"),
            422,
        )
    hits = DuplicateService.find_similar(
        title, subgroup_id, exclude_status_code_id=request.args.get("exclude", type=int)
    )
    return jsonify(items=hits)


@api_v1_bp.get("/status-codes/<int:status_code_id>")
@allow_token("catalogue:read")
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


@api_v1_bp.get("/status-codes/<int:status_code_id>/where-used")
@require_role(*OVERSIGHT_ROLES)
def where_used(status_code_id: int):
    """I-04: every other code that refers to this one."""
    from app.services.reference_service import ReferenceService

    try:
        StatusCodeService.get_current_revision(status_code_id, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Status code not found"), 404
    return jsonify(items=ReferenceService.where_used(status_code_id))


@api_v1_bp.get("/status-codes/<int:status_code_id>/connections")
@require_role(*OVERSIGHT_ROLES)
def code_connections(status_code_id: int):
    """FR-179: what suppresses this code, what it suppresses, what it requires and where it
    escalates, read from the imported programs."""
    from app.services.connection_service import ConnectionService

    try:
        StatusCodeService.get_current_revision(status_code_id, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Status code not found"), 404
    return jsonify(ConnectionService.for_code(status_code_id))


@api_v1_bp.get("/status-codes/connections")
@require_role(*OVERSIGHT_ROLES)
def catalogue_connections():
    """FR-179: causes with the consequences they suppress (a tree), the escalation targets and what
    looks wrong. Optional controller=MC|HC."""
    from app.services.connection_service import ConnectionService

    controller = request.args.get("controller") or None
    if controller not in (None, "MC", "HC"):
        return jsonify(error="validation_error", message="controller must be MC or HC"), 422
    return jsonify(ConnectionService.hierarchy(controller))


@api_v1_bp.get("/status-codes/<int:status_code_id>/family")
@login_required
def platform_family(status_code_id: int):
    """I-25: the code and its platform variants."""
    try:
        StatusCodeService.get_current_revision(status_code_id, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Status code not found"), 404
    members = []
    for code in StatusCodeService.family(status_code_id):
        try:
            revision = StatusCodeService.get_current_revision(code.id, current_user)
        except NotFoundError:
            continue
        members.append(
            {
                "status_code_id": code.id,
                "status_code_identifier": code.status_code_identifier,
                "title": revision.title,
                "turbine_platforms": sorted(p.turbine_platform.code for p in revision.platforms),
                "lifecycle_status": revision.lifecycle_status,
                "platform_variant_of_status_code_id": code.platform_variant_of_status_code_id,
            }
        )
    return jsonify(items=members)


@api_v1_bp.post("/status-codes/<int:status_code_id>/platform-variants")
@require_role("ADMINISTRATOR", "ENGINEER")
def create_platform_variant(status_code_id: int):
    """I-25: copy this code as a Draft for another turbine platform."""
    body = request.get_json(silent=True) or {}
    try:
        revision = StatusCodeService.create_platform_variant(
            status_code_id, body.get("turbine_platform", ""), current_user
        )
    except NotFoundError:
        return jsonify(error="not_found", message="Status code not found"), 404
    except InvalidTransitionError as exc:
        return jsonify(error="conflict", message=str(exc)), 409
    except ValidationFailed as exc:
        return _validation_error_response(exc)
    except (DomainError, ValueError) as exc:
        return jsonify(error="validation_error", message=str(exc)), 422
    return jsonify(revision_payload(revision)), 201


@api_v1_bp.put("/status-codes/<int:status_code_id>/planned-dates")
@require_role("ADMINISTRATOR")
def set_planned_dates(status_code_id: int):
    """I-27: planned effective / deprecation dates on the current revision."""
    body = request.get_json(silent=True) or {}
    try:
        revision = StatusCodeService.set_planned_dates(
            status_code_id,
            body.get("planned_effective_date"),
            body.get("planned_deprecation_date"),
            current_user,
        )
    except NotFoundError:
        return jsonify(error="not_found", message="Status code not found"), 404
    except InvalidTransitionError as exc:
        return jsonify(error="conflict", message=str(exc)), 409
    except ValidationFailed as exc:
        return _validation_error_response(exc)
    return jsonify(revision_payload(revision)), 200


@api_v1_bp.get("/status-codes/<int:status_code_id>/revisions")
@login_required
def list_revisions(status_code_id: int):
    revisions = StatusCodeService.list_revision_history(status_code_id, current_user)
    return jsonify([revision_payload(r) for r in revisions])


@api_v1_bp.get("/status-codes/<int:status_code_id>/revisions/<int:rev_a>/diff/<int:rev_b>")
@login_required
def diff_revisions(status_code_id: int, rev_a: int, rev_b: int):
    """FR-064: field-level diff between two revision numbers of one code."""
    try:
        return jsonify(
            RevisionDiffService.diff_revisions(status_code_id, rev_a, rev_b, current_user)
        )
    except NotFoundError:
        return jsonify(error="not_found", message="Revision not found"), 404


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

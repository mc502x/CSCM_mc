"""FR-045-FR-047, SEC-015. See docs/artifacts/openapi.yaml
/releases/{releaseId}/export and /exports/full-database."""

from flask import Response, jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1._errors import error_response
from app.api.v1.publication_routes import export_options_from_request, file_response
from app.auth.decorators import allow_token, current_user, login_required, require_role
from app.db_modes import writes_on_get
from app.domain.errors import AccountLockedError, DomainError, NotFoundError, StepUpRequiredError
from app.services.export_service import UNRELEASED_EXPORT_ROLES, ExportService
from app.services.release_service import ReleaseService, require_released_or_owner

_VALID_FORMATS = {"csv", "json", "xlsx", "pdf"}
WORKING_SET_NOTICE = "Not for distribution - unapproved data"


@api_v1_bp.get("/releases/<int:release_id>/export")
@allow_token("catalogue:read")
@writes_on_get
@login_required
def export_release(release_id: int):
    """FR-045. Optional profile, audience, language, strict_language, software_version
    (I-02/I-03/I-15/I-07) and bundle=true (ZIP with MANIFEST.json, I-06)."""
    export_format = (request.args.get("format") or "").lower()
    if export_format not in _VALID_FORMATS:
        return (
            jsonify(error="validation_error", message="format must be csv, json, xlsx, or pdf"),
            422,
        )
    try:
        release = ReleaseService.get(release_id)
        require_released_or_owner(release, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Release not found"), 404
    except DomainError as exc:
        return error_response(exc)

    try:
        options = export_options_from_request()
        result = ExportService.export_catalogue(
            ExportService.release_revisions(release, options),
            export_format,
            current_user,
            release_id=release_id,
            name_label=release.version_label,
            options=options,
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return file_response(result)


def _format_or_error():
    export_format = (request.args.get("format") or "").lower()
    if export_format not in _VALID_FORMATS:
        return None, (
            jsonify(error="validation_error", message="format must be csv, json, xlsx, or pdf"),
            422,
        )
    return export_format, None


@api_v1_bp.get("/exports/released")
@allow_token("catalogue:read")
@writes_on_get
@login_required
def export_released():
    """FR-045: the current set of all Released codes (any role; Released data
    is visible to Viewers, BR-009). Optional functional_system_group,
    functional_subgroup, turbine_platform filters, plus the shaping parameters."""
    export_format, error = _format_or_error()
    if error:
        return error
    filters = {
        "functional_system_group_id": request.args.get("functional_system_group", type=int),
        "functional_subgroup_id": request.args.get("functional_subgroup", type=int),
        "turbine_platform_code": request.args.get("turbine_platform") or None,
    }
    try:
        options = export_options_from_request()
        revisions = ExportService.released_revisions(**filters)
        result = ExportService.export_catalogue(
            revisions,
            export_format,
            current_user,
            scope={"scope": "released", **{k: v for k, v in filters.items() if v is not None}},
            options=options,
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return file_response(result)


@api_v1_bp.get("/exports/working-set")
@writes_on_get
@require_role(*UNRELEASED_EXPORT_ROLES)
def export_working_set():
    """FR-046: ad-hoc filtered working set, any lifecycle state, labelled
    "Not for distribution — unapproved data"; only the StCd Owner and Administrator (FR-175)."""
    export_format, error = _format_or_error()
    if error:
        return error
    filters = {
        "q": request.args.get("q") or None,
        "functional_system_group_id": request.args.get("functional_system_group", type=int),
        "functional_subgroup_id": request.args.get("functional_subgroup", type=int),
        "turbine_platform_code": request.args.get("turbine_platform") or None,
        "lifecycle_status": request.args.get("lifecycle_status") or None,
    }
    try:
        options = export_options_from_request(allow_audience=False)
        revisions = ExportService.working_set_revisions(current_user, **filters)
        result = ExportService.export_catalogue(
            revisions,
            export_format,
            current_user,
            scope={"scope": "working-set", **{k: v for k, v in filters.items() if v is not None}},
            notice=WORKING_SET_NOTICE,
            options=options,
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return file_response(result)


@api_v1_bp.post("/exports/full-database")
@require_role("ADMINISTRATOR")
def export_full_database():
    """I-17: a POST carrying `current_password`, so the download needs a fresh confirmation."""
    body = request.get_json(silent=True) or {}
    try:
        content, mimetype, filename = ExportService.export_full_database(
            current_user,
            reauth_password=body.get("current_password") or request.form.get("current_password"),
        )
    except (StepUpRequiredError, AccountLockedError) as exc:
        return error_response(exc)
    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

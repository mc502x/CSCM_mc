"""FR-045-FR-047, SEC-015. See docs/artifacts/openapi.yaml
/releases/{releaseId}/export and /exports/full-database."""

from flask import Response, jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.decorators import current_user, login_required, require_role
from app.db_modes import writes_on_get
from app.domain.errors import NotFoundError
from app.services.export_service import ExportService
from app.services.release_service import ReleaseService

_VALID_FORMATS = {"csv", "json", "xlsx", "pdf"}
WORKING_SET_NOTICE = "Not for distribution - unapproved data"


@api_v1_bp.get("/releases/<int:release_id>/export")
@writes_on_get
@login_required
def export_release(release_id: int):
    export_format = (request.args.get("format") or "").lower()
    if export_format not in _VALID_FORMATS:
        return (
            jsonify(error="validation_error", message="format must be csv, json, xlsx, or pdf"),
            422,
        )
    try:
        release = ReleaseService.get(release_id)
    except NotFoundError:
        return jsonify(error="not_found", message="Release not found"), 404

    revisions = [item.revision for item in release.items]
    content, mimetype, filename = ExportService.export_catalogue(
        revisions,
        export_format,
        current_user,
        release_id=release_id,
        name_label=release.version_label,
    )
    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _format_or_error():
    export_format = (request.args.get("format") or "").lower()
    if export_format not in _VALID_FORMATS:
        return None, (
            jsonify(error="validation_error", message="format must be csv, json, xlsx, or pdf"),
            422,
        )
    return export_format, None


def _file_response(content, mimetype, filename):
    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@api_v1_bp.get("/exports/released")
@writes_on_get
@login_required
def export_released():
    """FR-045: the current set of all Released codes (any role; Released data
    is visible to Viewers, BR-009). Optional functional_system_group,
    functional_subgroup, turbine_platform filters."""
    export_format, error = _format_or_error()
    if error:
        return error
    filters = {
        "functional_system_group_id": request.args.get("functional_system_group", type=int),
        "functional_subgroup_id": request.args.get("functional_subgroup", type=int),
        "turbine_platform_code": request.args.get("turbine_platform") or None,
    }
    revisions = ExportService.released_revisions(**filters)
    return _file_response(
        *ExportService.export_catalogue(
            revisions,
            export_format,
            current_user,
            scope={"scope": "released", **{k: v for k, v in filters.items() if v is not None}},
        )
    )


@api_v1_bp.get("/exports/working-set")
@writes_on_get
@require_role("ENGINEER", "REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER")
def export_working_set():
    """FR-046: ad-hoc filtered working set, any lifecycle state, labelled
    "Not for distribution — unapproved data"; never available to Viewers."""
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
    revisions = ExportService.working_set_revisions(current_user, **filters)
    return _file_response(
        *ExportService.export_catalogue(
            revisions,
            export_format,
            current_user,
            scope={"scope": "working-set", **{k: v for k, v in filters.items() if v is not None}},
            notice=WORKING_SET_NOTICE,
        )
    )


@api_v1_bp.get("/exports/full-database")
@writes_on_get
@require_role("ADMINISTRATOR")
def export_full_database():
    content, mimetype, filename = ExportService.export_full_database(current_user)
    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

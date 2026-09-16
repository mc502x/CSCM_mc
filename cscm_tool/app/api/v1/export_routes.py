"""FR-045-FR-047, SEC-015. See docs/artifacts/openapi.yaml
/releases/{releaseId}/export and /exports/full-database."""

from flask import Response, jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.decorators import current_user, login_required, require_role
from app.domain.errors import NotFoundError
from app.services.export_service import ExportService
from app.services.release_service import ReleaseService

_VALID_FORMATS = {"csv", "json", "pdf"}


@api_v1_bp.get("/releases/<int:release_id>/export")
@login_required
def export_release(release_id: int):
    export_format = (request.args.get("format") or "").lower()
    if export_format not in _VALID_FORMATS:
        return jsonify(error="validation_error", message="format must be csv, json, or pdf"), 422
    try:
        release = ReleaseService.get(release_id)
    except NotFoundError:
        return jsonify(error="not_found", message="Release not found"), 404

    revisions = [item.revision for item in release.items]
    content, mimetype, filename = ExportService.export_catalogue(
        revisions, export_format, current_user, release_id=release_id
    )
    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@api_v1_bp.get("/exports/full-database")
@require_role("ADMINISTRATOR")
def export_full_database():
    content, mimetype, filename = ExportService.export_full_database(current_user)
    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

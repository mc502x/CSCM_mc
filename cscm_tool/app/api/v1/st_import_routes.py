"""FR-048o..FR-048w: status code import from the generated StCd_<n>.st programs, and the legacy ->
new mapping. See docs/artifacts/openapi.yaml /imports/st*, /legacy-mapping*."""

from flask import Response, jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1._errors import error_response
from app.api.v1.serializers import import_job_payload
from app.auth.decorators import current_user, require_role
from app.domain.errors import DomainError
from app.services.legacy_mapping_service import LegacyMappingService
from app.services.st_import_service import StImportService

_IMPORT_ROLES = ("ADMINISTRATOR", "ENGINEER")
# Titles and states of Drafts are not for Viewers (SEC-006), so the mapping is internal.
_MAPPING_ROLES = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _options_from(source) -> dict:
    options = {"controller": source.get("controller")}
    platforms = source.get("platforms")
    if platforms:
        options["platforms"] = platforms
    return options


@api_v1_bp.post("/imports/st/preview")
@require_role(*_IMPORT_ROLES)
def preview_st_import():
    """Upload `StCd_<n>.st` files (repeat the `files` field) or a ZIP of them; nothing is
    created. The answer lists every program with its state (ready, exists, blocked), the
    legacy -> new number, the placement and the problems, plus a `token` for the confirmation.
    Form fields: `controller` (auto | MC | HC), `platforms` (comma separated). The title, the
    type and the access levels come from the mapping (`/mapping`), never from the upload."""
    uploads = [(f.filename or "upload", f.read()) for f in request.files.getlist("files") if f]
    uploads += [(f.filename or "upload", f.read()) for f in request.files.getlist("file") if f]
    if not uploads:
        return jsonify(error="validation_error", message="files are required"), 422
    try:
        return jsonify(StImportService.preview(uploads, current_user, _options_from(request.form)))
    except (DomainError, ValueError) as exc:
        return error_response(exc)


@api_v1_bp.post("/imports/st")
@require_role(*_IMPORT_ROLES)
def create_st_import():
    """Confirm a preview: JSON `{token, selected?, categories?, change_set_name?, async?}`.
    `selected` is a list of the item keys to import (default: every item that is ready);
    `categories` maps item keys to the status category of that program. Every chosen program
    becomes a Draft; all of them join one new change set. 202 with the import job."""
    body = request.get_json(silent=True) or {}
    token = body.get("token")
    selected = body.get("selected")
    if not isinstance(token, str) or not token:
        return jsonify(error="validation_error", message="token is required"), 422
    if selected is not None and not (
        isinstance(selected, list) and all(isinstance(k, str) for k in selected)
    ):
        return jsonify(error="validation_error", message="selected must be a list of keys"), 422
    try:
        job = StImportService.confirm(
            token,
            current_user,
            selected,
            change_set_name=body.get("change_set_name"),
            asynchronous=True if body.get("async") else None,
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(import_job_payload(job)), 202


@api_v1_bp.get("/status-codes/<int:status_code_id>/import-source")
@require_role(*_MAPPING_ROLES)
def status_code_import_source(status_code_id: int):
    """Where an imported code came from: file, SHA-256, program and every parsed attribute."""
    try:
        return jsonify(StImportService.source_of(status_code_id))
    except DomainError as exc:
        return error_response(exc)


@api_v1_bp.get("/legacy-mapping")
@require_role(*_MAPPING_ROLES)
def legacy_mapping():
    """Legacy number -> new identifier. Filters: `controller` (MC | HC), `q`, `state` (issued |
    reserved | pending). Legacy -> new only: the new library is larger than the old one, so
    there is no reverse lookup; `summary.new_without_legacy` counts the codes with no legacy
    number."""
    controller = request.args.get("controller")
    if controller and controller.upper() not in ("MC", "HC"):
        return jsonify(error="validation_error", message="controller must be MC or HC"), 422
    state = request.args.get("state")
    if state and state not in ("issued", "reserved", "pending"):
        return (
            jsonify(error="validation_error", message="state must be issued, reserved or pending"),
            422,
        )
    entries = LegacyMappingService.entries(controller, request.args.get("q"), state)
    return jsonify(summary=LegacyMappingService.summary(), entries=entries)


@api_v1_bp.get("/legacy-mapping/export")
@require_role(*_MAPPING_ROLES)
def legacy_mapping_export():
    """The mapping as CSV (default) or XLSX, with the same filters as the list."""
    fmt = (request.args.get("format") or "csv").lower()
    if fmt not in ("csv", "xlsx"):
        return jsonify(error="validation_error", message="format must be csv or xlsx"), 422
    entries = LegacyMappingService.entries(
        request.args.get("controller"), request.args.get("q"), request.args.get("state")
    )
    if fmt == "xlsx":
        return Response(
            LegacyMappingService.export_xlsx(entries),
            mimetype=_XLSX,
            headers={"Content-Disposition": "attachment; filename=legacy_to_new_status_codes.xlsx"},
        )
    return Response(
        LegacyMappingService.export_csv(entries),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=legacy_to_new_status_codes.csv"},
    )

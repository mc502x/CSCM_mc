"""Publication of the catalogue (docs/21-improvement-ideas.md): export profiles (I-02) and
audiences (I-03), manifests, verification, release notes and history (I-06), software-version
matrix and Release targets (I-07), translations (I-15) and the offline bundle (I-24).

The existing export endpoints in export_routes.py share `export_options_from_request`
defined here, so every export accepts the same shaping parameters."""

import json

from flask import Response, jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1._errors import error_response
from app.auth.decorators import current_user, login_required, require_role
from app.db_modes import writes_on_get
from app.domain.errors import DomainError, NotFoundError
from app.services import manifest_service
from app.services.audience_service import AUDIENCES, validate_audience
from app.services.export_profile_service import ExportProfileService, parse_columns
from app.services.export_service import ExportOptions, ExportService
from app.services.release_service import ReleaseService
from app.services.software_version_service import SoftwareVersionService
from app.services.translation_service import TranslationService

_WORKING = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")


def _body() -> dict:
    return request.get_json(silent=True) or {}


def export_options_from_request(*, allow_audience: bool = True) -> ExportOptions:
    """profile / audience / language / strict_language / software_version / bundle query
    parameters. Raises DomainError/ValueError/NotFoundError for bad values."""
    profile = None
    if request.args.get("profile"):
        profile = ExportProfileService.get_by_code(request.args["profile"])
    audience = validate_audience(request.args.get("audience"))
    if audience and not allow_audience:
        raise ValueError("An audience cannot be applied to the unapproved working set.")
    return ExportOptions(
        profile=profile,
        audience=audience,
        language=request.args.get("language") or None,
        strict_language=request.args.get("strict_language") == "true",
        software_version=request.args.get("software_version") or None,
        bundle=request.args.get("bundle") == "true",
    )


def file_response(result) -> Response:
    return Response(
        result.content,
        mimetype=result.mimetype,
        headers={
            "Content-Disposition": f"attachment; filename={result.filename}",
            "X-Content-SHA256": result.sha256,
        },
    )


# ---------------------------------------------------------------- profiles / audiences
def profile_payload(profile) -> dict:
    return {
        "id": profile.id,
        "code": profile.code,
        "name": profile.name,
        "description": profile.description,
        "columns": parse_columns(profile.columns),
        "language": profile.language_code,
        "audience": profile.audience,
        "title_page": bool(profile.title_page),
        "pdf_orientation": profile.pdf_orientation,
        "is_active": bool(profile.is_active),
    }


@api_v1_bp.get("/export-profiles")
@login_required
def list_export_profiles():
    include_inactive = request.args.get("include_inactive") == "true" and (
        current_user.role_code == "ADMINISTRATOR"
    )
    return jsonify(
        items=[
            profile_payload(p)
            for p in ExportProfileService.list_all(include_inactive=include_inactive)
        ]
    )


@api_v1_bp.post("/export-profiles")
@require_role("ADMINISTRATOR")
def create_export_profile():
    try:
        profile = ExportProfileService.create(_body(), current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(profile_payload(profile)), 201


@api_v1_bp.patch("/export-profiles/<int:profile_id>")
@require_role("ADMINISTRATOR")
def update_export_profile(profile_id: int):
    try:
        profile = ExportProfileService.update(profile_id, _body(), current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(profile_payload(profile))


@api_v1_bp.get("/audiences")
@login_required
def list_audiences():
    return jsonify(
        items=[{"code": code, "label": label} for code, (_a, label) in AUDIENCES.items()]
    )


# ---------------------------------------------------------------- release extras
def _published_release(release_id: int):
    release = ReleaseService.get(release_id)
    return release


@api_v1_bp.get("/releases/<int:release_id>/notes")
@writes_on_get
@login_required
def release_notes(release_id: int):
    """I-06: added / changed / deprecated against the previous published Release."""
    fmt = (request.args.get("format") or "json").lower()
    if fmt not in ("md", "csv", "pdf", "json"):
        return jsonify(error="validation_error", message="format must be md, csv, pdf or json"), 422
    try:
        release = _published_release(release_id)
        if release.status != "PUBLISHED" and current_user.role_code != "ADMINISTRATOR":
            raise NotFoundError("Release not found")
        result = ExportService.export_release_notes(
            release, fmt, current_user, bundle=request.args.get("bundle") == "true"
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return file_response(result)


@api_v1_bp.get("/releases/<int:release_id>/offline-bundle")
@writes_on_get
@login_required
def release_offline_bundle(release_id: int):
    """I-24: self-contained HTML lookup page for service technicians."""
    try:
        release = _published_release(release_id)
        if release.status != "PUBLISHED":
            return jsonify(error="conflict", message="Only a published Release can be bundled"), 409
        options = export_options_from_request()
        result = ExportService.export_offline_bundle(release, current_user, options)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return file_response(result)


@api_v1_bp.get("/releases/<int:release_id>/exports")
@require_role(*_WORKING)
def release_export_history(release_id: int):
    """Every export recorded for a Release with its hash (I-06)."""
    try:
        _published_release(release_id)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(
        items=[
            {
                "id": job.id,
                "export_type": job.export_type,
                "scope_type": job.export_scope_type,
                "sha256": job.sha256,
                "size_bytes": job.size_bytes,
                "row_count": job.row_count,
                "profile": job.profile_code,
                "audience": job.audience,
                "language": job.language_code,
                "software_version": job.software_version_code,
                "requested_by": job.requested_by,
                "created_at": job.created_at,
            }
            for job in ExportService.history(release_id)
        ]
    )


@api_v1_bp.get("/exports/<int:job_id>/manifest")
@require_role(*_WORKING)
def export_manifest(job_id: int):
    from app.extensions import db
    from app.models.export_job import ExportJob

    job = db.session.get(ExportJob, job_id)
    if job is None or not job.manifest:
        return jsonify(error="not_found", message="No manifest for this export"), 404
    return Response(job.manifest, mimetype="application/json")


@api_v1_bp.post("/exports/verify")
@login_required
def verify_export():
    """I-06: is this file one the system produced? Upload `file`; optionally `manifest`
    (a MANIFEST.json) to check it offline-style. Reports the hash, the matching recorded
    exports and the manifest signature state."""
    upload = request.files.get("file")
    if upload is None:
        return (
            jsonify(error="validation_error", message="A file upload named 'file' is required"),
            422,
        )
    content = upload.read()
    digest = manifest_service.sha256_hex(content)
    matches = ExportService.find_by_hash(digest)
    result = {
        "sha256": digest,
        "recorded": bool(matches),
        "export_job_ids": [m.id for m in matches],
    }
    manifest_upload = request.files.get("manifest")
    manifest = None
    if manifest_upload is not None:
        try:
            manifest = json.loads(manifest_upload.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return jsonify(error="validation_error", message="manifest is not valid JSON"), 422
    elif matches and matches[0].manifest:
        manifest = json.loads(matches[0].manifest)
    if manifest is not None:
        result["manifest"] = manifest_service.verify_file(content, manifest, upload.filename)
    return jsonify(result)


@api_v1_bp.put("/releases/<int:release_id>/target-versions")
@require_role("ADMINISTRATOR")
def set_release_target_versions(release_id: int):
    """I-07: the controller software versions this Release is published for."""
    try:
        release = ReleaseService.set_target_versions(
            release_id, _body().get("software_versions") or [], current_user
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(
        release_id=release.id,
        software_versions=[v.code for v in ReleaseService.target_versions(release)],
    )


# ---------------------------------------------------------------- software versions (I-07)
@api_v1_bp.get("/software-versions/matrix")
@login_required
def software_version_matrix():
    code = request.args.get("version")
    if not code:
        return jsonify(error="validation_error", message="version is required"), 422
    try:
        return jsonify(SoftwareVersionService.matrix(code))
    except (DomainError, ValueError) as exc:
        return error_response(exc)


@api_v1_bp.get("/software-versions/changes")
@login_required
def software_version_changes():
    first, last = request.args.get("from"), request.args.get("to")
    if not first or not last:
        return jsonify(error="validation_error", message="from and to are required"), 422
    try:
        return jsonify(SoftwareVersionService.changes_between(first, last))
    except (DomainError, ValueError) as exc:
        return error_response(exc)


# ---------------------------------------------------------------- translations (I-15)
def _translation_payload(row) -> dict:
    return {
        "revision_id": row.status_code_revision_id,
        "language": row.language.code,
        "status": row.translation_status,
        "title": row.title,
        "description": row.description,
        "remedy_text": row.remedy_text,
        "translated_by": row.translated_by,
        "translated_at": row.translated_at,
        "approved_by": row.approved_by,
        "approved_at": row.approved_at,
    }


@api_v1_bp.get("/revisions/<int:revision_id>/translations")
@login_required
def list_translations(revision_id: int):
    try:
        return jsonify(items=TranslationService.status_matrix(revision_id, current_user))
    except (DomainError, ValueError) as exc:
        return error_response(exc)


@api_v1_bp.put("/revisions/<int:revision_id>/translations/<language>")
@require_role("ADMINISTRATOR", "ENGINEER")
def save_translation(revision_id: int, language: str):
    body = _body()
    try:
        row = TranslationService.save(
            revision_id,
            language,
            body.get("title", ""),
            body.get("description", ""),
            body.get("remedy_text"),
            current_user,
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(_translation_payload(row))


@api_v1_bp.post("/revisions/<int:revision_id>/translations/<language>/approve")
@require_role("ADMINISTRATOR", "REVIEWER")
def approve_translation(revision_id: int, language: str):
    try:
        row = TranslationService.approve(revision_id, language, current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(_translation_payload(row))


@api_v1_bp.post("/revisions/<int:revision_id>/translations/carry-over")
@require_role("ADMINISTRATOR", "ENGINEER")
def carry_over_translations(revision_id: int):
    try:
        copied = TranslationService.carry_over(revision_id, current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(copied_languages=copied)


@api_v1_bp.get("/translations/worklist")
@require_role(*_WORKING)
def translation_worklist():
    language = request.args.get("language")
    if not language:
        return jsonify(error="validation_error", message="language is required"), 422
    try:
        return jsonify(items=TranslationService.worklist(language))
    except (DomainError, ValueError) as exc:
        return error_response(exc)

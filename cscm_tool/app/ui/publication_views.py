"""Screens for publishing the catalogue: export profiles (I-02), file verification (I-06),
release notes and the offline bundle (I-06, I-24), Release target versions (I-07) and
translations (I-15)."""

import json

from flask import Response, flash, redirect, render_template, request, url_for

from app.auth.decorators import current_user, login_required_web, require_role_web
from app.db_modes import writes_on_get
from app.domain.errors import DomainError, NotFoundError
from app.models.export_job import ExportProfile
from app.services import manifest_service
from app.services.audience_service import AUDIENCES
from app.services.export_profile_service import (
    EXPORT_FIELDS,
    ExportProfileService,
    parse_columns,
)
from app.services.export_service import ExportOptions, ExportService
from app.services.lookup_service import LookupService
from app.services.release_service import ReleaseService
from app.services.software_version_service import SoftwareVersionService
from app.services.status_code_service import StatusCodeService
from app.services.translation_service import TranslationService
from app.ui import ui_bp

_ERRORS = (DomainError, ValueError)
_WORKING = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")
_FORMATS = ("csv", "json", "xlsx", "pdf")


# ---------------------------------------------------------------- export profiles (I-02)
def _columns_from_text(text: str) -> list[dict]:
    """One `field | label` per line; a bare field uses its name as the label."""
    columns = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        field, _sep, label = line.partition("|")
        columns.append({"field": field.strip(), "label": label.strip() or field.strip()})
    return columns


def _columns_to_text(profile: ExportProfile) -> str:
    return "\n".join(f"{c['field']} | {c['label']}" for c in parse_columns(profile.columns))


@ui_bp.route("/admin/export-profiles", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR")
def export_profiles():
    if request.method == "POST":
        try:
            ExportProfileService.create(
                {
                    "code": request.form.get("code", ""),
                    "name": request.form.get("name", ""),
                    "description": request.form.get("description"),
                    "columns": _columns_from_text(request.form.get("columns", "")),
                    "audience": request.form.get("audience") or None,
                    "language": request.form.get("language") or None,
                    "pdf_orientation": request.form.get("pdf_orientation", "L"),
                    "title_page": request.form.get("title_page") == "on",
                },
                current_user,
            )
        except _ERRORS as exc:
            flash(str(exc), "error")
        else:
            flash("Export profile created.", "success")
        return redirect(url_for("ui.export_profiles"))
    return render_template(
        "admin/export_profiles.html",
        profiles=ExportProfileService.list_all(include_inactive=True),
        columns_text=_columns_to_text,
        fields=EXPORT_FIELDS,
        audiences=AUDIENCES,
        content_languages=LookupService.list_vocabulary("languages"),
    )


@ui_bp.route("/admin/export-profiles/<int:profile_id>", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def export_profile_update(profile_id):
    data: dict = {"name": request.form.get("name", "")}
    if "columns" in request.form:
        data["columns"] = _columns_from_text(request.form["columns"])
    data["audience"] = request.form.get("audience") or None
    data["language"] = request.form.get("language") or None
    data["is_active"] = request.form.get("is_active") == "on"
    data["title_page"] = request.form.get("title_page") == "on"
    data["pdf_orientation"] = request.form.get("pdf_orientation", "L")
    try:
        ExportProfileService.update(profile_id, data, current_user)
    except _ERRORS as exc:
        flash(str(exc), "error")
    else:
        flash("Export profile saved.", "success")
    return redirect(url_for("ui.export_profiles"))


# ---------------------------------------------------------------- verify a file (I-06)
@ui_bp.route("/exports/verify", methods=["POST"])
@login_required_web
def export_verify():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        flash("Choose the exported file to verify.", "error")
        return redirect(url_for("ui.export_center"))
    content = upload.read()
    digest = manifest_service.sha256_hex(content)
    matches = ExportService.find_by_hash(digest)
    manifest = None
    manifest_upload = request.files.get("manifest")
    if manifest_upload is not None and manifest_upload.filename:
        try:
            manifest = json.loads(manifest_upload.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            flash("The manifest is not valid JSON.", "error")
            return redirect(url_for("ui.export_center"))
    elif matches and matches[0].manifest:
        manifest = json.loads(matches[0].manifest)
    verification = (
        manifest_service.verify_file(content, manifest, upload.filename) if manifest else None
    )
    return render_template(
        "export_verify.html",
        filename=upload.filename,
        digest=digest,
        matches=matches,
        verification=verification,
    )


# ---------------------------------------------------------------- release extras (I-06, I-07, I-24)
@ui_bp.route("/releases/<int:release_id>/shaped-export")
@writes_on_get
@login_required_web
def release_shaped_export(release_id):
    """Release export with the chosen profile / audience / language / version (form on the
    Release page); the same pipeline as the API."""
    fmt = (request.args.get("format") or "csv").lower()
    if fmt not in _FORMATS:
        flash("Unknown export format.", "error")
        return redirect(url_for("ui.release_detail", release_id=release_id))
    try:
        release = ReleaseService.get(release_id)
        profile = (
            ExportProfileService.get_by_code(request.args["profile"])
            if request.args.get("profile")
            else None
        )
        options = ExportOptions(
            profile=profile,
            audience=request.args.get("audience") or None,
            language=request.args.get("language") or None,
            strict_language=request.args.get("strict_language") == "on",
            software_version=request.args.get("software_version") or None,
            bundle=request.args.get("bundle") == "on",
        )
        result = ExportService.export_catalogue(
            [item.revision for item in release.items],
            fmt,
            current_user,
            release_id=release_id,
            name_label=release.version_label,
            options=options,
        )
    except (NotFoundError, *_ERRORS) as exc:
        flash(str(exc), "error")
        return redirect(url_for("ui.release_detail", release_id=release_id))
    return Response(
        result.content,
        mimetype=result.mimetype,
        headers={
            "Content-Disposition": f"attachment; filename={result.filename}",
            "X-Content-SHA256": result.sha256,
        },
    )


@ui_bp.route("/releases/<int:release_id>/notes")
@writes_on_get
@login_required_web
def release_notes_download(release_id):
    fmt = (request.args.get("format") or "md").lower()
    try:
        release = ReleaseService.get(release_id)
        if release.status != "PUBLISHED" and current_user.role_code != "ADMINISTRATOR":
            raise NotFoundError("Release not found")
        result = ExportService.export_release_notes(
            release, fmt, current_user, bundle=request.args.get("bundle") == "on"
        )
    except (NotFoundError, *_ERRORS) as exc:
        flash(str(exc), "error")
        return redirect(url_for("ui.release_detail", release_id=release_id))
    return Response(
        result.content,
        mimetype=result.mimetype,
        headers={
            "Content-Disposition": f"attachment; filename={result.filename}",
            "X-Content-SHA256": result.sha256,
        },
    )


@ui_bp.route("/releases/<int:release_id>/offline-bundle")
@writes_on_get
@login_required_web
def release_offline_bundle_download(release_id):
    try:
        release = ReleaseService.get(release_id)
        if release.status != "PUBLISHED":
            raise DomainError("Only a published Release can be bundled.")
        options = ExportOptions(
            audience=request.args.get("audience") or None,
            language=request.args.get("language") or None,
            software_version=request.args.get("software_version") or None,
            bundle=request.args.get("bundle") == "on",
        )
        result = ExportService.export_offline_bundle(release, current_user, options)
    except (NotFoundError, *_ERRORS) as exc:
        flash(str(exc), "error")
        return redirect(url_for("ui.release_detail", release_id=release_id))
    return Response(
        result.content,
        mimetype=result.mimetype,
        headers={
            "Content-Disposition": f"attachment; filename={result.filename}",
            "X-Content-SHA256": result.sha256,
        },
    )


@ui_bp.route("/releases/<int:release_id>/target-versions", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def release_target_versions(release_id):
    try:
        ReleaseService.set_target_versions(
            release_id, request.form.getlist("software_versions"), current_user
        )
    except (NotFoundError, *_ERRORS) as exc:
        flash(str(exc), "error")
    else:
        flash("Target software versions saved.", "success")
    return redirect(url_for("ui.release_builder", release_id=release_id))


@ui_bp.route("/software-versions")
@login_required_web
def software_version_matrix():
    version = request.args.get("version")
    other = request.args.get("compare_to")
    matrix = changes = None
    try:
        if version and other:
            changes = SoftwareVersionService.changes_between(version, other)
        elif version:
            matrix = SoftwareVersionService.matrix(version)
    except (NotFoundError, *_ERRORS) as exc:
        flash(str(exc), "error")
    return render_template(
        "software_versions.html",
        versions=SoftwareVersionService.ordered(),
        version=version,
        other=other,
        matrix=matrix,
        changes=changes,
    )


# ---------------------------------------------------------------- translations (I-15)
@ui_bp.route("/status-codes/<int:status_code_id>/translations", methods=["GET", "POST"])
@login_required_web
def status_code_translations(status_code_id):
    try:
        revision = StatusCodeService.get_current_revision(status_code_id, current_user)
    except NotFoundError:
        flash("Status code not found.", "error")
        return redirect(url_for("ui.status_code_list"))
    # translations belong to the latest decided revision, which is what readers see
    target = StatusCodeService._repo.get_latest_revision_in_states(
        status_code_id, ("RELEASED", "APPROVED", "DEPRECATED")
    )
    if request.method == "POST" and target is not None:
        language = request.form.get("language", "")
        action = request.form.get("action", "save")
        try:
            if action == "approve":
                TranslationService.approve(target.id, language, current_user)
                flash("Translation approved.", "success")
            elif action == "carry":
                copied = TranslationService.carry_over(target.id, current_user)
                flash(
                    (
                        f"Copied {', '.join(copied)} from the previous revision as drafts."
                        if copied
                        else "Nothing to copy."
                    ),
                    "success" if copied else "info",
                )
            else:
                TranslationService.save(
                    target.id,
                    language,
                    request.form.get("title", ""),
                    request.form.get("description", ""),
                    request.form.get("remedy_text"),
                    current_user,
                )
                flash("Translation saved as a draft.", "success")
        except _ERRORS as exc:
            flash(str(exc), "error")
        return redirect(url_for("ui.status_code_translations", status_code_id=status_code_id))
    matrix = TranslationService.status_matrix(target.id, current_user) if target else []
    return render_template(
        "status_codes/translations.html", revision=revision, target=target, matrix=matrix
    )

"""S19 Library Import, plus the migration toolkit (I-05): template download, validate-only run,
update mode, progress of background jobs (I-32) and the reconciliation report. S39 imports status
codes from generated StCd_<n>.st programs (preview, multi-select, confirm); S40 shows the legacy ->
new mapping."""

from flask import (
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from app.api.v1.serializers import import_job_payload
from app.auth.decorators import current_user, require_role_web
from app.domain.errors import DomainError
from app.extensions import db
from app.i18n import translate as _
from app.models.lookup import LookupTurbinePlatform
from app.services.import_service import ImportService
from app.services.legacy_mapping_service import LegacyMappingService
from app.services.st_import_service import StImportService
from app.ui import ui_bp

_ROLES = ("ADMINISTRATOR", "ENGINEER")
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@ui_bp.route("/imports/new", methods=["GET", "POST"])
@require_role_web(*_ROLES)
def import_new():
    if request.method == "POST":
        upload = request.files.get("file")
        mode = request.form.get("mode", "CREATE")
        if upload is None or not upload.filename:
            flash(_("Choose a .csv or .xlsx file to upload."), "error")
        else:
            try:
                if request.form.get("action") == "validate":
                    report = ImportService.dry_run(
                        upload.filename, upload.read(), current_user, mode
                    )
                    return render_template(
                        "imports/dry_run.html", report=report, filename=upload.filename
                    )
                job = ImportService.process_upload(
                    upload.filename, upload.read(), current_user, mode=mode
                )
            except (DomainError, ValueError) as exc:
                flash(_(str(exc)), "error")
            else:
                return redirect(url_for("ui.import_detail", import_job_id=job.id))

    return render_template("imports/new.html")


@ui_bp.route("/imports/template.<fmt>")
@require_role_web(*_ROLES)
def import_template(fmt):
    if fmt == "csv":
        return Response(
            ImportService.template_csv(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=cscm_import_template.csv"},
        )
    if fmt == "xlsx":
        return Response(
            ImportService.template_xlsx(),
            mimetype=_XLSX,
            headers={"Content-Disposition": "attachment; filename=cscm_import_template.xlsx"},
        )
    flash(_("Unknown template format."), "error")
    return redirect(url_for("ui.import_new"))


@ui_bp.route("/imports/<int:import_job_id>")
@require_role_web(*_ROLES)
def import_detail(import_job_id):
    job = ImportService.get(import_job_id)
    if job is None:
        flash(_("Import job not found."), "error")
        return redirect(url_for("ui.import_new"))
    return render_template("imports/detail.html", job=job, progress=import_job_payload(job))


@ui_bp.route("/imports/<int:import_job_id>/progress")
@require_role_web(*_ROLES)
def import_progress(import_job_id):
    job = ImportService.get(import_job_id)
    if job is None:
        return jsonify(error="not_found"), 404
    return jsonify(import_job_payload(job))


@ui_bp.route("/imports/<int:import_job_id>/errors")
@require_role_web(*_ROLES)
def import_errors(import_job_id):
    job = ImportService.get(import_job_id)
    if job is None or not job.error_report_reference:
        flash(_("No error report available for this import job."), "error")
        return redirect(url_for("ui.import_new"))
    if request.args.get("format") == "xlsx" and job.error_report_xlsx_reference:
        return send_file(
            job.error_report_xlsx_reference,
            mimetype=_XLSX,
            as_attachment=True,
            download_name=f"import_{import_job_id}_errors.xlsx",
        )
    return send_file(
        job.error_report_reference,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"import_{import_job_id}_errors.csv",
    )


@ui_bp.route("/imports/reconciliation", methods=["GET", "POST"])
@require_role_web(*_ROLES)
def import_reconciliation():
    numbers = None
    expected_total = request.args.get("expected_total", type=int) or request.form.get(
        "expected_total", type=int
    )
    if request.method == "POST":
        upload = request.files.get("file")
        if upload is not None and upload.filename:
            from app.api.v1.import_routes import _legacy_numbers_from_upload

            try:
                numbers = _legacy_numbers_from_upload(upload)
            except (ValueError, UnicodeDecodeError, OSError) as exc:
                flash(f"The master list could not be read: {exc}", "error")
    report = ImportService.reconciliation(
        expected_legacy_references=numbers, expected_total=None if numbers else expected_total
    )
    return render_template("imports/reconciliation.html", report=report)


# ------------------------------------------------------------------ S39 status codes from .st files
def _st_options() -> dict:
    return {
        "controller": request.form.get("controller"),
        "platforms": request.form.getlist("platforms"),
    }


@ui_bp.route("/imports/st", methods=["GET", "POST"])
@require_role_web(*_ROLES)
def st_import_new():
    if request.method == "POST":
        uploads = [
            (f.filename or "upload", f.read()) for f in request.files.getlist("files") if f.filename
        ]
        if not uploads:
            flash(_("Choose the .st files, a folder or a ZIP to read."), "error")
        else:
            try:
                preview = StImportService.preview(uploads, current_user, _st_options())
            except (DomainError, ValueError) as exc:
                flash(_(str(exc)), "error")
            else:
                return render_template("imports/st_preview.html", preview=preview)
    platforms = db.session.query(LookupTurbinePlatform).filter_by(is_active=1).all()
    return render_template("imports/st_new.html", platforms=platforms)


@ui_bp.route("/imports/st/confirm", methods=["POST"])
@require_role_web(*_ROLES)
def st_import_confirm():
    try:
        job = StImportService.confirm(
            request.form.get("token", ""),
            current_user,
            request.form.getlist("selected"),
            change_set_name=request.form.get("change_set_name"),
        )
    except (DomainError, ValueError) as exc:
        flash(_(str(exc)), "error")
        return redirect(url_for("ui.st_import_new"))
    return redirect(url_for("ui.import_detail", import_job_id=job.id))


@ui_bp.route("/imports/st/cancel", methods=["POST"])
@require_role_web(*_ROLES)
def st_import_cancel():
    try:
        StImportService.discard(request.form.get("token", ""), current_user)
    except DomainError as exc:
        flash(_(str(exc)), "error")
    return redirect(url_for("ui.st_import_new"))


# ------------------------------------------------------------------ S40 legacy -> new mapping
_MAPPING_ROLES = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")


def _mapping_filters() -> dict:
    controller = (request.args.get("controller") or "").upper()
    state = request.args.get("state") or ""
    return {
        "controller": controller if controller in ("MC", "HC") else "",
        "state": state if state in ("issued", "reserved", "pending") else "",
        "q": (request.args.get("q") or "").strip(),
    }


@ui_bp.route("/legacy-mapping")
@require_role_web(*_MAPPING_ROLES)
def legacy_mapping():
    filters = _mapping_filters()
    return render_template(
        "imports/legacy_mapping.html",
        entries=LegacyMappingService.entries(
            filters["controller"] or None, filters["q"], filters["state"] or None
        ),
        summary=LegacyMappingService.summary(),
        filters=filters,
    )


@ui_bp.route("/legacy-mapping/export.<fmt>")
@require_role_web(*_MAPPING_ROLES)
def legacy_mapping_export(fmt):
    filters = _mapping_filters()
    entries = LegacyMappingService.entries(
        filters["controller"] or None, filters["q"], filters["state"] or None
    )
    if fmt == "xlsx":
        return Response(
            LegacyMappingService.export_xlsx(entries),
            mimetype=_XLSX,
            headers={"Content-Disposition": "attachment; filename=legacy_to_new_status_codes.xlsx"},
        )
    if fmt == "csv":
        return Response(
            LegacyMappingService.export_csv(entries),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=legacy_to_new_status_codes.csv"},
        )
    flash(_("Unknown export format."), "error")
    return redirect(url_for("ui.legacy_mapping"))

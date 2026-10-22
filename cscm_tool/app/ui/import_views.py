"""S19 Library Import."""

from flask import flash, redirect, render_template, request, send_file, url_for

from app.auth.decorators import current_user, require_role_web
from app.services.import_service import ImportService
from app.ui import ui_bp


@ui_bp.route("/imports/new", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def import_new():
    if request.method == "POST":
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            flash("Choose a .csv or .xlsx file to upload.", "error")
        else:
            try:
                job = ImportService.process_upload(upload.filename, upload.read(), current_user)
            except ValueError as exc:
                flash(str(exc), "error")
            else:
                return redirect(url_for("ui.import_detail", import_job_id=job.id))

    return render_template("imports/new.html")


@ui_bp.route("/imports/<int:import_job_id>")
@require_role_web("ADMINISTRATOR", "ENGINEER")
def import_detail(import_job_id):
    job = ImportService.get(import_job_id)
    if job is None:
        flash("Import job not found.", "error")
        return redirect(url_for("ui.import_new"))
    return render_template("imports/detail.html", job=job)


@ui_bp.route("/imports/<int:import_job_id>/errors")
@require_role_web("ADMINISTRATOR", "ENGINEER")
def import_errors(import_job_id):
    job = ImportService.get(import_job_id)
    if job is None or not job.error_report_reference:
        flash("No error report available for this import job.", "error")
        return redirect(url_for("ui.import_new"))
    return send_file(
        job.error_report_reference,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"import_{import_job_id}_errors.csv",
    )

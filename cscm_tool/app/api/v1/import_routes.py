"""FR-048a-d, EPIC-14. See docs/artifacts/openapi.yaml /imports*."""

from flask import jsonify, request, send_file

from app.api.v1 import api_v1_bp
from app.api.v1.serializers import import_job_payload
from app.auth.decorators import current_user, require_role
from app.services.import_service import ImportService


@api_v1_bp.get("/imports")
@require_role("ADMINISTRATOR", "ENGINEER")
def list_imports():
    jobs = ImportService.list_jobs()
    return jsonify([import_job_payload(j) for j in jobs])


@api_v1_bp.post("/imports")
@require_role("ADMINISTRATOR", "ENGINEER")
def create_import():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify(error="validation_error", message="file is required"), 422

    try:
        job = ImportService.process_upload(upload.filename, upload.read(), current_user)
    except ValueError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return jsonify(import_job_payload(job)), 202


@api_v1_bp.get("/imports/<int:import_job_id>")
@require_role("ADMINISTRATOR", "ENGINEER")
def get_import(import_job_id: int):
    job = ImportService.get(import_job_id)
    if job is None:
        return jsonify(error="not_found", message="Import job not found"), 404
    return jsonify(import_job_payload(job))


@api_v1_bp.get("/imports/<int:import_job_id>/errors")
@require_role("ADMINISTRATOR", "ENGINEER")
def get_import_errors(import_job_id: int):
    job = ImportService.get(import_job_id)
    if job is None:
        return jsonify(error="not_found", message="Import job not found"), 404
    if not job.error_report_reference:
        return jsonify(error="not_found", message="No error report for this import job"), 404
    return send_file(
        job.error_report_reference,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"import_{import_job_id}_errors.csv",
    )

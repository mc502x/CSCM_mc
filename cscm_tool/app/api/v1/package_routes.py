"""FR-173, FR-174: the baseline of a Release and the all-languages / all-access-levels package.
See docs/artifacts/openapi.yaml /releases/{releaseId}/baseline, /readiness, /packages."""

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1._errors import error_response
from app.api.v1.publication_routes import file_response
from app.auth.decorators import current_user, login_required, require_role
from app.domain.errors import DomainError, NotFoundError
from app.services.baseline_service import BaselineService
from app.services.package_service import PackageRequest, PackageService
from app.services.release_service import ReleaseService

READINESS_ROLES = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER", "STCD_OWNER")


def _release_or_404(release_id: int):
    try:
        return ReleaseService.get(release_id), None
    except NotFoundError:
        return None, (jsonify(error="not_found", message="Release not found"), 404)


@api_v1_bp.get("/releases/<int:release_id>/baseline")
@login_required
def release_baseline(release_id: int):
    """Counts of the complete set of codes valid as of this Release (by controller, platform)."""
    release, error = _release_or_404(release_id)
    if error:
        return error
    return jsonify(BaselineService.summary(release))


@api_v1_bp.get("/releases/<int:release_id>/readiness")
@require_role(*READINESS_ROLES)
def release_readiness(release_id: int):
    release, error = _release_or_404(release_id)
    if error:
        return error
    return jsonify(BaselineService.readiness(release))


def _package_request(body: dict) -> PackageRequest:
    def listed(key: str) -> tuple[str, ...]:
        value = body.get(key) or ()
        if isinstance(value, str):
            value = [v for v in value.split(",") if v]
        return tuple(str(v) for v in value)

    return PackageRequest(
        formats=listed("formats") or ("csv", "xlsx", "pdf"),
        languages=listed("languages"),
        audiences=listed("audiences"),
        include_unfiltered=body.get("include_unfiltered", True) is not False,
        platform=body.get("platform") or None,
        controller=body.get("controller") or None,
        strict_language=body.get("strict_language") is True,
    )


@api_v1_bp.post("/releases/<int:release_id>/packages")
@login_required
def create_package(release_id: int):
    """Starts building the ZIP; 202 with the job while it runs, 201 when it is already done."""
    release, error = _release_or_404(release_id)
    if error:
        return error
    try:
        job = PackageService.request(
            release, current_user, _package_request(request.get_json(silent=True) or {})
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(PackageService.status(job)), (201 if job.status == "COMPLETE" else 202)


@api_v1_bp.get("/releases/<int:release_id>/packages")
@login_required
def list_packages(release_id: int):
    release, error = _release_or_404(release_id)
    if error:
        return error
    return jsonify(items=[PackageService.status(j) for j in PackageService.packages_of(release.id)])


@api_v1_bp.get("/packages/<int:job_id>")
@login_required
def package_status(job_id: int):
    try:
        return jsonify(PackageService.status(PackageService.get(job_id)))
    except NotFoundError as exc:
        return error_response(exc)


@api_v1_bp.get("/packages/<int:job_id>/download")
@login_required
def package_download(job_id: int):
    from app.services.export_service import ExportResult

    try:
        job = PackageService.get(job_id)
        content, filename = PackageService.content(job, current_user)
    except (DomainError, NotFoundError) as exc:
        return error_response(exc)
    return file_response(
        ExportResult(content, "application/zip", filename, job.sha256 or "", {}, job.id)
    )

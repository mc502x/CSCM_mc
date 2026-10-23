"""S17 Export Center. Catalogue export is per-Release (see releases/detail.html);
this page is the entry point plus the Administrator-only full-database export."""

from flask import Response, flash, redirect, render_template, request, url_for

from app.auth.decorators import current_user, login_required_web, require_role_web
from app.domain.errors import AccountLockedError, StepUpRequiredError
from app.services.export_service import ExportService
from app.services.release_service import ReleaseService
from app.ui import ui_bp


@ui_bp.route("/exports")
@login_required_web
def export_center():
    from app.services.audience_service import AUDIENCES
    from app.services.export_profile_service import ExportProfileService

    releases = [r for r in ReleaseService.list_all() if r.status == "PUBLISHED"]
    return render_template(
        "export_center.html",
        releases=releases,
        profiles=ExportProfileService.list_all(),
        audiences=AUDIENCES,
    )


@ui_bp.route("/exports/full-database", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def export_full_database():
    """I-17: the full-database download is a POST that carries the Administrator's password."""
    try:
        content, mimetype, filename = ExportService.export_full_database(
            current_user, reauth_password=request.form.get("current_password")
        )
    except (StepUpRequiredError, AccountLockedError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("ui.export_center"))
    return Response(
        content,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

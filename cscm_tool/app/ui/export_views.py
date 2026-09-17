"""S17 Export Center. Catalogue export is per-Release (see releases/detail.html);
this page is the entry point plus the Administrator-only full-database export."""

from flask import render_template

from app.auth.decorators import login_required_web
from app.services.release_service import ReleaseService
from app.ui import ui_bp


@ui_bp.route("/exports")
@login_required_web
def export_center():
    releases = [r for r in ReleaseService.list_all() if r.status == "PUBLISHED"]
    return render_template("export_center.html", releases=releases)

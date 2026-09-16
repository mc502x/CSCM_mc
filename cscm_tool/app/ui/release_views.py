"""S11 Release List, S12 Release Builder, S13 Release Detail."""

from flask import flash, redirect, render_template, request, url_for

from app.api.v1.serializers import release_payload, revision_payload
from app.auth.decorators import current_user, login_required_web, require_role_web
from app.domain.errors import DomainError, InvalidTransitionError, NotFoundError
from app.services.lookup_service import LookupService
from app.services.release_service import ReleaseService
from app.ui import ui_bp


@ui_bp.route("/releases")
@login_required_web
def release_list():
    releases = ReleaseService.list_all()
    return render_template("releases/list.html", releases=[release_payload(r) for r in releases])


@ui_bp.route("/releases/new", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR")
def release_new():
    if request.method == "POST":
        name = request.form.get("name", "")
        version_label = request.form.get("version_label", "")
        scope_group = request.form.get("scope_functional_system_group") or None
        scope_filter = {"functional_system_group": scope_group} if scope_group else {}
        if not name or not version_label:
            flash("Name and version label are required.", "error")
        else:
            release = ReleaseService.create(
                {
                    "name": name,
                    "version_label": version_label,
                    "description": request.form.get("description") or None,
                    "scope_filter": scope_filter,
                },
                current_user,
            )
            flash("Release created.", "success")
            return redirect(url_for("ui.release_builder", release_id=release.id))

    groups = LookupService.list_vocabulary("functional-system-groups")
    return render_template("releases/new.html", groups=groups)


@ui_bp.route("/releases/<int:release_id>")
@login_required_web
def release_detail(release_id):
    try:
        release = ReleaseService.get(release_id)
    except NotFoundError:
        flash("Release not found.", "error")
        return redirect(url_for("ui.release_list"))
    return render_template("releases/detail.html", release=release_payload(release))


@ui_bp.route("/releases/<int:release_id>/builder", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR")
def release_builder(release_id):
    try:
        release = ReleaseService.get(release_id)
    except NotFoundError:
        flash("Release not found.", "error")
        return redirect(url_for("ui.release_list"))

    if release.status != "BUILDING":
        flash("This Release is already published and can no longer be changed.", "info")
        return redirect(url_for("ui.release_detail", release_id=release_id))

    if request.method == "POST":
        revision_ids = [int(v) for v in request.form.getlist("revision_ids")]
        try:
            ReleaseService.set_items(release_id, revision_ids, current_user)
        except (InvalidTransitionError, DomainError, ValueError) as exc:
            flash(str(exc), "error")
        else:
            flash("Candidate set updated.", "success")
        return redirect(url_for("ui.release_builder", release_id=release_id))

    candidates = ReleaseService.list_candidates(release_id)
    included_ids = {item.status_code_revision_id for item in release.items}
    return render_template(
        "releases/builder.html",
        release=release_payload(release),
        candidates=[revision_payload(c) for c in candidates],
        included_ids=included_ids,
    )


@ui_bp.route("/releases/<int:release_id>/publish", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def release_publish(release_id):
    try:
        ReleaseService.publish(release_id, current_user)
    except (InvalidTransitionError, DomainError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("ui.release_builder", release_id=release_id))

    flash("Release published.", "success")
    return redirect(url_for("ui.release_detail", release_id=release_id))

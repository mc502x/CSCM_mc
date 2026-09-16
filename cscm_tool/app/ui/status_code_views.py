"""S3 List/Search, S4 Detail, S5/S5a New, S6 Edit Draft."""

from flask import flash, redirect, render_template, request, url_for

from app.api.v1.serializers import revision_payload
from app.auth.decorators import current_user, login_required_web, require_role_web
from app.domain.errors import (
    DomainError,
    InvalidTransitionError,
    NotFoundError,
    SegregationOfDutiesViolation,
)
from app.services.lookup_service import LookupService
from app.services.status_code_service import StatusCodeService, ValidationFailed
from app.ui import ui_bp

_VOCAB_FIELDS = {
    "status_category": "status-categories",
    "availability_group": "availability-groups",
    "brake_program": "brake-programs",
    "reset_program": "reset-programs",
    "operational_state": "operational-states",
    "access_rights": "access-rights",
    "alarm_behaviour": "alarm-behaviours",
}


def _lookup_choices():
    choices = {}
    for field, vocabulary in _VOCAB_FIELDS.items():
        choices[field] = LookupService.list_vocabulary(vocabulary)
    choices["functional_system_group"] = LookupService.list_vocabulary("functional-system-groups")
    choices["turbine_platform"] = LookupService.list_vocabulary("turbine-platforms")
    return choices


def _form_to_data(form) -> dict:
    return {
        "functional_system_group": form.get("functional_system_group"),
        "functional_subgroup": form.get("functional_subgroup") or None,
        "turbine_platforms": form.getlist("turbine_platforms"),
        "title": form.get("title", ""),
        "description": form.get("description", ""),
        "status_category": form.get("status_category"),
        "availability_group": form.get("availability_group"),
        "brake_program": form.get("brake_program", "BP-NONE"),
        "reset_program": form.get("reset_program"),
        "software_version": form.get("software_version", ""),
        "operational_state": form.get("operational_state"),
        "access_rights": form.get("access_rights", "SERVICE"),
        "delay_before_alarm_seconds": int(form.get("delay_before_alarm_seconds") or 0),
        "delay_before_reset_seconds": int(form.get("delay_before_reset_seconds") or 0),
        "alarm_behaviour": form.get("alarm_behaviour"),
        "justification": form.get("justification") or None,
    }


@ui_bp.route("/status-codes")
@login_required_web
def status_code_list():
    page = request.args.get("page", 1, type=int)
    items, total = StatusCodeService.search(
        current_user,
        q=request.args.get("q") or None,
        functional_system_group_code=request.args.get("functional_system_group") or None,
        lifecycle_status=request.args.get("lifecycle_status") or None,
        is_sandbox=request.args.get("is_sandbox") == "true",
        page=page,
        page_size=50,
    )
    groups = LookupService.list_vocabulary("functional-system-groups")
    return render_template(
        "status_codes/list.html",
        items=[revision_payload(r) for r in items],
        total=total,
        page=page,
        groups=groups,
    )


@ui_bp.route("/status-codes/new", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def status_code_new():
    if request.method == "POST":
        data = _form_to_data(request.form)
        try:
            revision = StatusCodeService.create_draft(data, current_user)
        except ValidationFailed as exc:
            for err in exc.field_errors:
                flash(f"{err['field']}: {err['message']}", "error")
        except (KeyError, ValueError) as exc:
            flash(str(exc), "error")
        else:
            flash("Draft created.", "success")
            return redirect(
                url_for("ui.status_code_detail", status_code_id=revision.status_code_id)
            )

    return render_template(
        "status_codes/form.html", choices=_lookup_choices(), is_sandbox=False, revision=None
    )


@ui_bp.route("/status-codes/new-sandbox", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR")
def status_code_new_sandbox():
    if request.method == "POST":
        data = _form_to_data(request.form)
        try:
            revision = StatusCodeService.create_sandbox(data, current_user)
        except ValidationFailed as exc:
            for err in exc.field_errors:
                flash(f"{err['field']}: {err['message']}", "error")
        except (KeyError, ValueError) as exc:
            flash(str(exc), "error")
        else:
            flash(f"Sandbox code {revision.status_code.status_code_identifier} created.", "success")
            return redirect(
                url_for("ui.status_code_detail", status_code_id=revision.status_code_id)
            )

    return render_template(
        "status_codes/form.html", choices=_lookup_choices(), is_sandbox=True, revision=None
    )


@ui_bp.route("/status-codes/<int:status_code_id>")
@login_required_web
def status_code_detail(status_code_id):
    try:
        revision = StatusCodeService.get_current_revision(status_code_id, current_user)
    except NotFoundError:
        flash("Status code not found.", "error")
        return redirect(url_for("ui.status_code_list"))

    history = StatusCodeService.list_revision_history(status_code_id, current_user)
    tab = request.args.get("tab", "current")
    open_cr = None
    if revision.lifecycle_status in ("DRAFT", "REVIEW", "PENDING_APPROVAL"):
        open_cr = getattr(revision, "change_request", None)

    return render_template(
        "status_codes/detail.html",
        revision=revision_payload(revision),
        history=[revision_payload(r) for r in history],
        tab=tab,
        open_cr=open_cr,
    )


@ui_bp.route("/status-codes/<int:status_code_id>/edit", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def status_code_edit(status_code_id):
    try:
        revision = StatusCodeService.get_current_revision(status_code_id, current_user)
    except NotFoundError:
        flash("Status code not found.", "error")
        return redirect(url_for("ui.status_code_list"))

    if revision.lifecycle_status != "DRAFT":
        flash("Only a Draft revision may be edited.", "error")
        return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))

    if request.method == "POST":
        data = _form_to_data(request.form)
        try:
            StatusCodeService.update_draft(revision.id, data, current_user)
        except ValidationFailed as exc:
            for err in exc.field_errors:
                flash(f"{err['field']}: {err['message']}", "error")
        except SegregationOfDutiesViolation as exc:
            flash(str(exc), "error")
        except (KeyError, ValueError) as exc:
            flash(str(exc), "error")
        else:
            flash("Draft saved.", "success")
            return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))

    return render_template(
        "status_codes/form.html",
        choices=_lookup_choices(),
        is_sandbox=False,
        revision=revision_payload(revision),
    )


@ui_bp.route("/status-codes/<int:status_code_id>/new-revision", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def status_code_new_revision(status_code_id):
    try:
        revision = StatusCodeService.get_current_revision(status_code_id, current_user)
    except NotFoundError:
        flash("Status code not found.", "error")
        return redirect(url_for("ui.status_code_list"))

    data = {
        "functional_system_group": revision.status_code.functional_system_group.code,
        "functional_subgroup": (
            revision.status_code.functional_subgroup.code
            if revision.status_code.functional_subgroup
            else None
        ),
        "turbine_platforms": sorted(p.turbine_platform.code for p in revision.platforms),
        "title": revision.title,
        "description": revision.description,
        "status_category": revision.status_category.code,
        "availability_group": revision.availability_group.code,
        "brake_program": revision.brake_program.code,
        "reset_program": revision.reset_program.code,
        "software_version": revision.software_version,
        "operational_state": revision.operational_state.code,
        "access_rights": revision.access_rights.code,
        "delay_before_alarm_seconds": revision.delay_before_alarm_seconds,
        "delay_before_reset_seconds": revision.delay_before_reset_seconds,
        "alarm_behaviour": revision.alarm_behaviour.code,
    }
    try:
        new_revision = StatusCodeService.create_revision(status_code_id, data, current_user)
    except InvalidTransitionError as exc:
        flash(str(exc), "error")
    else:
        flash(f"New Draft revision {new_revision.revision_number} opened.", "success")

    return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))


@ui_bp.route("/status-codes/<int:status_code_id>/deprecate", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def status_code_deprecate(status_code_id):
    reason = request.form.get("reason", "")
    superseded_by = request.form.get("superseded_by_status_code_id") or None
    try:
        StatusCodeService.create_deprecation_request(
            status_code_id, reason, int(superseded_by) if superseded_by else None, current_user
        )
    except InvalidTransitionError as exc:
        flash(str(exc), "error")
    except ValidationFailed as exc:
        for err in exc.field_errors:
            flash(f"{err['field']}: {err['message']}", "error")
    else:
        flash("Deprecation request opened; it must go through Review and Approval.", "success")

    return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))


@ui_bp.route("/status-codes/<int:status_code_id>/archive", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def status_code_archive(status_code_id):
    try:
        StatusCodeService.archive(status_code_id, current_user)
    except (InvalidTransitionError, DomainError) as exc:
        flash(str(exc), "error")
    else:
        flash("Status code archived.", "success")
    return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))


@ui_bp.route("/status-codes/<int:status_code_id>/reinstate", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def status_code_reinstate(status_code_id):
    reason = request.form.get("reason", "")
    try:
        StatusCodeService.reinstate(status_code_id, reason, current_user)
    except InvalidTransitionError as exc:
        flash(str(exc), "error")
    except ValidationFailed as exc:
        for err in exc.field_errors:
            flash(f"{err['field']}: {err['message']}", "error")
    else:
        flash("Status code reinstated to Released.", "success")
    return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))


@ui_bp.route("/status-codes/<int:status_code_id>/delete", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def status_code_delete(status_code_id):
    try:
        StatusCodeService.delete_sandbox(status_code_id, current_user)
    except (NotFoundError, DomainError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))

    flash("Sandbox status code permanently deleted.", "success")
    return redirect(url_for("ui.status_code_list"))

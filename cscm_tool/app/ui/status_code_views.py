"""S3 List/Search, S4 Detail, S5/S5a New, S6 Edit Draft.

v3 (2026-09-17): field set rewritten for the real data model
(docs/06-data-dictionary.md). NFR-007a ("no data loss on validation
failure", the single highest-priority legacy-tool complaint): a rejected
Save/Submit never re-renders a blank form — `_form_to_data()`'s output is
already shaped exactly like the template's prefill dict (see
`_revision_to_form_values` for the read path producing the same shape), so
every view passes the just-submitted `data` back to the template as
`values` on failure instead of falling back to an empty form."""

from flask import flash, redirect, render_template, request, url_for

from app.api.v1.serializers import revision_payload
from app.auth.decorators import current_user, login_required_web, require_role_web
from app.domain.errors import (
    DomainError,
    InvalidTransitionError,
    NotFoundError,
    SegregationOfDutiesViolation,
)
from app.services.change_request_service import ChangeRequestService
from app.services.lookup_service import LookupService
from app.services.revision_diff_service import RevisionDiffService
from app.services.status_code_service import StatusCodeService, ValidationFailed
from app.ui import ui_bp

_ACCESS_VOCAB_FIELDS = {
    "development_access": "development-access",
    "sales_access": "sales-access",
    "tcc_access": "tcc-access",
    "service_access": "service-access",
    "turbine_operator_package_access": "turbine-operator-package-access",
    "grid_operator_access": "grid-operator-access",
    "service_partner_access": "service-partner-access",
    "customer_access": "customer-access",
}

_PROGRAM_FIELDS = (
    "yaw_program",
    "manual_reset_program",
    "auto_reset_program",
    "converter_reactive_power_program",
    "brake_program",
    "umrichterprogramm_gsc",
    "umrichterprogramm_msc",
    "yaw_bearing_lubrication_program",
)


def _lookup_choices():
    choices = {}
    for field, vocabulary in _ACCESS_VOCAB_FIELDS.items():
        choices[field] = LookupService.list_vocabulary(vocabulary)
    choices["functional_system_group"] = LookupService.list_vocabulary("functional-system-groups")
    choices["turbine_platform"] = LookupService.list_vocabulary("turbine-platforms")
    choices["available_group"] = LookupService.list_vocabulary("available-groups")
    return choices


def _int_or_none(value):
    return int(value) if value not in (None, "") else None


def _form_to_data(form) -> dict:
    """Shaped to match both what StatusCodeService expects AND what the
    template reads back for prefill (see module docstring) — Functional
    System Group/Subgroup and the eight audience-access fields are all
    submitted as surrogate ids (see app/services/lookup_service.py for why),
    under the same plain key name the service consumes."""
    data = {
        "functional_system_group": _int_or_none(form.get("functional_system_group")),
        "functional_subgroup": _int_or_none(form.get("functional_subgroup")),
        "turbine_platforms": form.getlist("turbine_platforms"),
        "title": form.get("title", ""),
        "description": form.get("description", ""),
        "software_version": form.get("software_version") or None,
        "status_category": form.get("status_category"),
        "available_group": _int_or_none(form.get("available_group")),
        "alarm_flag": form.get("alarm_flag") == "on",
        "set_delay": form.get("set_delay", ""),
        "reset_delay": form.get("reset_delay", ""),
        "up_down_counter": form.get("up_down_counter") == "on",
        "trigger_snapshot": form.get("trigger_snapshot") == "on",
        "loadless_spinning_permitted": form.get("loadless_spinning_permitted") == "on",
        "number_of_times_repeated": _int_or_none(form.get("number_of_times_repeated")),
        "repeated_over_the_course": form.get("repeated_over_the_course") or None,
        "status_code_for_repeated_error": _int_or_none(form.get("status_code_for_repeated_error")),
        "legacy_reference_number": form.get("legacy_reference_number") or None,
        "justification": form.get("justification") or None,
    }
    for field in _PROGRAM_FIELDS:
        data[field] = _int_or_none(form.get(field)) or 0
    for field in _ACCESS_VOCAB_FIELDS:
        data[field] = _int_or_none(form.get(field))
    return data


def _revision_to_form_values(payload: dict) -> dict:
    """The read-path counterpart to `_form_to_data`: reshapes a
    revision_payload() dict into the same plain-key shape (ids, not codes)
    so an Edit Draft form and a rejected Save/Submit form prefill
    identically from the template's point of view."""
    values = dict(payload)
    values["functional_system_group"] = payload["functional_system_group_id"]
    values["functional_subgroup"] = payload["functional_subgroup_id"]
    for field in _ACCESS_VOCAB_FIELDS:
        values[field] = payload[f"{field}_id"]
    return values


@ui_bp.route("/status-codes")
@login_required_web
def status_code_list():
    page = request.args.get("page", 1, type=int)
    items, total = StatusCodeService.search(
        current_user,
        q=request.args.get("q") or None,
        functional_system_group_id=request.args.get("functional_system_group", type=int),
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
    values = {}
    if request.method == "POST":
        data = _form_to_data(request.form)
        values = data
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
        "status_codes/form.html", choices=_lookup_choices(), is_sandbox=False, values=values
    )


@ui_bp.route("/status-codes/new-sandbox", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR")
def status_code_new_sandbox():
    values = {}
    if request.method == "POST":
        data = _form_to_data(request.form)
        values = data
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
        "status_codes/form.html", choices=_lookup_choices(), is_sandbox=True, values=values
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

    decisions = []
    if current_user.role_code != "VIEWER":
        decisions = ChangeRequestService.decision_history(status_code_id, current_user)

    diff = None
    rev_a = request.args.get("a", type=int)
    rev_b = request.args.get("b", type=int)
    if tab == "history" and rev_a and rev_b:
        try:
            diff = RevisionDiffService.diff_revisions(status_code_id, rev_a, rev_b, current_user)
        except NotFoundError:
            flash("Revision not found.", "error")

    return render_template(
        "status_codes/detail.html",
        revision=revision_payload(revision),
        history=[revision_payload(r) for r in history],
        tab=tab,
        open_cr=open_cr,
        diff=diff,
        decisions=decisions,
        rev_a=rev_a,
        rev_b=rev_b,
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

    values = _revision_to_form_values(revision_payload(revision))
    if request.method == "POST":
        data = _form_to_data(request.form)
        values = data
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
        values=values,
        editing=True,
    )


@ui_bp.route("/status-codes/<int:status_code_id>/new-revision", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def status_code_new_revision(status_code_id):
    try:
        revision = StatusCodeService.get_current_revision(status_code_id, current_user)
    except NotFoundError:
        flash("Status code not found.", "error")
        return redirect(url_for("ui.status_code_list"))

    data = _revision_to_form_values(revision_payload(revision))
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

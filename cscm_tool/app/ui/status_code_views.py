"""S3 List/Search, S4 Detail, S5/S5a New, S6 Edit Draft.

v3 (2026-09-17): field set rewritten for the real data model
(docs/06-data-dictionary.md). NFR-007a ("no data loss on validation
failure", the single highest-priority legacy-tool complaint): a rejected
Save/Submit never re-renders a blank form — `_form_to_data()`'s output is
already shaped exactly like the template's prefill dict (see
`_revision_to_form_values` for the read path producing the same shape), so
every view passes the just-submitted `data` back to the template as
`values` on failure instead of falling back to an empty form.

v4 (docs/21-improvement-ideas.md): the edit form carries the Draft's `row_version` so a
stale save is refused with the user's entries intact (I-01); saves report soft warnings
(I-04, I-12); the list takes more filters, a column chooser and saved searches (I-26); the
detail page shows where-used (I-04), the platform family (I-25), planned dates (I-27) and
the translation status (I-15)."""

from flask import flash, redirect, render_template, request, url_for

from app import status_code_fields
from app.api.v1.serializers import revision_payload
from app.auth.decorators import current_user, login_required_web, require_role_web
from app.domain.errors import (
    ConcurrentModificationError,
    DomainError,
    InvalidTransitionError,
    NotFoundError,
    SegregationOfDutiesViolation,
)
from app.i18n import translate as _
from app.services.change_request_service import ChangeRequestService
from app.services.field_review_service import FieldReviewService
from app.services.lookup_service import LookupService
from app.services.reference_service import ReferenceService
from app.services.revision_diff_service import RevisionDiffService
from app.services.saved_search_service import (
    COLUMNS,
    DEFAULT_COLUMNS,
    SORTABLE,
    SavedSearchService,
    clean_definition,
    query_string,
)
from app.services.status_code_service import StatusCodeService, ValidationFailed
from app.services.translation_service import TranslationService
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

_TEXT_FIELDS_V4 = (
    "remedy_text",
    "affected_component",
    "related_status_codes",
    "standard_references",
    "planned_effective_date",
    "planned_deprecation_date",
)


def _lookup_choices():
    choices = {}
    for field, vocabulary in _ACCESS_VOCAB_FIELDS.items():
        choices[field] = LookupService.list_vocabulary(vocabulary)
    choices["functional_system_group"] = LookupService.list_vocabulary("functional-system-groups")
    choices["turbine_platform"] = LookupService.list_vocabulary("turbine-platforms")
    choices["available_group"] = LookupService.list_vocabulary("available-groups")
    choices["software_versions"] = LookupService.list_vocabulary("controller-software-versions")
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
        "applies_from_version": _int_or_none(form.get("applies_from_version")),
        "applies_to_version": _int_or_none(form.get("applies_to_version")),
    }
    for field in _TEXT_FIELDS_V4:
        data[field] = (form.get(field) or "").strip() or None
    for field in _PROGRAM_FIELDS:
        data[field] = _int_or_none(form.get(field)) or 0
    for field in _ACCESS_VOCAB_FIELDS:
        data[field] = _int_or_none(form.get(field))
    # schema v4.1: the further programs, flags, parameters and user-group levels
    for field in status_code_fields.PROGRAM_FIELDS:
        data[field] = _int_or_none(form.get(field)) or 0
    for field in status_code_fields.FLAG_FIELDS:
        choice = form.get(field)
        data[field] = None if choice in (None, "") else choice == "1"
    data["operating_mode_mask"] = (form.get("operating_mode_mask") or "").strip() or None
    data["task_call_frequency"] = _int_or_none(form.get("task_call_frequency"))
    data["user_groups"] = {
        slot: {"read": form.get(f"ug_read_{slot}"), "write": form.get(f"ug_write_{slot}")}
        for slot in status_code_fields.USER_GROUP_SLOTS
        if form.get(f"ug_read_{slot}") not in (None, "")
        or form.get(f"ug_write_{slot}") not in (None, "")
    }
    if form.get("row_version"):
        data["expected_row_version"] = form.get("row_version")
    return data


def _revision_to_form_values(payload: dict) -> dict:
    """The read-path counterpart to `_form_to_data`: reshapes a
    revision_payload() dict into the same plain-key shape (ids, not codes)
    so an Edit Draft form and a rejected Save/Submit form prefill
    identically from the template's point of view."""
    values = dict(payload)
    values["functional_system_group"] = payload["functional_system_group_id"]
    values["functional_subgroup"] = payload["functional_subgroup_id"]
    values["applies_from_version"] = payload["applies_from_version_id"]
    values["applies_to_version"] = payload["applies_to_version_id"]
    for field in _ACCESS_VOCAB_FIELDS:
        values[field] = payload[f"{field}_id"]
    values["operating_mode_mask"] = payload["operating_mode_bits"]
    values["user_groups"] = {
        u["slot"]: {"read": u["read"], "write": u["write"]} for u in payload["user_groups"]
    }
    return values


def _flash_warnings(revision) -> None:
    for warning in StatusCodeService.warnings_for(revision):
        flash(warning["message"], "info")


def _flash_validation(exc: ValidationFailed) -> None:
    for err in exc.field_errors:
        flash(f"{err['field']}: {err['message']}", "error")


# ---------------------------------------------------------------- list (S3, I-26)
@ui_bp.route("/status-codes")
@login_required_web
def status_code_list():
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort") or None
    if sort and sort.lstrip("-") not in SORTABLE:
        sort = None
    items, total = StatusCodeService.search(
        current_user,
        q=request.args.get("q") or None,
        functional_system_group_id=request.args.get("functional_system_group", type=int),
        functional_subgroup_id=request.args.get("functional_subgroup", type=int),
        turbine_platform_code=request.args.get("turbine_platform") or None,
        lifecycle_status=request.args.get("lifecycle_status") or None,
        status_category=request.args.get("status_category") or None,
        is_sandbox=request.args.get("is_sandbox") == "true",
        page=page,
        page_size=50,
        sort=sort,
    )
    columns = clean_definition({"columns": request.args.get("cols")})["columns"]
    filters = {
        k: v
        for k, v in request.args.items()
        if k
        in (
            "q",
            "functional_system_group",
            "functional_subgroup",
            "turbine_platform",
            "lifecycle_status",
            "status_category",
            "sort",
            "is_sandbox",
        )
        and v
    }
    return render_template(
        "status_codes/list.html",
        items=[revision_payload(r) for r in items],
        total=total,
        page=page,
        groups=LookupService.list_vocabulary("functional-system-groups"),
        platforms=LookupService.list_vocabulary("turbine-platforms"),
        columns=columns,
        all_columns=COLUMNS,
        default_columns=DEFAULT_COLUMNS,
        saved=SavedSearchService.list_for(current_user),
        share_query=query_string({"filters": filters, "columns": columns}),
        saved_definition=SavedSearchService.definition_of,
        saved_query=lambda row: query_string(SavedSearchService.definition_of(row)),
    )


@ui_bp.route("/saved-searches", methods=["POST"])
@login_required_web
def saved_search_create():
    definition = {
        "filters": {
            k: v for k, v in request.form.items() if k not in ("csrf_token", "name", "cols") and v
        },
        "columns": request.form.get("cols"),
    }
    try:
        SavedSearchService.save(current_user, request.form.get("name", ""), definition)
    except (DomainError, ValueError) as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Search saved."), "success")
    filters: dict[str, str] = dict(definition["filters"])  # type: ignore[arg-type]
    return redirect(url_for("ui.status_code_list", **filters))  # type: ignore[arg-type]


@ui_bp.route("/saved-searches/<int:search_id>/delete", methods=["POST"])
@login_required_web
def saved_search_delete(search_id):
    try:
        SavedSearchService.delete(current_user, search_id)
    except (DomainError, ValueError) as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Saved search removed."), "success")
    return redirect(url_for("ui.status_code_list"))


# ---------------------------------------------------------------- create (S5, S5a)
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
            _flash_validation(exc)
        except (KeyError, ValueError) as exc:
            flash(_(str(exc)), "error")
        else:
            flash(_("Draft created."), "success")
            _flash_warnings(revision)
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
            _flash_validation(exc)
        except (KeyError, ValueError) as exc:
            flash(_(str(exc)), "error")
        else:
            flash(
                _(
                    "Sandbox code %(code)s created.",
                    code=revision.status_code.status_code_identifier,
                ),
                "success",
            )
            return redirect(
                url_for("ui.status_code_detail", status_code_id=revision.status_code_id)
            )

    return render_template(
        "status_codes/form.html", choices=_lookup_choices(), is_sandbox=True, values=values
    )


# ---------------------------------------------------------------- detail (S4)
@ui_bp.route("/status-codes/<int:status_code_id>")
@login_required_web
def status_code_detail(status_code_id):
    try:
        revision = StatusCodeService.get_current_revision(status_code_id, current_user)
    except NotFoundError:
        flash(_("Status code not found."), "error")
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
            flash(_("Revision not found."), "error")

    where_used = []
    connections = None
    if current_user.role_code != "VIEWER" and not revision.status_code.is_sandbox:
        where_used = ReferenceService.where_used(status_code_id)
        from app.services.connection_service import ConnectionService

        connections = ConnectionService.for_code(status_code_id)
    family = []
    if not revision.status_code.is_sandbox:
        for member in StatusCodeService.family(status_code_id):
            if member.id == status_code_id:
                continue
            try:
                member_revision = StatusCodeService.get_current_revision(member.id, current_user)
            except NotFoundError:
                continue
            family.append(revision_payload(member_revision))
    translations = []
    decided = StatusCodeService._repo.get_latest_revision_in_states(
        status_code_id, ("RELEASED", "APPROVED", "DEPRECATED")
    )
    if decided is not None and not revision.status_code.is_sandbox:
        translations = TranslationService.status_matrix(decided.id, current_user)

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
        where_used=where_used,
        connections=connections,
        family=family,
        translations=translations,
        reference_warnings=(
            ReferenceService.warnings_for_revision(revision)
            if current_user.role_code != "VIEWER"
            else []
        ),
        platforms=LookupService.list_vocabulary("turbine-platforms"),
        dependants=[
            d for d in where_used if d["lifecycle_status"] not in ("DEPRECATED", "ARCHIVED")
        ],
        is_hub=revision.status_code.functional_system_group.controller_type == "HUB",
        main_groups=LookupService.list_vocabulary("functional-system-groups"),
    )


# ---------------------------------------------------------------- connections (FR-179)
@ui_bp.route("/status-codes/connections")
@require_role_web("ENGINEER", "REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER", "STCD_OWNER")
def status_code_connections():
    from app.services.connection_service import ConnectionService

    controller = request.args.get("controller") or None
    if controller not in (None, "MC", "HC"):
        controller = None
    return render_template(
        "status_codes/connections.html",
        data=ConnectionService.hierarchy(controller),
        controller=controller,
    )


# ---------------------------------------------------------------- edit (S6, I-01, I-23)
@ui_bp.route("/status-codes/<int:status_code_id>/edit", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def status_code_edit(status_code_id):
    try:
        revision = StatusCodeService.get_current_revision(status_code_id, current_user)
    except NotFoundError:
        flash(_("Status code not found."), "error")
        return redirect(url_for("ui.status_code_list"))

    if revision.lifecycle_status != "DRAFT":
        flash(_("Only a Draft revision may be edited."), "error")
        return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))

    values = _revision_to_form_values(revision_payload(revision))
    conflict = None
    if request.method == "POST":
        data = _form_to_data(request.form)
        values = data
        try:
            saved = StatusCodeService.update_draft(revision.id, data, current_user)
        except ConcurrentModificationError as exc:
            # I-01: keep the user's entries, show what is stored now and what differs.
            current = revision_payload(revision)
            mine = {k: v for k, v in data.items() if k in current}
            differing = [
                {"field": k, "mine": mine[k], "current": current[k]}
                for k in mine
                if k not in ("justification",) and mine[k] != current.get(k)
            ]
            conflict = {
                "message": str(exc),
                "current_row_version": exc.current_row_version,
                "differences": differing,
            }
            # the next save is against the version the user has now seen
            values = {**data, "expected_row_version": exc.current_row_version}
        except ValidationFailed as exc:
            _flash_validation(exc)
        except (SegregationOfDutiesViolation, KeyError, ValueError) as exc:
            flash(_(str(exc)), "error")
        else:
            flash(_("Draft saved."), "success")
            _flash_warnings(saved)
            return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))

    cr = getattr(revision, "change_request", None)
    return render_template(
        "status_codes/form.html",
        choices=_lookup_choices(),
        is_sandbox=False,
        values=values,
        editing=True,
        conflict=conflict,
        row_version=(values.get("expected_row_version") or revision.row_version),
        field_comments=FieldReviewService.open_comments_by_field(cr.id) if cr else {},
        revision_id=revision.id,
    )


@ui_bp.route("/status-codes/<int:status_code_id>/new-revision", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def status_code_new_revision(status_code_id):
    try:
        revision = StatusCodeService.get_current_revision(status_code_id, current_user)
    except NotFoundError:
        flash(_("Status code not found."), "error")
        return redirect(url_for("ui.status_code_list"))

    data = _revision_to_form_values(revision_payload(revision))
    try:
        new_revision = StatusCodeService.create_revision(status_code_id, data, current_user)
    except InvalidTransitionError as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("New Draft revision %(n)s opened.", n=new_revision.revision_number), "success")

    return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))


@ui_bp.route("/status-codes/<int:status_code_id>/platform-variant", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def status_code_platform_variant(status_code_id):
    """I-25."""
    try:
        variant = StatusCodeService.create_platform_variant(
            status_code_id, request.form.get("turbine_platform", ""), current_user
        )
    except ValidationFailed as exc:
        _flash_validation(exc)
    except (DomainError, ValueError) as exc:
        flash(_(str(exc)), "error")
    else:
        flash(
            _("Platform variant created as a Draft; it goes through the normal review."), "success"
        )
        return redirect(url_for("ui.status_code_detail", status_code_id=variant.status_code_id))
    return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id, tab="actions"))


@ui_bp.route("/status-codes/<int:status_code_id>/planned-dates", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def status_code_planned_dates(status_code_id):
    """I-27."""
    try:
        StatusCodeService.set_planned_dates(
            status_code_id,
            request.form.get("planned_effective_date") or None,
            request.form.get("planned_deprecation_date") or None,
            current_user,
        )
    except ValidationFailed as exc:
        _flash_validation(exc)
    except (DomainError, ValueError) as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Planned dates saved."), "success")
    return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id, tab="actions"))


@ui_bp.route("/status-codes/<int:status_code_id>/deprecate", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def status_code_deprecate(status_code_id):
    reason = request.form.get("reason", "")
    superseded_by = request.form.get("superseded_by_status_code_id") or None
    try:
        StatusCodeService.create_deprecation_request(
            status_code_id,
            reason,
            int(superseded_by) if superseded_by else None,
            current_user,
            acknowledge_dependants=request.form.get("acknowledge_dependants") == "on",
        )
    except InvalidTransitionError as exc:
        flash(_(str(exc)), "error")
    except ValidationFailed as exc:
        _flash_validation(exc)
    else:
        flash(_("Deprecation request opened; it must go through Review and Approval."), "success")

    return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id, tab="actions"))


@ui_bp.route("/status-codes/<int:status_code_id>/archive", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def status_code_archive(status_code_id):
    try:
        StatusCodeService.archive(status_code_id, current_user)
    except (InvalidTransitionError, DomainError) as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("Status code archived."), "success")
    return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))


@ui_bp.route("/status-codes/<int:status_code_id>/reinstate", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def status_code_reinstate(status_code_id):
    reason = request.form.get("reason", "")
    try:
        StatusCodeService.reinstate(status_code_id, reason, current_user)
    except InvalidTransitionError as exc:
        flash(_(str(exc)), "error")
    except ValidationFailed as exc:
        _flash_validation(exc)
    else:
        flash(_("Status code reinstated to Released."), "success")
    return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))


@ui_bp.route("/status-codes/<int:status_code_id>/delete", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def status_code_delete(status_code_id):
    try:
        StatusCodeService.delete_sandbox(status_code_id, current_user)
    except (NotFoundError, DomainError) as exc:
        flash(_(str(exc)), "error")
        return redirect(url_for("ui.status_code_detail", status_code_id=status_code_id))

    flash(_("Sandbox status code permanently deleted."), "success")
    return redirect(url_for("ui.status_code_list"))

# ruff: noqa: E501  (docstring lines)
"""S41 The mapping and its change requests (FR-191..FR-198): the table of the legacy -> new pairs with
what the programs do not carry, the request for a change (one row, the ticked rows, or a whole
workbook) and the page where the StCd Owner, the Chief Engineer and an Administrator decide."""

import json

from flask import Response, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import OperationalError

from app.auth.decorators import current_user, require_role_web
from app.auth.roles import role_info
from app.domain.errors import DomainError
from app.extensions import db
from app.i18n import translate as _
from app.models.mapping import MappingChangeItem
from app.services.mapping_service import (
    APPROVER_ROLES,
    EDITABLE,
    FAMILIES,
    REQUEST_ROLES,
    STATUSES,
    TYPES,
    VIEW_ROLES,
    MappingService,
    audience_labels,
    differences,
    field_label,
    row_dict,
)
from app.ui import ui_bp
from app.utils import join_multi, split_multi

_ERRORS = (DomainError, ValueError)
_MAPPING_TABLES = ("status_code_mapping", "mapping_change", "mapping_approval")


def _is_missing_mapping_table(exc: OperationalError) -> bool:
    message = str(exc.orig) if exc.orig is not None else str(exc)
    return "no such table" in message and any(t in message for t in _MAPPING_TABLES)


@ui_bp.errorhandler(OperationalError)
def _database_not_upgraded(exc: OperationalError):
    """A database that is still at an older schema: say what to run instead of a stack trace."""
    if not _is_missing_mapping_table(exc):
        raise exc
    db.session.rollback()
    return render_template("mapping/not_upgraded.html"), 503


_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PAGE_SIZE = 100
SHOW_ALL_LIMIT = 5000  # one click shows every row; the table holds about 1,200
SHOWN_ITEMS = 500


def _form_values() -> dict:
    """The editable fields of the row form; an empty field is no value."""
    values: dict = {}
    for name in EDITABLE:
        if name in request.form:
            text = request.form.get(name, "").strip()
            values[name] = text or None
    return values


def _form_context(row: dict | None) -> dict:
    row = dict(row or {})
    counter = row.get("up_down_counter")
    if isinstance(counter, str):  # as typed in the form that was refused
        row["up_down_counter"] = {"yes": 1, "no": 0}.get(counter.strip().lower())
    return {
        "row": row,
        "families": FAMILIES,
        "types": TYPES,
        "levels": audience_labels(),
        "field_label": field_label,
    }


def _page_url(page: int, **changes: str | None) -> str:
    args: dict = {k: v for k, v in request.args.lists() if k not in ("page", "all")}
    if page > 1:
        args["page"] = page
    args.update({k: v for k, v in changes.items() if v is not None})
    return url_for("ui.mapping_list", **args)


@ui_bp.route("/mapping")
@require_role_web(*VIEW_ROLES)
def mapping_list():
    family = join_multi(request.args.getlist("family")) or ""
    status = join_multi(request.args.getlist("status")) or ""
    show_all = request.args.get("all") == "1"
    page = 1 if show_all else max(1, request.args.get("page", 1, type=int) or 1)
    size = SHOW_ALL_LIMIT if show_all else PAGE_SIZE
    rows, total = MappingService.search(
        family,
        status,
        request.args.get("q"),
        page,
        size,
    )
    return render_template(
        "mapping/list.html",
        rows=rows,
        total=total,
        page=page,
        pages=1 if show_all else max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE),
        show_all=show_all,
        all_url=_page_url(1, all="1"),
        paged_url=_page_url(1, all=None),
        page_url=_page_url,
        summary=MappingService.summary(),
        options={
            "family": [("MC", _("Main Controller")), ("HC", _("Hub Controller"))],
            "status": [(s, s) for s in STATUSES],
        },
        filters={
            "family": [f for f in split_multi(family) if f in FAMILIES],
            "status": [s for s in split_multi(status) if s in STATUSES],
            "q": request.args.get("q") or "",
        },
        can_request=current_user.role_code in REQUEST_ROLES,
    )


@ui_bp.route("/mapping/export")
@require_role_web(*VIEW_ROLES)
def mapping_export():
    chosen = [f for f in split_multi(request.args.getlist("family")) if f in FAMILIES]
    return Response(
        MappingService.export_xlsx(chosen[0] if len(chosen) == 1 else None),
        mimetype=_XLSX,
        headers={"Content-Disposition": "attachment; filename=legacy_mapping.xlsx"},
    )


@ui_bp.route("/mapping/seed", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def mapping_seed():
    try:
        loaded = MappingService.seed()
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        flash(
            _("The initial mapping was loaded.") if loaded else _("The mapping already has rows."),
            "success" if loaded else "info",
        )
    return redirect(url_for("ui.mapping_list"))


@ui_bp.route("/mapping/new", methods=["GET", "POST"])
@require_role_web(*REQUEST_ROLES)
def mapping_new():
    if request.method == "POST":
        values = _form_values()
        values["family"] = request.form.get("family", "")
        try:
            change = MappingService.propose(
                current_user,
                f"New row {values.get('new_number') or '?'}",
                request.form.get("reason", ""),
                [MappingService.build_item("ADD", None, values)],
            )
        except _ERRORS as exc:
            flash(_(str(exc)), "error")
            return render_template("mapping/row.html", model=None, **_form_context(values)), 422
        flash(_("The request was made. It takes effect after the three approvals."), "success")
        return redirect(url_for("ui.mapping_change", change_id=change.id))
    return render_template("mapping/row.html", model=None, **_form_context(None))


@ui_bp.route("/mapping/<int:mapping_id>", methods=["GET", "POST"])
@require_role_web(*VIEW_ROLES)
def mapping_row(mapping_id: int):
    try:
        model = MappingService.get(mapping_id)
    except DomainError:
        flash(_("The mapping row was not found."), "error")
        return redirect(url_for("ui.mapping_list"))
    if request.method == "POST":
        if current_user.role_code not in REQUEST_ROLES:
            flash(_("Your role may not propose a change of the mapping."), "error")
            return redirect(url_for("ui.mapping_row", mapping_id=mapping_id))
        action = request.form.get("action", "CHANGE")
        edits = _form_values() if action == "CHANGE" else {}
        edits.pop("family", None)
        label = f"StCd-{model.new_number:05d}"
        verb = {"CHANGE": "Change", "CONFIRM": "Approve", "REJECT": "Reject"}.get(action, "Change")
        try:
            change = MappingService.propose(
                current_user,
                f"{verb} {label}",
                request.form.get("reason", ""),
                [MappingService.build_item(action, model.id, edits)],
            )
        except _ERRORS as exc:
            flash(_(str(exc)), "error")
            row = {**row_dict(model), **edits}
            return render_template("mapping/row.html", model=model, **_form_context(row)), 422
        flash(_("The request was made. It takes effect after the three approvals."), "success")
        return redirect(url_for("ui.mapping_change", change_id=change.id))
    history = (
        db.session.query(MappingChangeItem)
        .filter_by(mapping_id=model.id)
        .order_by(MappingChangeItem.id.desc())
        .all()
    )
    return render_template(
        "mapping/row.html",
        model=model,
        history=[i.change for i in history],
        can_request=current_user.role_code in REQUEST_ROLES,
        **_form_context(row_dict(model)),
    )


@ui_bp.route("/mapping/select", methods=["POST"])
@require_role_web(*REQUEST_ROLES)
def mapping_select():
    ids = [int(v) for v in request.form.getlist("ids") if v.isdigit()]
    if not ids:
        flash(_("Tick at least one row."), "error")
        return redirect(request.referrer or url_for("ui.mapping_list"))
    try:
        items = [MappingService.build_item("CONFIRM", i) for i in ids]
        change = MappingService.propose(
            current_user,
            f"Approve {len(items)} rows",
            request.form.get("reason", ""),
            items,
            "SELECTION",
        )
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
        return redirect(request.referrer or url_for("ui.mapping_list"))
    flash(_("The request was made. It takes effect after the three approvals."), "success")
    return redirect(url_for("ui.mapping_change", change_id=change.id))


@ui_bp.route("/mapping/upload", methods=["GET", "POST"])
@require_role_web(*REQUEST_ROLES)
def mapping_upload():
    report = None
    if request.method == "POST":
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            flash(_("Choose the workbook (.xlsx) to compare."), "error")
        else:
            try:
                plan = MappingService.plan_from_workbook(
                    upload.read(), confirm_unchanged=request.form.get("confirm_unchanged") == "1"
                )
                if plan["problems"]:
                    report = plan
                elif not plan["items"]:
                    flash(_("The workbook holds no new and no different row."), "info")
                else:
                    items = [
                        MappingService.build_item(i["action"], i["mapping_id"], i["after"])
                        for i in plan["items"]
                    ]
                    change = MappingService.propose(
                        current_user,
                        request.form.get("title") or f"Workbook {upload.filename}"[:120],
                        request.form.get("reason", ""),
                        items,
                        "WORKBOOK",
                    )
                    flash(
                        _("The request was made. It takes effect after the three approvals."),
                        "success",
                    )
                    return redirect(url_for("ui.mapping_change", change_id=change.id))
            except _ERRORS as exc:
                flash(_(str(exc)), "error")
    return render_template("mapping/upload.html", report=report)


@ui_bp.route("/mapping-changes")
@require_role_web(*VIEW_ROLES)
def mapping_changes():
    state = join_multi(request.args.getlist("state")) or ""
    changes = MappingService.changes(state)
    return render_template(
        "mapping/changes.html",
        changes=changes,
        states=[(s, s) for s in ("OPEN", "APPLIED", "REJECTED", "WITHDRAWN")],
        state=split_multi(state),
        decisions={c.id: MappingService.who_decides(c) for c in changes},
        role_label=lambda code: role_info(code).label,
        waiting=MappingService.awaiting(current_user),
    )


@ui_bp.route("/mapping-changes/<int:change_id>")
@require_role_web(*VIEW_ROLES)
def mapping_change(change_id: int):
    try:
        change = MappingService.get_change(change_id)
    except DomainError:
        flash(_("The request was not found."), "error")
        return redirect(url_for("ui.mapping_changes"))
    entries = []
    for item in change.items[:SHOWN_ITEMS]:
        before = json.loads(item.before_json) if item.before_json else None
        after = json.loads(item.after_json)
        changed = differences(before, after)
        entries.append(
            {
                "item": item,
                "after": after,
                "changes": [
                    {
                        "field": field_label(f),
                        "old_value": (before or {}).get(f),
                        "new_value": after.get(f),
                    }
                    for f in changed
                ],
            }
        )
    slots = MappingService.who_decides(change)
    role = current_user.role_code
    reason = None
    if change.state != "OPEN":
        reason = None
    elif role not in APPROVER_ROLES:
        reason = None
    elif change.requested_by == current_user.id:
        reason = "own"
    elif slots.get(role) is not None:
        reason = "decided"
    can_decide = change.state == "OPEN" and role in APPROVER_ROLES and reason is None
    return render_template(
        "mapping/change.html",
        change=change,
        entries=entries,
        more=max(0, len(change.items) - SHOWN_ITEMS),
        slots=slots,
        role_label=lambda code: role_info(code).label,
        can_decide=can_decide,
        why_not=reason,
        can_withdraw=change.state == "OPEN" and change.requested_by == current_user.id,
        stale=MappingService.stale_items(change) if change.state == "OPEN" else [],
    )


@ui_bp.route("/mapping-changes/<int:change_id>/decisions", methods=["POST"])
@require_role_web(*APPROVER_ROLES)
def mapping_decide(change_id: int):
    try:
        change = MappingService.decide(
            change_id,
            current_user,
            request.form.get("decision", ""),
            request.form.get("comment"),
            reauth_password=request.form.get("current_password"),
        )
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        if change.state == "APPLIED":
            flash(_("All three approvals are in: the mapping was changed."), "success")
        elif change.state == "REJECTED":
            flash(_("The request was rejected."), "info")
        else:
            flash(_("Your approval was recorded."), "success")
    return redirect(url_for("ui.mapping_change", change_id=change_id))


@ui_bp.route("/mapping-changes/<int:change_id>/withdraw", methods=["POST"])
@require_role_web(*REQUEST_ROLES)
def mapping_withdraw(change_id: int):
    try:
        MappingService.withdraw(change_id, current_user)
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        flash(_("The request was withdrawn."), "info")
    return redirect(url_for("ui.mapping_change", change_id=change_id))

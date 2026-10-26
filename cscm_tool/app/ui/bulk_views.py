"""The workbench of a change set (FR-180): bulk edit, submit, domain sign-off, the sample inspection
and the decision with its sample, on one page. The services are in app/services/bulk_service.py;
every action here ends in the single-code services, one call per code."""

from flask import flash, redirect, render_template, request, url_for

from app.auth.decorators import current_user, require_role_web
from app.auth.roles import OVERSIGHT_ROLES
from app.domain.errors import DomainError, NotFoundError
from app.i18n import translate as _
from app.services.bulk_service import EDITABLE, BulkService
from app.services.change_set_service import ChangeSetService
from app.services.lookup_service import LookupService
from app.ui import ui_bp

_ERRORS = (DomainError, ValueError)
_WORKING = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")
_ACCESS_VOCABULARY = {
    "development_access": "development-access",
    "sales_access": "sales-access",
    "tcc_access": "tcc-access",
    "service_access": "service-access",
    "turbine_operator_package_access": "turbine-operator-package-access",
    "grid_operator_access": "grid-operator-access",
    "service_partner_access": "service-partner-access",
    "customer_access": "customer-access",
}


def _back(change_set_id: int):
    return redirect(url_for("ui.change_set_workbench", change_set_id=change_set_id))


def _report(results: list[dict], done_text: str) -> None:
    ok = sum(1 for r in results if r["ok"])
    flash(
        _("%(ok)s of %(n)s: %(what)s.", ok=ok, n=len(results), what=done_text),
        "success" if ok else "error",
    )
    shown = 0
    for r in results:
        if not r["ok"] and shown < 10:
            flash(f"CR #{r['cr_id']}: {r['message']}", "error")
            shown += 1


@ui_bp.route("/change-sets/<int:change_set_id>/workbench")
@require_role_web(*OVERSIGHT_ROLES)
def change_set_workbench(change_set_id):
    try:
        overview = ChangeSetService.overview(change_set_id)
    except NotFoundError:
        flash(_("Change set not found."), "error")
        return redirect(url_for("ui.change_set_list"))
    samples = [
        s
        for s in BulkService.samples(change_set_id)
        if s.drawn_by == current_user.id and s.status in ("OPEN", "PASSED", "FAILED")
    ]
    return render_template(
        "change_sets/workbench.html",
        overview=overview,
        readiness=BulkService.readiness(change_set_id),
        rules=BulkService.rules(),
        samples=samples,
        domains=sorted(current_user.engineering_domain_codes),
        platforms=LookupService.list_vocabulary("turbine-platforms"),
        access=[
            (field, LookupService.list_vocabulary(vocab))
            for field, vocab in _ACCESS_VOCABULARY.items()
        ],
    )


@ui_bp.route("/change-sets/<int:change_set_id>/bulk/edit", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def change_set_bulk_edit(change_set_id):
    form = request.form
    changes: dict = {}
    if form.get("status_category"):
        changes["status_category"] = form["status_category"]
    if form.getlist("turbine_platforms"):
        changes["turbine_platforms"] = form.getlist("turbine_platforms")
    if form.get("available_group", type=int):
        changes["available_group"] = form.get("available_group", type=int)
    for field in EDITABLE:
        if field in _ACCESS_VOCABULARY and form.get(field):
            changes[field] = int(form[field])
    try:
        results = BulkService.edit(
            change_set_id, form.getlist("cr_ids", type=int) or None, changes, current_user
        )
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        _report(results, _("Drafts saved"))
    return _back(change_set_id)


@ui_bp.route("/change-sets/<int:change_set_id>/bulk/submit", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def change_set_bulk_submit(change_set_id):
    try:
        results = BulkService.submit(
            change_set_id, current_user, request.form.getlist("cr_ids", type=int) or None
        )
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        _report(results, _("Drafts submitted for review"))
    return _back(change_set_id)


@ui_bp.route("/change-sets/<int:change_set_id>/bulk/domain", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def change_set_bulk_domain(change_set_id):
    try:
        results = BulkService.domain_signoff(
            change_set_id,
            request.form.get("domain", ""),
            current_user,
            sample_id=request.form.get("sample_id", type=int),
        )
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        _report(results, _("Drafts signed off"))
    return _back(change_set_id)


@ui_bp.route("/change-sets/<int:change_set_id>/bulk/sample", methods=["POST"])
@require_role_web(*_WORKING)
def change_set_sample_draw(change_set_id):
    step = request.form.get("step", "")
    domain = None
    if step.startswith("domain:"):
        step, domain = "domain", step.split(":", 1)[1]
    try:
        sample = BulkService.draw_sample(
            change_set_id,
            step,
            current_user,
            domain_code=domain,
        )
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    else:
        flash(
            _(
                "Sample %(id)s drawn: %(n)s of %(total)s codes to inspect.",
                id=sample.id,
                n=len(sample.items),
                total=sample.population,
            ),
            "success",
        )
    return _back(change_set_id)


@ui_bp.route("/bulk-samples/<int:sample_id>/verdicts", methods=["POST"])
@require_role_web(*_WORKING)
def change_set_sample_verdicts(sample_id):
    try:
        sample = BulkService.get_sample(sample_id)
        for item in sample.items:
            verdict = request.form.get(f"verdict_{item.change_request_id}")
            if verdict:
                BulkService.record_verdict(
                    sample_id,
                    item.change_request_id,
                    verdict,
                    request.form.get(f"note_{item.change_request_id}"),
                    current_user,
                )
    except NotFoundError:
        flash(_("Sample not found"), "error")
        return redirect(url_for("ui.change_set_list"))
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
    sample = BulkService.get_sample(sample_id)
    return _back(sample.change_set_id)


@ui_bp.route("/bulk-samples/<int:sample_id>/reject", methods=["POST"])
@require_role_web(*_WORKING)
def change_set_sample_reject(sample_id):
    try:
        sample = BulkService.get_sample(sample_id)
        change_set_id = sample.change_set_id
        results = BulkService.reject_defects(
            sample_id,
            current_user,
            request.form.get("current_password"),
            request.form.get("comment"),
        )
    except NotFoundError:
        flash(_("Sample not found"), "error")
        return redirect(url_for("ui.change_set_list"))
    except _ERRORS as exc:
        flash(_(str(exc)), "error")
        return _back(BulkService.get_sample(sample_id).change_set_id)
    _report(results, _("defective codes sent back"))
    return _back(change_set_id)

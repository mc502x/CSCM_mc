"""Reporting, integration and operations screens of the improvement pack: catalogue health and
capacity (I-19), success metrics (I-10), fleet feedback (I-28), Hub -> Main consolidation (I-36),
API tokens and webhooks (I-29), backups and audit verification (I-09, I-18)."""

from flask import flash, redirect, render_template, request, url_for

from app.audit_chain import AuditChainService
from app.auth.decorators import current_user, require_role_web
from app.auth.roles import OVERSIGHT_ROLES
from app.domain.errors import DomainError
from app.services import backup_service
from app.services.health_report_service import HealthReportService
from app.services.hub_consolidation_service import HubConsolidationService
from app.services.integration_service import (
    TOKEN_SCOPES,
    ApiTokenService,
    WebhookService,
)
from app.services.kpi_service import KpiService
from app.services.lookup_service import LookupService
from app.services.occurrence_service import OccurrenceService
from app.services.status_code_service import ValidationFailed
from app.ui import ui_bp

_WORKING = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")
_ERRORS = (DomainError, ValueError)


@ui_bp.route("/reports/catalogue-health")
@require_role_web("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER")
def catalogue_health():
    return render_template("reports/catalogue_health.html", report=HealthReportService.report())


@ui_bp.route("/reports/success-metrics")
@require_role_web("ADMINISTRATOR", "CHIEF_ENGINEER")
def success_metrics():
    return render_template("reports/success_metrics.html", kpis=KpiService.compute())


@ui_bp.route("/reports/fleet-feedback", methods=["GET", "POST"])
@require_role_web("ADMINISTRATOR", "CHIEF_ENGINEER")
def fleet_feedback():
    if request.method == "POST":
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            flash("Choose a CSV or XLSX file with the occurrence counts.", "error")
        else:
            try:
                batch = OccurrenceService.import_counts(
                    upload.filename,
                    upload.read(),
                    request.form.get("source_label", ""),
                    request.form.get("period_start", ""),
                    request.form.get("period_end", ""),
                    current_user,
                )
            except _ERRORS as exc:
                flash(str(exc), "error")
            else:
                flash(
                    f"Imported counts for {batch.row_count} codes "
                    f"({batch.unmatched_count} rows matched no code).",
                    "success",
                )
        return redirect(url_for("ui.fleet_feedback"))
    return render_template(
        "reports/fleet_feedback.html",
        report=OccurrenceService.report(),
        imports=OccurrenceService.list_imports(),
    )


# ---------------------------------------------------------------- Hub consolidation (I-36)
@ui_bp.route("/hub-consolidation")
@require_role_web(*OVERSIGHT_ROLES)
def hub_consolidation():
    group_id = request.args.get("group", type=int)
    return render_template(
        "hub_consolidation.html",
        report=HubConsolidationService.mapping_report(group_id),
        hub_groups=HubConsolidationService.hub_groups(),
        main_groups=HubConsolidationService.main_groups(),
        selected_group=group_id,
        subgroups=(
            LookupService.list_vocabulary(
                "functional-subgroups",
                functional_system_group_id=request.args.get("target_group", type=int),
            )
            if request.args.get("target_group", type=int)
            else []
        ),
        target_group=request.args.get("target_group", type=int),
    )


@ui_bp.route("/hub-consolidation/<int:hub_status_code_id>/mc-draft", methods=["POST"])
@require_role_web("ADMINISTRATOR", "ENGINEER")
def hub_create_mc_draft(hub_status_code_id):
    try:
        revision, _mapping = HubConsolidationService.create_mc_draft(
            hub_status_code_id,
            request.form.get("functional_system_group", 0, type=int),
            request.form.get("functional_subgroup", 0, type=int),
            current_user,
        )
    except ValidationFailed as exc:
        for err in exc.field_errors:
            flash(f"{err['field']}: {err['message']}", "error")
    except _ERRORS as exc:
        flash(str(exc), "error")
    else:
        flash("Main Controller draft created from the Hub Controller code.", "success")
        return redirect(url_for("ui.status_code_detail", status_code_id=revision.status_code_id))
    return redirect(url_for("ui.hub_consolidation"))


@ui_bp.route("/hub-consolidation/deprecate", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def hub_bulk_deprecate():
    group_id = request.form.get("functional_system_group", type=int) or 0
    try:
        result = HubConsolidationService.request_hub_deprecation(group_id, current_user)
    except _ERRORS as exc:
        flash(str(exc), "error")
    else:
        flash(
            f"{len(result['created'])} deprecation request(s) opened, "
            f"{len(result['skipped'])} skipped.",
            "success",
        )
        for item in result["skipped"][:10]:
            flash(f"{item['hub_identifier']}: {item['reason']}", "info")
    return redirect(url_for("ui.hub_consolidation", group=group_id))


# ---------------------------------------------------------------- integrations (I-29)
def _integrations_page(**extra):
    return render_template(
        "admin/integrations.html",
        tokens=ApiTokenService.list_all(current_user),
        webhooks=WebhookService.list_all(current_user),
        scopes=TOKEN_SCOPES,
        **extra,
    )


@ui_bp.route("/admin/integrations")
@require_role_web("ADMINISTRATOR")
def integrations():
    return _integrations_page()


@ui_bp.route("/admin/integrations/tokens", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def integration_token_create():
    try:
        _row, plaintext = ApiTokenService.create(
            current_user,
            request.form.get("name", ""),
            request.form.getlist("scopes"),
            request.form.get("expires_in_days", 90, type=int),
        )
    except _ERRORS as exc:
        flash(str(exc), "error")
        return redirect(url_for("ui.integrations"))
    # Rendered in this response only (not via flash/session): the secret is shown exactly once.
    return _integrations_page(new_token=plaintext)


@ui_bp.route("/admin/integrations/tokens/<int:token_id>/revoke", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def integration_token_revoke(token_id):
    try:
        ApiTokenService.revoke(token_id, current_user)
    except _ERRORS as exc:
        flash(str(exc), "error")
    else:
        flash("Token revoked.", "success")
    return redirect(url_for("ui.integrations"))


@ui_bp.route("/admin/integrations/webhooks", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def integration_webhook_create():
    try:
        _row, secret = WebhookService.create(
            current_user, request.form.get("name", ""), request.form.get("url", "")
        )
    except _ERRORS as exc:
        flash(str(exc), "error")
        return redirect(url_for("ui.integrations"))
    return _integrations_page(new_webhook_secret=secret)


@ui_bp.route("/admin/integrations/webhooks/<int:webhook_id>/toggle", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def integration_webhook_toggle(webhook_id):
    try:
        WebhookService.set_active(webhook_id, request.form.get("active") == "1", current_user)
    except _ERRORS as exc:
        flash(str(exc), "error")
    return redirect(url_for("ui.integrations"))


# ---------------------------------------------------------------- operations (I-09, I-18)
@ui_bp.route("/admin/operations")
@require_role_web("ADMINISTRATOR")
def operations():
    return render_template(
        "admin/operations.html",
        backup=backup_service.status_summary(),
        last_backup=backup_service.read_status(),
        migration=backup_service.migration_state(),
        anchor=AuditChainService.read_anchor(),
        result=None,
    )


@ui_bp.route("/admin/operations/audit-verify", methods=["POST"])
@require_role_web("ADMINISTRATOR")
def operations_audit_verify():
    return render_template(
        "admin/operations.html",
        backup=backup_service.status_summary(),
        last_backup=backup_service.read_status(),
        migration=backup_service.migration_state(),
        anchor=AuditChainService.read_anchor(),
        result=AuditChainService.verify(),
    )

"""Operations, reporting and integration endpoints of the improvement pack: catalogue health
and KPIs (I-19, I-10), backup status and audit verification (I-09, I-18), saved searches
(I-26), fleet occurrence feedback (I-28), API tokens, webhooks and the change feed (I-29), and
Hub -> Main Controller consolidation (I-36)."""

from flask import jsonify, make_response, request

from app.api.v1 import api_v1_bp
from app.api.v1._errors import error_response
from app.api.v1.serializers import revision_payload
from app.audit_chain import AuditChainService
from app.auth.decorators import (
    allow_token,
    current_user,
    login_required,
    require_role,
)
from app.auth.roles import OVERSIGHT_ROLES
from app.domain.errors import DomainError
from app.services import backup_service
from app.services.health_report_service import HealthReportService
from app.services.hub_consolidation_service import HubConsolidationService
from app.services.integration_service import (
    TOKEN_SCOPES,
    ApiTokenService,
    ChangeFeedService,
    WebhookService,
)
from app.services.kpi_service import KpiService
from app.services.occurrence_service import OccurrenceService
from app.services.saved_search_service import (
    COLUMNS,
    DEFAULT_COLUMNS,
    SavedSearchService,
    query_string,
)
from app.services.status_code_service import ValidationFailed

_WORKING = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")


def _body() -> dict:
    return request.get_json(silent=True) or {}


# ---------------------------------------------------------------- reports (I-19, I-10)
@api_v1_bp.get("/reports/catalogue-health")
@require_role("ADMINISTRATOR", "CHIEF_ENGINEER", "REVIEWER")
def catalogue_health():
    return jsonify(HealthReportService.report())


@api_v1_bp.get("/reports/kpis")
@require_role("ADMINISTRATOR", "CHIEF_ENGINEER")
def success_metrics():
    return jsonify(KpiService.compute())


# ---------------------------------------------------------------- backup / audit chain
@api_v1_bp.get("/operations/backup-status")
@require_role("ADMINISTRATOR")
def backup_status():
    return jsonify(summary=backup_service.status_summary(), last=backup_service.read_status())


@api_v1_bp.post("/operations/audit-verify")
@require_role("ADMINISTRATOR")
def audit_verify():
    """I-18: walk the whole audit hash chain now."""
    return jsonify(AuditChainService.verify())


# ---------------------------------------------------------------- saved searches (I-26)
def _saved_payload(row) -> dict:
    definition = SavedSearchService.definition_of(row)
    return {
        "id": row.id,
        "name": row.name,
        "filters": definition["filters"],
        "columns": definition["columns"],
        "query_string": query_string(definition),
        "created_at": row.created_at,
    }


@api_v1_bp.get("/saved-searches")
@login_required
def list_saved_searches():
    return jsonify(
        items=[_saved_payload(r) for r in SavedSearchService.list_for(current_user)],
        available_columns=[{"key": k, "label": v} for k, v in COLUMNS.items()],
        default_columns=list(DEFAULT_COLUMNS),
    )


@api_v1_bp.post("/saved-searches")
@login_required
def create_saved_search():
    body = _body()
    try:
        row = SavedSearchService.save(current_user, body.get("name", ""), body)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(_saved_payload(row)), 201


@api_v1_bp.delete("/saved-searches/<int:search_id>")
@login_required
def delete_saved_search(search_id: int):
    try:
        SavedSearchService.delete(current_user, search_id)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return "", 204


# ---------------------------------------------------------------- fleet occurrences (I-28)
def _occurrence_payload(batch) -> dict:
    return {
        "id": batch.id,
        "source_label": batch.source_label,
        "period_start": batch.period_start,
        "period_end": batch.period_end,
        "imported_by": batch.imported_by,
        "imported_at": batch.imported_at,
        "matched_codes": batch.row_count,
        "unmatched_rows": batch.unmatched_count,
    }


@api_v1_bp.get("/occurrence-imports")
@require_role("ADMINISTRATOR", "CHIEF_ENGINEER")
def list_occurrence_imports():
    return jsonify(items=[_occurrence_payload(b) for b in OccurrenceService.list_imports()])


@api_v1_bp.post("/occurrence-imports")
@require_role("ADMINISTRATOR", "CHIEF_ENGINEER")
def create_occurrence_import():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify(error="validation_error", message="file is required"), 422
    try:
        batch = OccurrenceService.import_counts(
            upload.filename,
            upload.read(),
            request.form.get("source_label", ""),
            request.form.get("period_start", ""),
            request.form.get("period_end", ""),
            current_user,
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(_occurrence_payload(batch)), 201


@api_v1_bp.get("/reports/occurrences")
@require_role("ADMINISTRATOR", "CHIEF_ENGINEER")
def occurrence_report():
    return jsonify(
        OccurrenceService.report(
            top=request.args.get("top", 20, type=int),
            min_periods=request.args.get("min_periods", 1, type=int),
        )
    )


# ---------------------------------------------------------------- tokens / webhooks / feed (I-29)
def _token_payload(row) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "token_prefix": row.token_prefix,
        "scopes": row.scopes.split(),
        "expires_at": row.expires_at,
        "last_used_at": row.last_used_at,
        "revoked_at": row.revoked_at,
        "created_at": row.created_at,
    }


@api_v1_bp.get("/api-tokens")
@require_role("ADMINISTRATOR")
def list_api_tokens():
    return jsonify(
        items=[_token_payload(t) for t in ApiTokenService.list_all(current_user)],
        available_scopes=[{"scope": k, "description": v} for k, v in TOKEN_SCOPES.items()],
    )


@api_v1_bp.post("/api-tokens")
@require_role("ADMINISTRATOR")
def create_api_token():
    body = _body()
    try:
        row, plaintext = ApiTokenService.create(
            current_user,
            body.get("name", ""),
            body.get("scopes") or [],
            int(body.get("expires_in_days", 90)),
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    payload = _token_payload(row)
    payload["token"] = plaintext  # shown exactly once
    return jsonify(payload), 201


@api_v1_bp.delete("/api-tokens/<int:token_id>")
@require_role("ADMINISTRATOR")
def revoke_api_token(token_id: int):
    try:
        ApiTokenService.revoke(token_id, current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return "", 204


def _webhook_payload(row) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "url": row.url,
        "events": row.events.split(","),
        "is_active": bool(row.is_active),
        "last_delivery_at": row.last_delivery_at,
        "last_status": row.last_status,
        "created_at": row.created_at,
    }


@api_v1_bp.get("/webhooks")
@require_role("ADMINISTRATOR")
def list_webhooks():
    return jsonify(items=[_webhook_payload(w) for w in WebhookService.list_all(current_user)])


@api_v1_bp.post("/webhooks")
@require_role("ADMINISTRATOR")
def create_webhook():
    body = _body()
    try:
        row, secret = WebhookService.create(
            current_user, body.get("name", ""), body.get("url", ""), body.get("events")
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    payload = _webhook_payload(row)
    payload["secret"] = secret  # shown exactly once
    return jsonify(payload), 201


@api_v1_bp.patch("/webhooks/<int:webhook_id>")
@require_role("ADMINISTRATOR")
def update_webhook(webhook_id: int):
    try:
        row = WebhookService.set_active(
            webhook_id, bool(_body().get("is_active", True)), current_user
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(_webhook_payload(row))


@api_v1_bp.get("/webhooks/<int:webhook_id>/deliveries")
@require_role("ADMINISTRATOR")
def webhook_deliveries(webhook_id: int):
    return jsonify(
        items=[
            {
                "id": d.id,
                "event": d.event,
                "http_status": d.http_status,
                "ok": bool(d.ok),
                "error": d.error,
                "delivered_at": d.delivered_at,
            }
            for d in WebhookService.deliveries(webhook_id, current_user)
        ]
    )


@api_v1_bp.get("/changes")
@allow_token("changes:read")
@login_required
def change_feed():
    """Releases, deprecations, reinstatements and archivals in audit order. Pass the
    `next_since_id` of the previous response as `since_id`; ETag / If-None-Match supported."""
    feed = ChangeFeedService.since(
        request.args.get("since_id", 0, type=int), request.args.get("limit", 100, type=int)
    )
    response = make_response(jsonify(feed))
    response.set_etag(
        f"{feed['next_since_id']}-{len(feed['items'])}-{int(feed['has_more'])}", weak=True
    )
    return response.make_conditional(request)


# ---------------------------------------------------------------- Hub consolidation (I-36)
@api_v1_bp.get("/hub-consolidation/mapping")
@require_role(*OVERSIGHT_ROLES)
def hub_mapping_report():
    return jsonify(HubConsolidationService.mapping_report(request.args.get("group", type=int)))


@api_v1_bp.post("/status-codes/<int:status_code_id>/mc-drafts")
@require_role("ADMINISTRATOR", "ENGINEER")
def create_mc_draft_from_hub(status_code_id: int):
    """I-36: copy a Hub Controller code into a new Main Controller Draft."""
    body = _body()
    try:
        revision, _mapping = HubConsolidationService.create_mc_draft(
            status_code_id,
            int(body.get("functional_system_group") or 0),
            int(body.get("functional_subgroup") or 0),
            current_user,
        )
    except ValidationFailed as exc:
        return error_response(exc)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(revision_payload(revision)), 201


@api_v1_bp.post("/hub-consolidation/deprecation-requests")
@require_role("ADMINISTRATOR")
def hub_bulk_deprecation():
    try:
        result = HubConsolidationService.request_hub_deprecation(
            int(_body().get("functional_system_group") or 0), current_user
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(result)

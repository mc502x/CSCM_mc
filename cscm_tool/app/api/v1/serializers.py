"""Shared response payload builders matching docs/artifacts/openapi.yaml schemas."""

import json

from app.models.audit import AuditLogEntry
from app.models.change_request import ChangeRequest, DomainSignoff, ReviewComment
from app.models.import_job import ImportJob
from app.models.release import Release
from app.models.status_code import StatusCodeRevision


def _access_code(lookup) -> str | None:
    return lookup.code if lookup is not None else None


def revision_payload(revision: StatusCodeRevision) -> dict:
    status_code = revision.status_code
    group = status_code.functional_system_group
    subgroup = status_code.functional_subgroup
    return {
        "id": revision.id,
        "status_code_id": status_code.id,
        "status_code_identifier": status_code.status_code_identifier,
        # v3: functional_system_group/functional_subgroup `code` is display
        # only (WTUR/WROT are each reused for a second, numerically distinct
        # group) — the *_id fields are the unambiguous, round-trippable
        # values a client must submit back (see app/services/lookup_service.py).
        "functional_system_group": group.code,
        "functional_system_group_id": group.id,
        "functional_system_group_label": group.label,
        "functional_system_group_range_start": group.range_start,
        "functional_system_group_range_end": group.range_end,
        "functional_subgroup": subgroup.code,
        "functional_subgroup_id": subgroup.id,
        "functional_subgroup_label": subgroup.label,
        "turbine_platforms": sorted(p.turbine_platform.code for p in revision.platforms),
        "is_sandbox": bool(status_code.is_sandbox),
        "platform_variant_of_status_code_id": status_code.platform_variant_of_status_code_id,
        "legacy_reference_number": status_code.legacy_reference_number,
        "revision_number": revision.revision_number,
        "is_current": bool(revision.is_current),
        "title": revision.title,
        "description": revision.description,
        "software_version": revision.software_version,
        "status_category": revision.status_category,
        "available_group": revision.available_group,
        "alarm_flag": bool(revision.alarm_flag),
        "set_delay": revision.set_delay,
        "reset_delay": revision.reset_delay,
        "up_down_counter": bool(revision.up_down_counter),
        "trigger_snapshot": bool(revision.trigger_snapshot),
        "loadless_spinning_permitted": bool(revision.loadless_spinning_permitted),
        "number_of_times_repeated": revision.number_of_times_repeated,
        "repeated_over_the_course": revision.repeated_over_the_course,
        "status_code_for_repeated_error": revision.status_code_for_repeated_error,
        "yaw_program": revision.yaw_program,
        "manual_reset_program": revision.manual_reset_program,
        "auto_reset_program": revision.auto_reset_program,
        "converter_reactive_power_program": revision.converter_reactive_power_program,
        "brake_program": revision.brake_program,
        "umrichterprogramm_gsc": revision.umrichterprogramm_gsc,
        "umrichterprogramm_msc": revision.umrichterprogramm_msc,
        "yaw_bearing_lubrication_program": revision.yaw_bearing_lubrication_program,
        # SEC-013/FR-025a: Engineer-proposed until admin_signoff_at is set.
        "development_access": _access_code(revision.development_access),
        "development_access_id": revision.development_access_id,
        "sales_access": _access_code(revision.sales_access),
        "sales_access_id": revision.sales_access_id,
        "tcc_access": _access_code(revision.tcc_access),
        "tcc_access_id": revision.tcc_access_id,
        "service_access": _access_code(revision.service_access),
        "service_access_id": revision.service_access_id,
        "turbine_operator_package_access": _access_code(revision.turbine_operator_package_access),
        "turbine_operator_package_access_id": revision.turbine_operator_package_access_id,
        "grid_operator_access": _access_code(revision.grid_operator_access),
        "grid_operator_access_id": revision.grid_operator_access_id,
        "service_partner_access": _access_code(revision.service_partner_access),
        "service_partner_access_id": revision.service_partner_access_id,
        "customer_access": _access_code(revision.customer_access),
        "customer_access_id": revision.customer_access_id,
        # Derived, read-only (docs/06-data-dictionary.md §2e) — always mirror
        # the parent Functional System Group, never independently entered.
        "logical_node": group.code,
        "node_value": group.sort_order,
        "owner_id": revision.owner_id,
        "lifecycle_status": revision.lifecycle_status,
        "created_by": revision.created_by,
        "created_at": revision.created_at,
        "reviewer_signoff_by": revision.reviewer_signoff_by,
        "reviewer_signoff_at": revision.reviewer_signoff_at,
        "admin_signoff_by": revision.admin_signoff_by,
        "admin_signoff_at": revision.admin_signoff_at,
        "chief_engineer_approved_by": revision.chief_engineer_approved_by,
        "chief_engineer_approval_date": revision.chief_engineer_approval_date,
        "effective_date": revision.effective_date,
        "deprecated_reason": revision.deprecated_reason,
        "superseded_by_status_code_id": revision.superseded_by_status_code_id,
    }


def review_comment_payload(comment: ReviewComment) -> dict:
    return {
        "id": comment.id,
        "author_id": comment.author_id,
        "comment_text": comment.comment_text,
        "decision": comment.decision,
        "created_at": comment.created_at,
    }


def domain_signoff_payload(signoff: DomainSignoff) -> dict:
    return {
        "id": signoff.id,
        "engineering_domain": signoff.engineering_domain.code,
        "signed_off_by": signoff.signed_off_by,
        "signed_off_at": signoff.signed_off_at,
        "status": "SIGNED_OFF",
    }


def pending_domain_signoff_payload(domain_code: str) -> dict:
    return {
        "id": None,
        "engineering_domain": domain_code,
        "signed_off_by": None,
        "signed_off_at": None,
        "status": "REQUIRED_PENDING",
    }


def release_payload(release: Release) -> dict:
    return {
        "id": release.id,
        "name": release.name,
        "version_label": release.version_label,
        "description": release.description,
        "scope_filter": json.loads(release.scope_filter or "{}"),
        "status": release.status,
        "created_by": release.created_by,
        "created_at": release.created_at,
        "published_by": release.published_by,
        "published_at": release.published_at,
        "item_count": len(release.items),
    }


def audit_log_entry_payload(entry: AuditLogEntry) -> dict:
    return {
        "id": entry.id,
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id,
        "action": entry.action,
        "actor_id": entry.actor_id,
        "occurred_at": entry.occurred_at,
        "before_value": json.loads(entry.before_value) if entry.before_value else None,
        "after_value": json.loads(entry.after_value) if entry.after_value else None,
        "ip_address": entry.ip_address,
        "request_id": entry.request_id,
    }


def change_request_payload(cr: ChangeRequest) -> dict:
    return {
        "id": cr.id,
        "status_code_revision_id": cr.status_code_revision_id,
        "cr_type": cr.cr_type,
        "requested_by": cr.requested_by,
        "justification": cr.justification,
        "import_job_id": cr.import_job_id,
        "state": cr.state,
        "submitted_at": cr.submitted_at,
        "chief_engineer_decided_at": cr.chief_engineer_decided_at,
        "chief_engineer_decided_by": cr.chief_engineer_decided_by,
        "comments": [review_comment_payload(c) for c in cr.comments],
        "domain_signoffs": [domain_signoff_payload(d) for d in cr.domain_signoffs],
    }


def import_job_payload(job: ImportJob) -> dict:
    return {
        "id": job.id,
        "requested_by": job.requested_by,
        "source_format": job.source_format,
        "source_file_reference": job.source_file_reference,
        "row_count": job.row_count,
        "status": job.status,
        "created_count": job.created_count,
        "error_count": job.error_count,
        "error_report_reference": job.error_report_reference,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }

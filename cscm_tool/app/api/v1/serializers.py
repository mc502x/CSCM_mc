"""Shared response payload builders matching docs/artifacts/openapi.yaml schemas."""

import json

from app.models.change_request import ChangeRequest, DomainSignoff, ReviewComment
from app.models.release import Release
from app.models.status_code import StatusCodeRevision


def revision_payload(revision: StatusCodeRevision) -> dict:
    status_code = revision.status_code
    return {
        "id": revision.id,
        "status_code_id": status_code.id,
        "status_code_identifier": status_code.status_code_identifier,
        "functional_system_group": status_code.functional_system_group.code,
        "functional_subgroup": (
            status_code.functional_subgroup.code if status_code.functional_subgroup else None
        ),
        "turbine_platforms": sorted(p.turbine_platform.code for p in revision.platforms),
        "is_sandbox": bool(status_code.is_sandbox),
        "platform_variant_of_status_code_id": status_code.platform_variant_of_status_code_id,
        "revision_number": revision.revision_number,
        "is_current": bool(revision.is_current),
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


def change_request_payload(cr: ChangeRequest) -> dict:
    return {
        "id": cr.id,
        "status_code_revision_id": cr.status_code_revision_id,
        "cr_type": cr.cr_type,
        "requested_by": cr.requested_by,
        "justification": cr.justification,
        "state": cr.state,
        "submitted_at": cr.submitted_at,
        "chief_engineer_decided_at": cr.chief_engineer_decided_at,
        "chief_engineer_decided_by": cr.chief_engineer_decided_by,
        "comments": [review_comment_payload(c) for c in cr.comments],
        "domain_signoffs": [domain_signoff_payload(d) for d in cr.domain_signoffs],
    }

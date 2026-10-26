"""Success metrics (I-10): the KPIs the business case promises (docs/01-executive-summary.md
§4), computed from timestamps the system already stores - nothing is tracked twice.

* median business days from submission to Chief Engineer approval  (target <= 7)
* median business days from a cross-domain sign-off request to the sign-off (target <= 3)
* share of Released revisions with a complete audit trail          (target 100 %)
* age distribution of everything waiting for a decision
* codes whose owner is no longer an active user ("unknown owner")"""

from datetime import UTC, datetime, timedelta
from statistics import median

from sqlalchemy import text

from app.extensions import db
from app.models.change_request import ChangeRequest, DomainSignoff, DomainSignoffRequest
from app.models.status_code import StatusCode, StatusCodeRevision
from app.models.user import User
from app.services.sla_service import SlaService, business_days_between
from app.utils import format_iso, parse_iso

TARGET_APPROVAL_DAYS = 7
TARGET_CROSS_DOMAIN_DAYS = 3

_REQUIRED_TRAIL = (
    "SUBMIT_FOR_REVIEW",
    "REVIEWER_SIGNOFF",
    "ADMIN_SIGNOFF",
    "CHIEF_ENGINEER_APPROVE",
    "RELEASE_PUBLISH",
)
_AGE_BUCKETS = (("0-1 days", 0, 1), ("2-3 days", 2, 3), ("4-5 days", 4, 5), ("6+ days", 6, None))


def _summary(values: list[int], target: int) -> dict:
    if not values:
        return {"sample_size": 0, "median_days": None, "target_days": target, "meets_target": None}
    med = median(values)
    return {
        "sample_size": len(values),
        "median_days": med,
        "p90_days": sorted(values)[min(len(values) - 1, int(len(values) * 0.9))],
        "target_days": target,
        "meets_target": med <= target,
    }


class KpiService:
    @staticmethod
    def approval_times(since: datetime | None = None) -> list[int]:
        query = db.session.query(ChangeRequest).filter(
            ChangeRequest.submitted_at.isnot(None),
            ChangeRequest.chief_engineer_decided_at.isnot(None),
            ChangeRequest.state == "APPROVED",
        )
        if since is not None:
            query = query.filter(ChangeRequest.chief_engineer_decided_at >= format_iso(since))
        return [
            business_days_between(
                parse_iso(cr.submitted_at).date(), parse_iso(cr.chief_engineer_decided_at).date()
            )
            for cr in query
        ]

    @staticmethod
    def cross_domain_times(since: datetime | None = None) -> list[int]:
        rows = (
            db.session.query(DomainSignoffRequest, DomainSignoff)
            .join(
                DomainSignoff,
                (DomainSignoff.change_request_id == DomainSignoffRequest.change_request_id)
                & (
                    DomainSignoff.engineering_domain_id
                    == DomainSignoffRequest.engineering_domain_id
                ),
            )
            .all()
        )
        values = []
        for request, signoff in rows:
            if since is not None and signoff.signed_off_at < format_iso(since):
                continue
            values.append(
                business_days_between(
                    parse_iso(request.created_at).date(), parse_iso(signoff.signed_off_at).date()
                )
            )
        return values

    @staticmethod
    def audit_trail_completeness() -> dict:
        released_ids = {
            rid
            for (rid,) in db.session.query(StatusCodeRevision.id)
            .join(StatusCode, StatusCode.id == StatusCodeRevision.status_code_id)
            .filter(StatusCodeRevision.lifecycle_status == "RELEASED", StatusCode.is_sandbox == 0)
        }
        if not released_ids:
            return {
                "released_revisions": 0,
                "complete": 0,
                "percent": None,
                "incomplete_examples": [],
            }
        placeholders = ",".join(f"'{a}'" for a in _REQUIRED_TRAIL)
        rows = db.session.execute(
            text(
                "SELECT entity_id, COUNT(DISTINCT action) FROM audit_log_entry "  # noqa: S608  # nosec B608
                f"WHERE entity_type = 'StatusCodeRevision' AND action IN ({placeholders}) "
                "GROUP BY entity_id"
            )
        )
        complete_ids = {eid for eid, n in rows if n == len(_REQUIRED_TRAIL) and eid in released_ids}
        incomplete = sorted(released_ids - complete_ids)
        examples = []
        for rid in incomplete[:10]:
            revision = db.session.get(StatusCodeRevision, rid)
            if revision is not None:
                examples.append(revision.status_code.status_code_identifier)
        return {
            "released_revisions": len(released_ids),
            "complete": len(complete_ids),
            "percent": round(100 * len(complete_ids) / len(released_ids), 1),
            "incomplete_examples": examples,
        }

    @staticmethod
    def queue_age_distribution() -> dict:
        waiting = SlaService.waiting()
        distribution: dict[str, dict[str, int]] = {"review": {}, "approval": {}}
        for stage in distribution:
            for label, _low, _high in _AGE_BUCKETS:
                distribution[stage][label] = 0
        for _cr, info in waiting:
            for label, low, high in _AGE_BUCKETS:
                if info["age_days"] >= low and (high is None or info["age_days"] <= high):
                    distribution[info["stage"]][label] += 1
                    break
        return {
            "waiting_total": len(waiting),
            "by_stage": distribution,
            "red": sum(1 for _c, i in waiting if i["level"] == "red"),
            "amber": sum(1 for _c, i in waiting if i["level"] == "amber"),
        }

    @staticmethod
    def unknown_owner() -> dict:
        rows = (
            db.session.query(StatusCode, User)
            .outerjoin(User, User.id == StatusCode.owner_id)
            .filter(StatusCode.is_sandbox == 0)
            .all()
        )
        orphaned = [
            code.status_code_identifier or f"draft #{code.id}"
            for code, owner in rows
            if owner is None or not owner.is_active
        ]
        return {"count": len(orphaned), "examples": orphaned[:25]}

    @staticmethod
    def compute(now: datetime | None = None) -> dict:
        now = now or datetime.now(UTC)
        recent = now - timedelta(days=90)
        return {
            "generated_at": format_iso(now),
            "approval_time": {
                "all_time": _summary(KpiService.approval_times(), TARGET_APPROVAL_DAYS),
                "last_90_days": _summary(KpiService.approval_times(recent), TARGET_APPROVAL_DAYS),
            },
            "cross_domain_turnaround": {
                "all_time": _summary(KpiService.cross_domain_times(), TARGET_CROSS_DOMAIN_DAYS),
                "last_90_days": _summary(
                    KpiService.cross_domain_times(recent), TARGET_CROSS_DOMAIN_DAYS
                ),
            },
            "audit_trail": KpiService.audit_trail_completeness(),
            "queues": KpiService.queue_age_distribution(),
            "unknown_owner": KpiService.unknown_owner(),
        }

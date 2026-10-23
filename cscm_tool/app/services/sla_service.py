"""Workflow SLA tracking (I-08): how long a CR has waited at its current stage, in
business days (Monday-Friday; no holiday calendar), and whether that is amber/red
against the Administrator-configured thresholds.

The business case promises a median of at most 7 business days from submission to
approval (docs/01-executive-summary.md §4); these thresholds are what turns that
promise into something a queue can show."""

from datetime import UTC, date, datetime, timedelta

from app.extensions import db
from app.models.change_request import ChangeRequest
from app.models.operations import AppSetting
from app.models.status_code import StatusCodeRevision
from app.services.settings_service import SETTINGS
from app.utils import parse_iso

_STAGES = {"REVIEW": "review", "PENDING_APPROVAL": "approval"}


def business_days_between(start: date, end: date) -> int:
    """Weekdays elapsed after `start` up to and including `end` (0 if end <= start)."""
    count = 0
    day = start
    while day < end:
        day += timedelta(days=1)
        if day.weekday() < 5:
            count += 1
    return count


class SlaService:
    @staticmethod
    def thresholds() -> dict[str, dict[str, int]]:
        keys = [k for k in SETTINGS if k.startswith("sla.")]
        stored = {
            row.key: row.value
            for row in db.session.query(AppSetting).filter(AppSetting.key.in_(keys)).all()
        }
        value = lambda key: int(stored.get(key, SETTINGS[key][0]))  # noqa: E731
        return {
            stage: {
                "amber": value(f"sla.{stage}.amber_days"),
                "red": value(f"sla.{stage}.red_days"),
            }
            for stage in ("review", "approval")
        }

    @staticmethod
    def stage_entered_at(cr: ChangeRequest) -> str | None:
        revision = cr.revision
        if revision.lifecycle_status == "REVIEW":
            return cr.submitted_at
        if revision.lifecycle_status == "PENDING_APPROVAL":
            stamps = [s for s in (revision.reviewer_signoff_at, revision.admin_signoff_at) if s]
            return max(stamps) if stamps else cr.submitted_at
        return None

    @staticmethod
    def info(
        cr: ChangeRequest, now: datetime | None = None, thresholds: dict | None = None
    ) -> dict | None:
        """None for a CR that is not waiting on a decision."""
        stage = _STAGES.get(cr.revision.lifecycle_status)
        entered = SlaService.stage_entered_at(cr)
        if stage is None or entered is None:
            return None
        now = now or datetime.now(UTC)
        limits = (thresholds or SlaService.thresholds())[stage]
        age = business_days_between(parse_iso(entered).date(), now.date())
        level = "red" if age >= limits["red"] else "amber" if age >= limits["amber"] else "ok"
        return {
            "stage": stage,
            "entered_at": entered,
            "age_days": age,
            "level": level,
            "amber_days": limits["amber"],
            "red_days": limits["red"],
        }

    @staticmethod
    def waiting(now: datetime | None = None) -> list[tuple[ChangeRequest, dict]]:
        """Every CR waiting on a decision with its SLA info, oldest first."""
        thresholds = SlaService.thresholds()
        crs = (
            db.session.query(ChangeRequest)
            .join(
                StatusCodeRevision, ChangeRequest.status_code_revision_id == StatusCodeRevision.id
            )
            .filter(StatusCodeRevision.lifecycle_status.in_(tuple(_STAGES)))
            .order_by(ChangeRequest.id)
            .all()
        )
        rows = []
        for cr in crs:
            info = SlaService.info(cr, now, thresholds)
            if info is not None:
                rows.append((cr, info))
        rows.sort(key=lambda row: (-row[1]["age_days"], row[0].id))
        return rows

    @staticmethod
    def stalled(now: datetime | None = None) -> list[tuple[ChangeRequest, dict]]:
        return [row for row in SlaService.waiting(now) if row[1]["level"] != "ok"]

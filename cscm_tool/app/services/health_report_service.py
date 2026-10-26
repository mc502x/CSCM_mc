"""Catalogue health report and number-range capacity forecast (I-19).

Four questions an Administrator or Chief Engineer should be able to answer without a
query tool:

* *capacity* - how full is each subgroup's number band, and which ones are about to run out
  (allocation only fails once a band is already exhausted)?
* *missing data* - which released/approved codes lack optional-but-expected content
  (remedy text, audience access, a software-version range)?
* *inconsistencies* - combinations that are probably wrong (an INFO code with an alarm, a
  repeat threshold without an escalation code, a planned deprecation date already past)
* *unused numbers* - gaps inside a band. Numbers are never reused (BR-001), so a gap is lost
  capacity worth knowing about, not something to fill.

Read-only; nothing here changes data."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.extensions import db
from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup
from app.models.status_code import StatusCode, StatusCodeRevision
from app.services.settings_service import SettingsService

_REAL_PREFIX_LEN = len("StCd-")
_SAMPLE = 25


def _allocated_numbers() -> dict[int, list[int]]:
    """group id -> sorted allocated numbers (real identifiers only)."""
    rows = db.session.execute(
        text(
            "SELECT functional_system_group_id, "
            "CAST(SUBSTR(status_code_identifier, :o) AS INTEGER) "
            "FROM status_code WHERE status_code_identifier GLOB 'StCd-[0-9]*' "
            "ORDER BY functional_system_group_id, 2"
        ),
        {"o": _REAL_PREFIX_LEN + 1},
    )
    grouped: dict[int, list[int]] = {}
    for group_id, number in rows:
        grouped.setdefault(group_id, []).append(number)
    return grouped


class HealthReportService:
    @staticmethod
    def capacity() -> list[dict]:
        """One row per active subgroup, fullest first."""
        alert_percent = SettingsService.get_int("health.capacity_alert_percent")
        alert_numbers = SettingsService.get_int("health.capacity_alert_numbers")
        allocated = _allocated_numbers()
        rows = []
        subgroups = (
            db.session.query(LookupFunctionalSubgroup, LookupFunctionalSystemGroup)
            .join(
                LookupFunctionalSystemGroup,
                LookupFunctionalSystemGroup.id
                == LookupFunctionalSubgroup.functional_system_group_id,
            )
            .filter(LookupFunctionalSubgroup.is_active == 1)
            .order_by(LookupFunctionalSystemGroup.sort_order, LookupFunctionalSubgroup.sort_order)
            .all()
        )
        for subgroup, group in subgroups:
            inside = [
                n
                for n in allocated.get(group.id, [])
                if subgroup.sub_range_start <= n <= subgroup.sub_range_end
            ]
            total = subgroup.sub_range_end - subgroup.sub_range_start + 1
            last = max(inside) if inside else subgroup.sub_range_start - 1
            remaining = subgroup.sub_range_end - last
            percent = round(100 * remaining / total, 1)
            rows.append(
                {
                    "functional_system_group": group.code,
                    "functional_system_group_id": group.id,
                    "controller": "HC" if group.controller_type == "HUB" else "MC",
                    "functional_subgroup": subgroup.code,
                    "functional_subgroup_id": subgroup.id,
                    "label": subgroup.label,
                    "range_start": subgroup.sub_range_start,
                    "range_end": subgroup.sub_range_end,
                    "total": total,
                    "allocated": len(inside),
                    "remaining": remaining,
                    "percent_remaining": percent,
                    "alert": bool(inside)
                    and (remaining <= alert_numbers or percent <= alert_percent),
                    "exhausted": remaining <= 0,
                }
            )
        rows.sort(key=lambda r: (r["percent_remaining"], r["functional_subgroup_id"]))
        return rows

    @staticmethod
    def unused_numbers() -> list[dict]:
        allocated = _allocated_numbers()
        out = []
        subgroups = (
            db.session.query(LookupFunctionalSubgroup, LookupFunctionalSystemGroup)
            .join(
                LookupFunctionalSystemGroup,
                LookupFunctionalSystemGroup.id
                == LookupFunctionalSubgroup.functional_system_group_id,
            )
            .order_by(LookupFunctionalSystemGroup.sort_order, LookupFunctionalSubgroup.sort_order)
            .all()
        )
        for subgroup, group in subgroups:
            inside = sorted(
                n
                for n in allocated.get(group.id, [])
                if subgroup.sub_range_start <= n <= subgroup.sub_range_end
            )
            if len(inside) < 2:
                continue
            present = set(inside)
            gaps = [n for n in range(inside[0], inside[-1] + 1) if n not in present]
            if gaps:
                out.append(
                    {
                        "functional_system_group": group.code,
                        "functional_subgroup": subgroup.code,
                        "gap_count": len(gaps),
                        "examples": [f"StCd-{n:05d}" for n in gaps[:_SAMPLE]],
                    }
                )
        return out

    @staticmethod
    def _current_decided() -> list[tuple[StatusCodeRevision, StatusCode]]:
        rows = (
            db.session.query(StatusCodeRevision, StatusCode)
            .join(StatusCode, StatusCode.id == StatusCodeRevision.status_code_id)
            .filter(
                StatusCode.is_sandbox == 0,
                StatusCodeRevision.is_current == 1,
                StatusCodeRevision.lifecycle_status.in_(("APPROVED", "RELEASED")),
            )
            .all()
        )
        return [(revision, code) for revision, code in rows]

    @staticmethod
    def missing_data() -> dict:
        checks = {
            "remedy_text": lambda r: not r.remedy_text,
            "affected_component": lambda r: not r.affected_component,
            "software_version_range": lambda r: r.applies_from_version_id is None
            and r.applies_to_version_id is None,
            "audience_access": lambda r: all(
                getattr(r, f"{a}_id") is None
                for a in (
                    "development_access",
                    "sales_access",
                    "tcc_access",
                    "service_access",
                    "turbine_operator_package_access",
                    "grid_operator_access",
                    "service_partner_access",
                    "customer_access",
                )
            ),
        }
        decided = HealthReportService._current_decided()
        result: dict = {"checked": len(decided), "fields": {}}
        for name, missing in checks.items():
            hits = [(r, c) for r, c in decided if missing(r)]
            result["fields"][name] = {
                "count": len(hits),
                "examples": [c.status_code_identifier for _r, c in hits[:_SAMPLE]],
            }
        return result

    @staticmethod
    def inconsistencies(today: str | None = None) -> list[dict]:
        today = today or datetime.now(UTC).date().isoformat()
        rules = [
            (
                "INFO_WITH_ALARM",
                "An INFO status should not raise an alarm.",
                lambda r: r.status_category == "INFO" and r.alarm_flag,
            ),
            (
                "REPEAT_WITHOUT_ESCALATION",
                "A repeat threshold is set but no escalation code.",
                lambda r: r.number_of_times_repeated is not None
                and r.status_code_for_repeated_error is None,
            ),
            (
                "ESCALATION_WITHOUT_THRESHOLD",
                "An escalation code is set but no repeat threshold.",
                lambda r: r.status_code_for_repeated_error is not None
                and r.number_of_times_repeated is None,
            ),
            (
                "WINDOW_WITHOUT_THRESHOLD",
                "A repeat window is set but no repeat count.",
                lambda r: bool(r.repeated_over_the_course) and r.number_of_times_repeated is None,
            ),
            (
                "PLANNED_DEPRECATION_PASSED",
                "The planned deprecation date has passed but the code is still live.",
                lambda r: bool(r.planned_deprecation_date)
                and r.planned_deprecation_date < today
                and r.lifecycle_status in ("APPROVED", "RELEASED"),
            ),
        ]
        findings = []
        decided = HealthReportService._current_decided()
        for code, description, test in rules:
            hits = [c.status_code_identifier for r, c in decided if test(r)]
            if hits:
                findings.append(
                    {
                        "rule": code,
                        "description": description,
                        "count": len(hits),
                        "examples": hits[:_SAMPLE],
                    }
                )
        return findings

    @staticmethod
    def upcoming(days: int = 90, today: str | None = None) -> dict:
        start = today or datetime.now(UTC).date().isoformat()
        end = (datetime.fromisoformat(start) + timedelta(days=days)).date().isoformat()
        rows = (
            db.session.query(StatusCodeRevision, StatusCode)
            .join(StatusCode, StatusCode.id == StatusCodeRevision.status_code_id)
            .filter(StatusCode.is_sandbox == 0, StatusCodeRevision.is_current == 1)
            .all()
        )
        deprecations = sorted(
            (
                {
                    "status_code_identifier": c.status_code_identifier,
                    "title": r.title,
                    "planned_deprecation_date": r.planned_deprecation_date,
                }
                for r, c in rows
                if r.planned_deprecation_date
                and start <= r.planned_deprecation_date <= end
                and r.lifecycle_status in ("APPROVED", "RELEASED")
            ),
            key=lambda d: d["planned_deprecation_date"],
        )
        effective = sorted(
            (
                {
                    "status_code_identifier": c.status_code_identifier,
                    "title": r.title,
                    "planned_effective_date": r.planned_effective_date,
                }
                for r, c in rows
                if r.planned_effective_date
                and r.planned_effective_date >= start
                and r.lifecycle_status in ("APPROVED", "REVIEW", "PENDING_APPROVAL", "DRAFT")
            ),
            key=lambda d: d["planned_effective_date"],
        )
        return {"window_days": days, "deprecations": deprecations, "effective": effective}

    @staticmethod
    def report() -> dict:
        capacity = HealthReportService.capacity()
        return {
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "capacity": capacity,
            "capacity_alerts": [c for c in capacity if c["alert"] or c["exhausted"]],
            "missing_data": HealthReportService.missing_data(),
            "inconsistencies": HealthReportService.inconsistencies(),
            "unused_numbers": HealthReportService.unused_numbers(),
            "upcoming": HealthReportService.upcoming(),
        }

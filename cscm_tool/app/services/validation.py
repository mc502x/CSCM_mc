"""Field-level and cross-field validation, per docs/06-data-dictionary.md
and its "Validation" column (FR-022, FR-027). Operates on the raw request
payload (string lookup codes, not yet resolved to FK ids) since that is the
natural point to validate before NumberingService/LookupService touch the
database. Returns a list of {"field", "message"} dicts; empty means valid."""

import re

_SOFTWARE_VERSION_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")

_SAFETY_ALLOWED_ALARM_BEHAVIOURS = {"LATCHING", "ESCALATING"}
_EMERGENCY_BRAKE_ALLOWED_CATEGORIES = {"FAULT", "SAFETY"}


def validate_revision_fields(data: dict) -> list[dict]:
    errors: list[dict] = []

    title = data.get("title") or ""
    if not (1 <= len(title) <= 120):
        errors.append({"field": "title", "message": "Title must be 1-120 characters."})

    description = data.get("description") or ""
    if not (10 <= len(description) <= 4000):
        errors.append(
            {"field": "description", "message": "Description must be 10-4000 characters."}
        )

    if title and description and title == description:
        errors.append({"field": "title", "message": "Title must not equal Description."})

    software_version = data.get("software_version") or ""
    if not _SOFTWARE_VERSION_RE.match(software_version):
        errors.append(
            {
                "field": "software_version",
                "message": "Software version must look like '4.12' or '4.12.0'.",
            }
        )

    delay_before_alarm_seconds = data.get("delay_before_alarm_seconds", 0)
    if not (0 <= delay_before_alarm_seconds <= 3600):
        errors.append(
            {"field": "delay_before_alarm_seconds", "message": "Must be between 0 and 3600."}
        )

    delay_before_reset_seconds = data.get("delay_before_reset_seconds", 0)
    if not (0 <= delay_before_reset_seconds <= 86400):
        errors.append(
            {"field": "delay_before_reset_seconds", "message": "Must be between 0 and 86400."}
        )

    alarm_behaviour = data.get("alarm_behaviour")
    status_category = data.get("status_category")

    if alarm_behaviour == "ESCALATING" and delay_before_alarm_seconds <= 0:
        errors.append(
            {
                "field": "delay_before_alarm_seconds",
                "message": "Required (> 0) when Alarm Behaviour is ESCALATING.",
            }
        )

    if data.get("reset_program") == "AUTO" and delay_before_reset_seconds <= 0:
        errors.append(
            {
                "field": "delay_before_reset_seconds",
                "message": "Required (> 0) when Reset Program is AUTO.",
            }
        )

    if status_category == "SAFETY" and alarm_behaviour not in _SAFETY_ALLOWED_ALARM_BEHAVIOURS:
        errors.append(
            {
                "field": "alarm_behaviour",
                "message": "Must be LATCHING or ESCALATING when Status Category is SAFETY.",
            }
        )

    if (
        data.get("brake_program") == "BP-4"
        and status_category not in _EMERGENCY_BRAKE_ALLOWED_CATEGORIES
    ):
        errors.append(
            {
                "field": "brake_program",
                "message": "Emergency Brake (BP-4) requires Status Category FAULT or SAFETY.",
            }
        )

    turbine_platforms = data.get("turbine_platforms")
    if turbine_platforms is not None and len(turbine_platforms) < 1:
        errors.append(
            {"field": "turbine_platforms", "message": "At least one Turbine Platform is required."}
        )

    return errors


def validate_deprecation_reason(reason: str | None) -> list[dict]:
    if reason is None or not (10 <= len(reason) <= 2000):
        return [
            {
                "field": "deprecated_reason",
                "message": "Deprecation reason must be 10-2000 characters.",
            }
        ]
    return []


def validate_justification(justification: str | None, required: bool) -> list[dict]:
    if not required:
        return []
    if justification is None or not (10 <= len(justification) <= 2000):
        return [{"field": "justification", "message": "Justification must be 10-2000 characters."}]
    return []

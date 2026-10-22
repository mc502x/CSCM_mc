"""Field-level and cross-field validation, per docs/06-data-dictionary.md
and its "Validation" column (FR-022, FR-027). Operates on the raw request
payload (string lookup codes/ids, not yet resolved to FK ids) since that is
the natural point to validate before NumberingService/LookupService touch
the database. Returns a list of {"field", "message"} dicts; empty means
valid.

v3 (2026-09-17): the old Safety-category/Alarm-Behaviour and Auto-reset/
delay cross-field rules are retired — docs/13-test-strategy.md is explicit
that "neither...the real data model supports" them, since status_category,
alarm, and reset are now a 3-value enum, a plain boolean, and eight numeric
program-reference fields respectively, none of which carry the old
semantics those rules depended on. available_group and the eight program
reference fields are soft-validated only (a currently-observed set that can
legitimately grow — docs/06-data-dictionary.md §2c, §9c) and are
deliberately NOT hard-validated here."""

import re

_DELAY_RE = re.compile(r"^\*?\d+(\.\d+)?\s?(ms|s|min|MIN|h|d)$")
_REPEAT_WINDOW_RE = re.compile(r"^\d+(\.\d+)?\s?(s|min|h|d)$")
_STATUS_CATEGORIES = {"ERROR", "WARNING", "INFO"}


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

    status_category = data.get("status_category")
    if status_category not in _STATUS_CATEGORIES:
        errors.append(
            {
                "field": "status_category",
                "message": "Status Category must be one of ERROR, WARNING, INFO.",
            }
        )

    set_delay = data.get("set_delay") or ""
    if not _DELAY_RE.match(set_delay):
        errors.append(
            {
                "field": "set_delay",
                "message": "Set Delay must be a number with a unit, e.g. '10ms' or '2min'.",
            }
        )

    reset_delay = data.get("reset_delay") or ""
    if not _DELAY_RE.match(reset_delay):
        errors.append(
            {
                "field": "reset_delay",
                "message": "Reset Delay must be a number with a unit, e.g. '10ms' or '2min'.",
            }
        )

    number_of_times_repeated = data.get("number_of_times_repeated")
    if number_of_times_repeated is not None and number_of_times_repeated < 1:
        errors.append(
            {
                "field": "number_of_times_repeated",
                "message": "Number of Times Repeated must be at least 1 when set.",
            }
        )

    repeated_over_the_course = data.get("repeated_over_the_course")
    if repeated_over_the_course and not _REPEAT_WINDOW_RE.match(repeated_over_the_course):
        errors.append(
            {
                "field": "repeated_over_the_course",
                "message": "Repeated Over the Course must be a number with a unit, e.g. '1d'.",
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

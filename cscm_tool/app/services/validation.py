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

from app import status_code_fields

_DELAY_RE = re.compile(r"^\*?\d+(\.\d+)?\s?(ms|s|min|MIN|h|d)$")
# FR-189: a delay that the program does not give as a time is never replaced by an assumed time. It
# stays the name of the variable or parameter that sets it, or the statement that the program has no
# timer; either way a person has to look the value up before the code is released.
_PARAMETER_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*(\[[A-Za-z0-9_]+\])?$"
)
NO_VALUE = "not in the program"


def _is_parameter(value: str) -> bool:
    """A controller identifier, not a plain word: it has a digit, an underscore, a dot or an index,
    or lower and upper case letters mixed after the first letter (StCd14000SetDelayGpTi), and at
    least six characters. A word such as 'soon', 'bad' or 'Fast' is a mistake, not a parameter."""
    if len(value) < 6 or not _PARAMETER_RE.match(value):
        return False
    if any(c.isdigit() or c in "_.[" for c in value):
        return True
    rest = value[1:]
    return any(c.islower() for c in rest) and any(c.isupper() for c in rest)


def is_delay(value: str) -> bool:
    return bool(_DELAY_RE.match(value)) or _is_parameter(value) or value == NO_VALUE


_REPEAT_WINDOW_RE = re.compile(r"^\d+(\.\d+)?\s?(s|min|h|d)$")
_STATUS_CATEGORIES = {"ERROR", "WARNING", "INFO"}
_IDENTIFIER_RE = re.compile(r"^StCd-\d{5}$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# I-14 limits (mirror the CHECK constraints in docs/artifacts/schema.sql)
MAX_REMEDY_CHARS = 4000
MAX_COMPONENT_CHARS = 200
MAX_RELATED_CHARS = 500
MAX_STANDARDS_CHARS = 1000


def split_identifier_list(value: str | None) -> list[str]:
    """`related_status_codes` is a comma/semicolon/space separated list of identifiers."""
    return [part for part in re.split(r"[,;\s]+", value or "") if part]


def _valid_iso_date(value: str) -> bool:
    from datetime import date

    if not _ISO_DATE_RE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


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
    if not is_delay(set_delay):
        errors.append(
            {
                "field": "set_delay",
                "message": "Set Delay must be a number with a unit, e.g. '10ms' or '2min', "
                "or the name of the parameter that sets it.",
            }
        )

    reset_delay = data.get("reset_delay") or ""
    if not is_delay(reset_delay):
        errors.append(
            {
                "field": "reset_delay",
                "message": "Reset Delay must be a number with a unit, e.g. '10ms' or '2min', "
                "or the name of the parameter that sets it.",
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

    for field, limit, label in (
        ("remedy_text", MAX_REMEDY_CHARS, "Remedy text"),
        ("affected_component", MAX_COMPONENT_CHARS, "Affected component"),
        ("standard_references", MAX_STANDARDS_CHARS, "Standard references"),
    ):
        value = data.get(field)
        if value and len(value) > limit:
            errors.append(
                {"field": field, "message": f"{label} must be at most {limit} characters."}
            )

    related = data.get("related_status_codes")
    if related:
        if len(related) > MAX_RELATED_CHARS:
            errors.append(
                {
                    "field": "related_status_codes",
                    "message": f"Related codes must be at most {MAX_RELATED_CHARS} characters.",
                }
            )
        bad = [i for i in split_identifier_list(related) if not _IDENTIFIER_RE.match(i)]
        if bad:
            errors.append(
                {
                    "field": "related_status_codes",
                    "message": "Related codes must be identifiers like StCd-01234, separated by "
                    f"commas (not: {', '.join(bad[:3])}).",
                }
            )

    for field, label in (
        ("planned_effective_date", "Planned effective date"),
        ("planned_deprecation_date", "Planned deprecation date"),
    ):
        value = data.get(field)
        if value and not _valid_iso_date(value):
            errors.append({"field": field, "message": f"{label} must be a date like 2027-03-31."})

    turbine_platforms = data.get("turbine_platforms")
    if turbine_platforms is not None and len(turbine_platforms) < 1:
        errors.append(
            {"field": "turbine_platforms", "message": "At least one Turbine Platform is required."}
        )

    errors.extend(status_code_fields.validate(data))

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

"""FR-022, FR-027 field rules from docs/06-data-dictionary.md, v3
(2026-09-17). Note: the old Safety-category/Alarm-Behaviour and Auto-reset/
delay cross-field rules are retired (docs/13-test-strategy.md) since the
real data model doesn't support them — status_category is now a 3-value
enum, alarm is a plain boolean, and reset/brake are numeric program
references, none of which carry the old semantics."""

from app.services.validation import validate_revision_fields

BASE_VALID_DATA = {
    "title": "Converter Grid Undervoltage Trip",
    "description": "Triggered when converter DC-link voltage falls below threshold.",
    "software_version": "4.12.0",
    "status_category": "ERROR",
    "available_group": 27,
    "alarm_flag": True,
    "set_delay": "10ms",
    "reset_delay": "2min",
    "turbine_platforms": ["3XM"],
}


def test_valid_data_has_no_errors():
    assert validate_revision_fields(BASE_VALID_DATA) == []


def test_title_too_short():
    errors = validate_revision_fields({**BASE_VALID_DATA, "title": ""})
    assert any(e["field"] == "title" for e in errors)


def test_description_too_short():
    errors = validate_revision_fields({**BASE_VALID_DATA, "description": "short"})
    assert any(e["field"] == "description" for e in errors)


def test_title_must_not_equal_description():
    errors = validate_revision_fields(
        {**BASE_VALID_DATA, "title": "Same Text Same Text", "description": "Same Text Same Text"}
    )
    assert any(e["field"] == "title" for e in errors)


def test_status_category_must_be_error_warning_or_info():
    errors = validate_revision_fields({**BASE_VALID_DATA, "status_category": "SAFETY"})
    assert any(e["field"] == "status_category" for e in errors)
    for value in ("ERROR", "WARNING", "INFO"):
        assert validate_revision_fields({**BASE_VALID_DATA, "status_category": value}) == []


def test_set_delay_rejects_missing_unit():
    errors = validate_revision_fields({**BASE_VALID_DATA, "set_delay": "10"})
    assert any(e["field"] == "set_delay" for e in errors)


def test_set_delay_accepts_leading_star_and_units():
    for value in ("10ms", "*500ms", "2min", "*0 ms", "1.5h", "3d"):
        assert validate_revision_fields({**BASE_VALID_DATA, "set_delay": value}) == []


def test_reset_delay_rejects_missing_unit():
    errors = validate_revision_fields({**BASE_VALID_DATA, "reset_delay": "abc"})
    assert any(e["field"] == "reset_delay" for e in errors)


def test_turbine_platforms_required_when_provided_empty():
    errors = validate_revision_fields({**BASE_VALID_DATA, "turbine_platforms": []})
    assert any(e["field"] == "turbine_platforms" for e in errors)


def test_number_of_times_repeated_must_be_at_least_one():
    errors = validate_revision_fields({**BASE_VALID_DATA, "number_of_times_repeated": 0})
    assert any(e["field"] == "number_of_times_repeated" for e in errors)
    assert validate_revision_fields({**BASE_VALID_DATA, "number_of_times_repeated": 10}) == []


def test_repeated_over_the_course_format():
    errors = validate_revision_fields({**BASE_VALID_DATA, "repeated_over_the_course": "1day"})
    assert any(e["field"] == "repeated_over_the_course" for e in errors)
    assert validate_revision_fields({**BASE_VALID_DATA, "repeated_over_the_course": "1d"}) == []

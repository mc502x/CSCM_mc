"""FR-022, FR-027 cross-field rules from docs/06-data-dictionary.md."""

from app.services.validation import validate_revision_fields

BASE_VALID_DATA = {
    "title": "Converter Grid Undervoltage Trip",
    "description": "Triggered when converter DC-link voltage falls below threshold.",
    "software_version": "4.12.0",
    "status_category": "FAULT",
    "reset_program": "MANUAL",
    "alarm_behaviour": "SELF_CLEARING",
    "brake_program": "BP-NONE",
    "delay_before_alarm_seconds": 0,
    "delay_before_reset_seconds": 0,
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


def test_software_version_format():
    errors = validate_revision_fields({**BASE_VALID_DATA, "software_version": "not-a-version"})
    assert any(e["field"] == "software_version" for e in errors)
    assert validate_revision_fields({**BASE_VALID_DATA, "software_version": "4.12"}) == []


def test_escalating_alarm_requires_delay():
    errors = validate_revision_fields(
        {**BASE_VALID_DATA, "alarm_behaviour": "ESCALATING", "delay_before_alarm_seconds": 0}
    )
    assert any(e["field"] == "delay_before_alarm_seconds" for e in errors)

    ok = validate_revision_fields(
        {**BASE_VALID_DATA, "alarm_behaviour": "ESCALATING", "delay_before_alarm_seconds": 5}
    )
    assert ok == []


def test_auto_reset_requires_delay():
    errors = validate_revision_fields(
        {**BASE_VALID_DATA, "reset_program": "AUTO", "delay_before_reset_seconds": 0}
    )
    assert any(e["field"] == "delay_before_reset_seconds" for e in errors)


def test_safety_category_requires_latching_or_escalating_alarm():
    errors = validate_revision_fields(
        {**BASE_VALID_DATA, "status_category": "SAFETY", "alarm_behaviour": "SILENT"}
    )
    assert any(e["field"] == "alarm_behaviour" for e in errors)

    ok = validate_revision_fields(
        {**BASE_VALID_DATA, "status_category": "SAFETY", "alarm_behaviour": "LATCHING"}
    )
    assert ok == []


def test_emergency_brake_requires_fault_or_safety_category():
    errors = validate_revision_fields(
        {**BASE_VALID_DATA, "brake_program": "BP-4", "status_category": "OPERATIONAL"}
    )
    assert any(e["field"] == "brake_program" for e in errors)

    ok = validate_revision_fields(
        {**BASE_VALID_DATA, "brake_program": "BP-4", "status_category": "FAULT"}
    )
    assert ok == []


def test_turbine_platforms_required_when_provided_empty():
    errors = validate_revision_fields({**BASE_VALID_DATA, "turbine_platforms": []})
    assert any(e["field"] == "turbine_platforms" for e in errors)

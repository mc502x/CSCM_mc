"""What the .st import takes from the mapping and how it checks the program against the row (FR-192,
FR-193): title, type, cause and directive, the value of a parameter delay, the legacy number of the
header, the approval state of the row, and the glossary check of the title.

TC-077. Requirements: FR-192, FR-193, FR-189, BR-027.
"""

import io
from pathlib import Path

import pytest

from app.extensions import db
from app.models.mapping import StatusCodeMapping
from app.models.status_code import StatusCode
from tests.helpers import login_as, make_cast

pytestmark = pytest.mark.usefixtures("st_mapping")
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "st"


@pytest.fixture()
def engineer(client, make_user):
    user = make_cast(make_user)["engineer"]
    login_as(client, user)
    return user


def _preview(client, names):
    data = {"files": [(io.BytesIO((FIXTURES / n).read_bytes()), n) for n in names]}
    response = client.post(
        "/api/v1/imports/st/preview", data=data, content_type="multipart/form-data"
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def _edit(app, new_number, **fields):
    with app.app_context():
        row = db.session.query(StatusCodeMapping).filter_by(new_number=new_number).one()
        for name, value in fields.items():
            setattr(row, name, value)
        db.session.commit()


def _import_one(app, client, name):
    preview = _preview(client, [name])
    assert client.post("/api/v1/imports/st", json={"token": preview["token"]}).status_code == 202
    with app.app_context():
        return db.session.query(StatusCode).one().revisions[0]


def test_cause_and_directive_become_the_remedy_text(app, client, engineer):
    _edit(app, 1000, cause="The converter lost its enable signal.", directive="Check the cabling.")
    revision = _import_one(app, client, "StCd_1000.st")
    assert revision.remedy_text == (
        "Cause: The converter lost its enable signal.\nDirective: Check the cabling."
    )


def test_a_row_without_cause_and_directive_leaves_the_remedy_text_empty(app, client, engineer):
    assert _import_one(app, client, "StCd_1000.st").remedy_text is None


def test_the_mapping_gives_the_value_of_a_delay_the_program_sets_with_a_parameter(
    app, client, engineer
):
    _edit(app, 12501, parameter_set_delay="*5s")
    preview = _preview(client, ["StCd_14000.st"])
    warnings = " ".join(preview["items"][0]["warnings"])
    assert "StCd14000SetDelayGpTi" in warnings and "*5s is the value the mapping gives" in warnings
    revision = _import_one(app, client, "StCd_14000.st")
    assert revision.set_delay == "*5s" and revision.reset_delay == "200ms"
    assert "set delay = *5s from the mapping (the program sets it with the parameter" in (
        revision.description
    )


def test_a_time_in_the_program_wins_over_the_mapping(app, client, engineer):
    _edit(app, 1000, parameter_set_delay="*9s")
    assert _import_one(app, client, "StCd_1000.st").set_delay == "10ms"


def test_the_legacy_number_of_the_header_must_be_the_one_of_the_row(app, client, engineer):
    _edit(app, 1000, legacy_number=3001)
    item = _preview(client, ["StCd_1000.st"])["items"][0]
    assert item["state"] == "blocked"
    assert "header gives legacy number 3000, the mapping gives 3001" in item["issues"][0]["message"]


def test_a_row_that_is_not_approved_yet_is_used_with_a_warning(app, client, engineer):
    _edit(app, 1000, status="PROPOSED")
    item = _preview(client, ["StCd_1000.st"])["items"][0]
    assert item["state"] == "ready"
    assert any("proposed" in w and "not approved yet" in w for w in item["warnings"])
    _edit(app, 1000, status="APPROVED")
    assert not any(
        "not approved" in w for w in _preview(client, ["StCd_1000.st"])["items"][0]["warnings"]
    )


def test_a_rejected_row_is_as_good_as_none(app, client, engineer):
    _edit(app, 1000, status="REJECTED")
    item = _preview(client, ["StCd_1000.st"])["items"][0]
    assert item["state"] == "blocked" and "is not in the mapping" in item["issues"][0]["message"]


def test_a_title_that_does_not_say_what_the_name_says_is_flagged(app, client, engineer):
    _edit(app, 1000, description="Inverter ready")  # the program name is "Umrichter nicht bereit"
    item = _preview(client, ["StCd_1000.st"])["items"][0]
    messages = " ".join(item["warnings"])
    assert "Title and program name" in messages
    assert "'umrichter'" in messages and "'converter'" in messages and "'not ready'" in messages
    assert item["state"] == "ready"  # a check for a person, never a block


def test_a_hub_row_for_a_main_program_is_not_taken(app, client, engineer):
    # StCd_1000 is a Main program; a Hub row with the same new number is not its row
    _edit(app, 1000, family="HC")
    item = _preview(client, ["StCd_1000.st"])["items"][0]
    assert item["state"] == "blocked"
    assert "Hub Controller row in the mapping" in item["issues"][0]["message"]


def test_a_program_already_in_the_catalogue_keeps_its_title_when_the_row_is_gone(
    app, client, engineer
):
    _import_one(app, client, "StCd_1000.st")
    with app.app_context():
        db.session.query(StatusCodeMapping).filter_by(new_number=1000).delete()
        db.session.commit()
    item = _preview(client, ["StCd_1000.st"])["items"][0]
    assert item["state"] == "exists", item.get("changes")
    assert any("is not in the mapping; its title" in w for w in item["warnings"])


def test_the_glossary_is_a_check_not_a_translation():
    from app.importers import glossary

    assert glossary.check("Umrichter nicht bereit", "Converter not ready") == []
    assert glossary.check("Hydrauliköl Temperatur zu hoch", "Hydraulic oil temp. too high") == []
    assert glossary.check("", "anything") == [] and glossary.check("Umrichter", "") == []
    assert glossary.terms()

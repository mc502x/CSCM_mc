"""The import assumes no value (FR-189): a value is read from the program, chosen by the user, or - when
the program gives a variable instead of a time - the name of that variable; what the program does not
give is listed in the comment of the Draft; the type, the title and the access levels come from the
mapping and nowhere else (FR-192), and a program the mapping does not know is not imported.

TC-053. Requirements: FR-189, FR-190, FR-192, FR-048o, BR-023.
"""

import io
from pathlib import Path

import pytest

from app.extensions import db
from app.models.status_code import StatusCode
from tests.helpers import login_as, make_cast, valid_payload

pytestmark = pytest.mark.usefixtures("st_mapping")
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "st"


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


def _preview(client, names, **fields):
    data = {"files": [(io.BytesIO((FIXTURES / n).read_bytes()), n) for n in names], **fields}
    response = client.post(
        "/api/v1/imports/st/preview", data=data, content_type="multipart/form-data"
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def _import(app, client, name, **fields):
    preview = _preview(client, [name], default_category="ERROR", **fields)
    done = client.post("/api/v1/imports/st", json={"token": preview["token"]})
    assert done.status_code == 202, done.get_json()
    with app.app_context():
        revision = db.session.query(StatusCode).one().revisions[0]
        return (
            revision.set_delay,
            revision.reset_delay,
            revision.description,
            revision.status_category,
        )


def test_a_delay_that_is_a_variable_stays_the_name_of_the_variable(app, client, cast):
    login_as(client, cast["engineer"])
    set_delay, reset_delay, comment, _category = _import(app, client, "StCd_14000.st")
    assert set_delay == "StCd14000SetDelayGpTi"  # the program names a parameter, not a time
    assert reset_delay == "200ms"  # the program gives a time
    assert "0ms" not in set_delay
    assert "Not resolved by the import:" in comment
    assert "set delay = StCd14000SetDelayGpTi (a variable or parameter" in comment
    assert "reset delay =" not in comment


def test_a_delay_the_program_does_not_have_says_so(app, client, cast):
    login_as(client, cast["engineer"])
    set_delay, reset_delay, comment, _category = _import(app, client, "StCd_14005.st")
    assert (set_delay, reset_delay) == ("not in the program", "not in the program")
    assert "set delay: the program has no timer" in comment
    assert "reset delay: the program has no timer" in comment


def test_a_program_that_gives_everything_lists_only_what_no_program_carries(app, client, cast):
    login_as(client, cast["engineer"])
    set_delay, reset_delay, comment, _category = _import(app, client, "StCd_1000.st")
    assert (set_delay, reset_delay) == ("10ms", "2min")
    assert "variable" not in comment and "no timer" not in comment
    assert "up/down counter" not in comment  # no program carries it: the mapping does
    assert "entered as No" not in comment  # the alarm and the snapshot are in the file
    assert "Name in the program: Umrichter nicht bereit" in comment


def test_the_preview_warns_with_the_name_of_the_parameter(client, cast):
    login_as(client, cast["engineer"])
    preview = _preview(client, ["StCd_14000.st"], default_category="ERROR")
    warnings = " ".join(preview["items"][0]["warnings"])
    assert "StCd14000SetDelayGpTi" in warnings and "look the value up" in warnings
    assert "0ms is entered" not in warnings


def test_a_program_the_mapping_does_not_know_is_blocked_and_never_imported(app, client, cast):
    from app.models.mapping import StatusCodeMapping

    with app.app_context():
        db.session.query(StatusCodeMapping).filter_by(new_number=1001).delete()
        db.session.commit()
    login_as(client, cast["engineer"])
    preview = _preview(client, ["StCd_1000.st", "StCd_1001.st"])
    states = {i["program_number"]: i["state"] for i in preview["items"]}
    assert states == {1000: "ready", 1001: "blocked"}
    blocked = preview["items"][1]
    assert "StCd-01001" in blocked["issues"][0]["message"]
    assert "is not in the mapping" in blocked["issues"][0]["message"]
    refused = client.post(
        "/api/v1/imports/st", json={"token": preview["token"], "selected": [blocked["key"]]}
    )
    assert refused.status_code == 422
    done = client.post("/api/v1/imports/st", json={"token": preview["token"]})
    assert done.status_code == 202 and done.get_json()["created_count"] == 1
    with app.app_context():
        assert db.session.query(StatusCode).count() == 1


def test_a_delay_may_be_the_name_of_a_parameter_but_not_a_malformed_time(client, cast, wcnv_ids):
    login_as(client, cast["engineer"])
    ok = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, set_delay="StCdX.SetDelayGpTi")
    )
    assert ok.status_code == 201 and ok.get_json()["set_delay"] == "StCdX.SetDelayGpTi"
    for bad in ("10 sec", "", "10", "a b"):
        refused = client.post("/api/v1/status-codes", json=valid_payload(*wcnv_ids, set_delay=bad))
        assert refused.status_code == 422, bad
    assert "the name of the parameter" in refused.get_data(as_text=True)


def _access(app, client, name):
    """(the named levels of the Draft, its comment) after importing one program."""
    preview = _preview(client, [name], default_category="ERROR")
    assert client.post("/api/v1/imports/st", json={"token": preview["token"]}).status_code == 202
    with app.app_context():
        revision = db.session.query(StatusCode).one().revisions[0]
        levels = {
            field: (getattr(revision, field).label if getattr(revision, field) else None)
            for field in (
                "development_access",
                "sales_access",
                "tcc_access",
                "service_access",
                "turbine_operator_package_access",
                "grid_operator_access",
                "service_partner_access",
                "customer_access",
            )
        }
        numbers = {slot: (g.read_level, g.write_level) for slot, g in _slots(revision)}
        return levels, revision.description, numbers


def _slots(revision):
    from app.status_code_fields import user_groups

    return [
        (slot, type("G", (), {"read_level": v["read"], "write_level": v["write"]}))
        for slot, v in user_groups(revision).items()
    ]


def _row(new_number):
    from app.models.mapping import StatusCodeMapping

    return db.session.query(StatusCodeMapping).filter_by(new_number=new_number).one()


def test_the_named_access_levels_come_from_the_mapping(app, client, cast):
    login_as(client, cast["engineer"])
    levels, comment, numbers = _access(app, client, "StCd_14000.st")
    assert levels == {
        "development_access": "See only",
        "sales_access": "See only",
        "tcc_access": "See only",
        "service_access": "See only",
        "turbine_operator_package_access": "Covert",
        "grid_operator_access": "Covert",
        "service_partner_access": "Covert",
        "customer_access": "See only",
    }
    assert "Mapping and program differ" not in comment
    assert "access levels not in the mapping" not in comment
    assert numbers[1] == (1, 50) and numbers[5] == (50, 50)  # the numbers themselves are kept


def test_a_level_the_mapping_leaves_empty_stays_empty_and_is_listed(app, client, cast):
    with app.app_context():
        _row(1000).sales_access = None
        _row(1000).tcc_access = None
        db.session.commit()
    login_as(client, cast["engineer"])
    levels, comment, numbers = _access(app, client, "StCd_1000.st")
    assert levels["sales_access"] is None and levels["tcc_access"] is None
    assert levels["development_access"] == "Department"
    assert "access levels not in the mapping: Sales, TCC" in comment
    assert numbers[2] == (1, 10)  # the numbers of the program are kept all the same


def test_a_level_whose_numbers_differ_from_the_program_is_named_and_warned_about(app, client, cast):
    with app.app_context():
        _row(1000).development_access = "See only"  # 1 / 50 - the program gives 1 / 5
        db.session.commit()
    login_as(client, cast["engineer"])
    preview = _preview(client, ["StCd_1000.st"])
    warnings = " ".join(preview["items"][0]["warnings"])
    assert "Development access: the mapping says See only (read 1 / write 50)" in warnings
    assert "the program has read 1 / write 5" in warnings
    done = client.post("/api/v1/imports/st", json={"token": preview["token"]})
    assert done.status_code == 202
    with app.app_context():
        revision = db.session.query(StatusCode).one().revisions[0]
        assert revision.development_access.label == "See only"  # the mapping names the level
        assert "Mapping and program differ: Development access" in revision.description
        assert dict(_slots(revision))[1].write_level == 5  # the program's own number


def test_a_level_that_is_no_longer_active_is_not_guessed(app, client, cast):
    with app.app_context():
        _row(1000).customer_access = "A level that was removed"
        db.session.commit()
    login_as(client, cast["engineer"])
    levels, comment, _numbers = _access(app, client, "StCd_1000.st")
    assert levels["customer_access"] is None
    assert "Customer access: the mapping names 'A level that was removed'" in comment

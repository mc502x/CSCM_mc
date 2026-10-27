"""The import assumes no value (FR-189): a value is read from the program, chosen by the user, or - when
the program gives a variable instead of a time - the name of that variable; what the program does not
give is listed in the comment of the Draft; no status category is ever assumed.

TC-053. Requirements: FR-189, FR-048o, BR-023.
"""

import io
from pathlib import Path

import pytest

from app.extensions import db
from app.models.status_code import StatusCode
from tests.helpers import login_as, make_cast, valid_payload

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
    assert "up/down counter" in comment  # no program carries it: entered as No and said so
    assert "alarm" not in comment.split("entered as No:")[1].split(";")[0]  # the file gives it


def test_the_preview_warns_with_the_name_of_the_parameter(client, cast):
    login_as(client, cast["engineer"])
    preview = _preview(client, ["StCd_14000.st"], default_category="ERROR")
    warnings = " ".join(preview["items"][0]["warnings"])
    assert "StCd14000SetDelayGpTi" in warnings and "look the value up" in warnings
    assert "0ms is entered" not in warnings


def test_no_category_is_assumed(app, client, cast):
    login_as(client, cast["engineer"])
    preview = _preview(client, ["StCd_1000.st", "StCd_1001.st"])  # nothing chosen
    assert preview["options"]["default_category"] is None
    assert [i["category"] for i in preview["items"]] == [None, None]
    assert all("No status category is chosen" in " ".join(i["warnings"]) for i in preview["items"])
    refused = client.post("/api/v1/imports/st", json={"token": preview["token"]})
    assert refused.status_code == 422 and "none is assumed" in refused.get_json()["message"]
    with app.app_context():
        assert db.session.query(StatusCode).count() == 0  # nothing was created
    keys = [i["key"] for i in preview["items"]]
    chosen = client.post(
        "/api/v1/imports/st",
        json={"token": preview["token"], "categories": {keys[0]: "INFO", keys[1]: "WARNING"}},
    )
    assert chosen.status_code == 202, chosen.get_json()
    with app.app_context():
        found = {
            c.revisions[0].title: c.revisions[0].status_category
            for c in db.session.query(StatusCode).all()
        }
        assert sorted(found.values()) == ["INFO", "WARNING"]


def test_the_preview_page_asks_for_a_category_instead_of_assuming_one(client, cast):
    login_as(client, cast["engineer"])
    form = client.get("/imports/st").get_data(as_text=True)
    assert '<option value="" selected>(choose)</option>' in form
    assert 'id="default_category"' in form and "none is assumed" in form
    page = client.post(
        "/imports/st",
        data={"files": [(io.BytesIO((FIXTURES / "StCd_1000.st").read_bytes()), "StCd_1000.st")]},
        content_type="multipart/form-data",
    ).get_data(as_text=True)
    assert '<option value="" selected>(choose)</option>' in page  # the row has none chosen
    assert "checked" not in page.split('class="st-row-check"')[1].split(">")[0]  # not ticked


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


def test_the_user_group_numbers_of_the_file_become_the_named_access_levels(app, client, cast):
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
    assert "Access levels, proposed from the user-group numbers of the program:" in comment
    assert "Development = See only (read 1, write 50)" in comment
    assert "Turbine Operator Package = Covert (read 50, write 50)" in comment
    assert "fits no named level" not in comment
    assert numbers[1] == (1, 50) and numbers[5] == (50, 50)  # the numbers themselves are kept


def test_a_level_that_no_single_named_level_carries_stays_empty_and_is_listed(app, client, cast):
    login_as(client, cast["engineer"])
    levels, comment, numbers = _access(app, client, "StCd_1000.st")
    assert levels["turbine_operator_package_access"] == "Preventive Maintenance"  # 1 / 10
    assert levels["service_partner_access"] == "Ext. Service Provider"  # 1 / 15
    assert levels["customer_access"] == "See only" and levels["grid_operator_access"] == "Covert"
    # Development 1/5, Sales 1/10, TCC 1/10 and Service 1/20 are carried by no named level:
    for audience in ("development_access", "sales_access", "tcc_access", "service_access"):
        assert levels[audience] is None
    assert "Development access: read 1 / write 5 fits no named level" in comment
    assert "Service access: read 1 / write 20 fits no named level" in comment
    assert numbers[1] == (1, 5) and numbers[4] == (1, 20)  # the numbers are kept all the same


def test_a_pair_of_numbers_that_fits_two_named_levels_is_not_guessed(app):
    from app.importers import stcd
    from app.services import st_import_service as service

    code = stcd.StatusCode(identifier="StCd-01000", number=1000, controller="MC")
    code.user_groups = {2: {"read": 1, "write": 10}}
    audiences = {"sales_access": [(1, "Sales", 1, 10), (2, "Dealer", 1, 10)]}
    translated: list[str] = []
    unresolved: list[str] = []
    found = service._translate_access(code, audiences, translated, unresolved)
    assert found == {} and translated == []
    assert any(
        "Sales access: read 1 / write 10 fits more than one level (Sales, Dealer)" in u
        for u in unresolved
    )
    assert any("access levels not in the program:" in u for u in unresolved)  # the other seven

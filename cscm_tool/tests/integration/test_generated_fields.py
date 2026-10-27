"""The fields of the generated controller programs (schema v4.1, docs/06-data-dictionary.md sections
2c.1, 2d.1 and 2f; docs/03-srs.md FR-168): the further subsystem programs, the operating-mode mask, the
task call frequency, the flags and the numeric user-group levels are stored, copied, shown, exported
and read from the program files - and a field that does not apply to the controller of a code is
refused.

TC-063. Requirements: FR-168, FR-048o, FR-025, FR-032.
"""

import io
import json
from pathlib import Path

import pytest

from app import status_code_fields as fields
from app.extensions import db
from app.importers import stcd
from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup
from app.models.status_code import StatusCode, StatusCodeRevision
from app.services import st_import_service
from tests.helpers import decide, domain_sign, login_as, make_cast, submit, valid_payload

pytestmark = pytest.mark.usefixtures("st_mapping")
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "st"


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


def _read(name):
    return (FIXTURES / name).read_bytes()


def _import(client, name):
    data = {"files": [(io.BytesIO(_read(name)), name)], "default_category": "ERROR"}
    preview = client.post(
        "/api/v1/imports/st/preview", data=data, content_type="multipart/form-data"
    ).get_json()
    response = client.post("/api/v1/imports/st", json={"token": preview["token"]})
    assert response.status_code == 202, response.get_json()


def _parsed(name):
    programs, _ = stcd.parse_bytes(_read(name), name)
    return programs[0]


def _revision(app):
    with app.app_context():
        return db.session.query(StatusCodeRevision).order_by(StatusCodeRevision.id).first()


def _hub_ids(app):
    with app.app_context():
        group = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(LookupFunctionalSystemGroup.controller_type == "HUB")
            .first()
        )
        subgroup = (
            db.session.query(LookupFunctionalSubgroup)
            .filter(LookupFunctionalSubgroup.functional_system_group_id == group.id)
            .first()
        )
        return group.id, subgroup.id


# -------------------------------------------------------------------------- the program import
@pytest.mark.parametrize("name", ["StCd_1000.st", "StCd_1001.st", "StCd_1002.st"])
def test_a_main_program_import_keeps_every_field_of_the_program(app, client, cast, name):
    login_as(client, cast["engineer"])
    _import(client, name)
    parsed = _parsed(name)
    with app.app_context():
        revision = db.session.query(StatusCodeRevision).one()
        assert revision.task_call_frequency == parsed.task_call_frequency
        assert fields.mask_to_binary(revision.operating_mode_mask, "MAIN") == parsed.op_mode_bits
        assert bool(revision.availability_calc) is bool(parsed.availability_calc)
        assert bool(revision.zero_load_operation) is bool(parsed.zero_load_operation)
        # ZeroLoadPrg_ArBo and ZeroLoadOperation_ArBo are two different attributes
        assert bool(revision.loadless_spinning_permitted) is bool(
            parsed.other.get("ZeroLoadPrg_ArBo")
        )
        for source, target in st_import_service._EXTRA_PROGRAM_FIELDS.items():
            assert getattr(revision, target) == int(parsed.programs.get(source) or 0), target
        assert fields.user_groups(revision) == {
            slot: {"read": v["read"], "write": v["write"]} for slot, v in parsed.user_groups.items()
        }
        assert 13 not in fields.user_groups(revision)  # slot 13 is never written


def test_the_two_zero_load_attributes_are_not_mixed_up(app, client, cast):
    login_as(client, cast["engineer"])
    _import(
        client, "StCd_1002.st"
    )  # ZeroLoadOperation TRUE, ZeroLoadPrg FALSE (docs/06 section 2f)
    revision = _revision(app)
    assert revision.zero_load_operation == 1 and revision.loadless_spinning_permitted == 0


def test_a_hub_program_import_keeps_its_hub_fields_and_nothing_of_the_main_ones(app, client, cast):
    login_as(client, cast["engineer"])
    _import(client, "StCd_14000.st")
    parsed = _parsed("StCd_14000.st")
    with app.app_context():
        revision = db.session.query(StatusCodeRevision).one()
        assert revision.rotor_brake_program == 20  # rotor overspeed: the export loses this value
        assert fields.mask_to_binary(revision.operating_mode_mask, "HUB") == parsed.op_mode_bits
        assert len(parsed.op_mode_bits) == 6
        assert revision.availability_calc == 0
        assert all(
            getattr(revision, f) is None for f in fields.FLAG_FIELDS if f != "availability_calc"
        )
        assert all(getattr(revision, f) == 0 for f, _ in fields.MAIN_PROGRAMS)
        assert revision.zero_load_operation is None  # Main only


# -------------------------------------------------------------------------- the controller rule
def test_a_field_of_the_other_controller_is_refused_and_the_rest_is_stored(
    app, client, cast, wcnv_ids
):
    login_as(client, cast["engineer"])
    hub = _hub_ids(app)
    main_bad = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, pitch_error_program=5)
    )
    assert main_bad.status_code == 422
    assert "pitch_error_program" in json.dumps(main_bad.get_json())
    hub_bad = client.post(
        "/api/v1/status-codes", json=valid_payload(*hub, hydraulic_pump_program=3)
    )
    assert hub_bad.status_code == 422 and "hydraulic_pump_program" in json.dumps(hub_bad.get_json())
    hub_flag_on_main = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, vane_position_flag=True)
    )
    assert hub_flag_on_main.status_code == 422

    ok = client.post(
        "/api/v1/status-codes",
        json=valid_payload(
            *wcnv_ids,
            hydraulic_pump_program=7,
            zero_load_operation=True,
            availability_calc=False,
            operating_mode_mask="11111110000100000000",
            task_call_frequency=100,
            user_groups=[{"slot": 1, "read": 1, "write": 5}, {"slot": 8, "read": 50, "write": 50}],
        ),
    )
    assert ok.status_code == 201, ok.get_json()
    body = ok.get_json()
    assert body["hydraulic_pump_program"] == 7 and body["zero_load_operation"] is True
    assert body["availability_calc"] is False and body["vane_position_flag"] is None
    assert (
        body["operating_mode_bits"] == "11111110000100000000" and body["controller_type"] == "MAIN"
    )
    assert body["task_call_frequency"] == 100
    assert body["user_groups"] == [
        {"slot": 1, "read": 1, "write": 5},
        {"slot": 8, "read": 50, "write": 50},
    ]


@pytest.mark.parametrize(
    "extra",
    [
        {"operating_mode_mask": "12"},
        {"operating_mode_mask": 1 << 21},
        {"task_call_frequency": 0},
        {"hydraulic_pump_program": 70000},
        {"zero_load_operation": "maybe"},
        {"user_groups": [{"slot": 16, "read": 1, "write": 1}]},
        {"user_groups": [{"slot": 1, "read": 256, "write": 1}]},
    ],
)
def test_values_out_of_range_are_refused(client, cast, wcnv_ids, extra):
    login_as(client, cast["engineer"])
    response = client.post("/api/v1/status-codes", json=valid_payload(*wcnv_ids, **extra))
    assert response.status_code == 422, response.get_json()


# -------------------------------------------------------------------------- copy, edit, show
def _approved_main_code(app, client, cast, wcnv_ids, **extra):
    login_as(client, cast["engineer"])
    created = client.post("/api/v1/status-codes", json=valid_payload(*wcnv_ids, **extra))
    assert created.status_code == 201, created.get_json()
    from tests.helpers import cr_id_for_revision

    cr_id = cr_id_for_revision(app, created.get_json()["id"])
    domain_sign(client, cast, cr_id)
    assert submit(client, cast, cr_id).status_code == 200
    assert decide(client, cast["reviewer"], cr_id, "reviewer-signoff").status_code == 200
    assert decide(client, cast["admin"], cr_id, "admin-signoff").status_code == 200
    final = decide(client, cast["chief_engineer"], cr_id, "chief-engineer-decide")
    assert final.get_json()["state"] == "APPROVED"
    return created.get_json()["status_code_id"]


def test_a_new_revision_carries_over_what_the_caller_does_not_send_and_the_diff_shows_changes(
    app, client, cast, wcnv_ids
):
    code_id = _approved_main_code(
        app,
        client,
        cast,
        wcnv_ids,
        tower_fan_program=10,
        task_call_frequency=10,
        user_groups=[{"slot": 3, "read": 1, "write": 10}],
    )
    login_as(client, cast["engineer"])
    # a client that does not know the new fields opens a revision: nothing is lost
    revision = client.post(
        f"/api/v1/status-codes/{code_id}/revisions",
        json=valid_payload(*wcnv_ids, title="Converter Grid Undervoltage Trip (revised)"),
    )
    assert revision.status_code == 201, revision.get_json()
    body = revision.get_json()
    assert body["tower_fan_program"] == 10 and body["task_call_frequency"] == 10
    assert body["user_groups"] == [{"slot": 3, "read": 1, "write": 10}]

    # a PATCH of the Draft that leaves the fields out keeps them; one that sends them changes them
    patched = client.patch(
        f"/api/v1/revisions/{body['id']}",
        json=valid_payload(*wcnv_ids, title="Changed again here"),
    )
    assert patched.status_code == 200, patched.get_json()
    assert patched.get_json()["tower_fan_program"] == 10
    changed = client.patch(
        f"/api/v1/revisions/{body['id']}",
        json=valid_payload(
            *wcnv_ids,
            tower_fan_program=20,
            user_groups=[{"slot": 3, "read": 1, "write": 20}],
        ),
    )
    assert changed.status_code == 200, changed.get_json()
    assert changed.get_json()["tower_fan_program"] == 20
    diff = client.get(f"/api/v1/status-codes/{code_id}/revisions/1/diff/2").get_json()
    names = {c["field"]: (c["old_value"], c["new_value"]) for c in diff["field_changes"]}
    assert names["tower_fan_program"] == (10, 20)
    assert names["user_group_levels"] == ("3:1/10", "3:1/20")


def test_the_form_stores_the_fields_and_the_pages_show_them(app, client, cast, wcnv_ids):
    login_as(client, cast["engineer"])
    form = {
        "functional_system_group": str(wcnv_ids[0]),
        "functional_subgroup": str(wcnv_ids[1]),
        "turbine_platforms": "3XM",
        "title": "Converter fan fault",
        "description": "The converter fan reports a fault for more than ten seconds.",
        "status_category": "ERROR",
        "available_group": "27",
        "set_delay": "10ms",
        "reset_delay": "2min",
        "hydraulic_pump_program": "7",
        "operating_mode_mask": "11111110000100000000",
        "task_call_frequency": "10",
        "availability_calc": "1",
        "zero_load_operation": "0",
        "ug_read_4": "1",
        "ug_write_4": "15",
    }
    response = client.post("/status-codes/new", data=form, follow_redirects=True)
    page = response.get_data(as_text=True)
    revision = _revision(app)
    assert revision is not None, page[:500]
    with app.app_context():
        revision = db.session.query(StatusCodeRevision).one()
        assert revision.hydraulic_pump_program == 7 and revision.availability_calc == 1
        assert revision.zero_load_operation == 0 and revision.vane_position_flag is None
        assert fields.user_groups(revision) == {4: {"read": 1, "write": 15}}
        code_id = revision.status_code_id
    detail = client.get(f"/status-codes/{code_id}").get_data(as_text=True)
    assert "Further Program References" in detail and "Hydraulic Pump Program" in detail
    assert "11111110000100000000" in detail and "User-Group Levels" in detail
    assert "Pitch Error Program" not in detail  # a Main Controller code shows Main fields only
    edit = client.get(f"/status-codes/{code_id}/edit").get_data(as_text=True)
    assert 'name="ug_read_4"' in edit and 'value="15"' in edit and "Operation Parameters" in edit


def test_a_rejected_form_keeps_what_was_typed(client, cast, wcnv_ids):
    login_as(client, cast["engineer"])
    form = {
        "functional_system_group": str(wcnv_ids[0]),
        "functional_subgroup": str(wcnv_ids[1]),
        "turbine_platforms": "3XM",
        "title": "Converter fan fault",
        "description": "The converter fan reports a fault for more than ten seconds.",
        "status_category": "ERROR",
        "available_group": "27",
        "set_delay": "10ms",
        "reset_delay": "2min",
        "pitch_error_program": "5",  # Hub only
        "operating_mode_mask": "10101",
        "ug_read_2": "1",
        "ug_write_2": "10",
    }
    page = client.post("/status-codes/new", data=form).get_data(as_text=True)
    assert "does not apply to the Main Controller" in page
    assert 'value="10101"' in page and 'name="ug_write_2"' in page


def test_the_levels_and_programs_are_internal_and_never_leave_in_an_audience_export(
    app, client, cast, wcnv_ids
):
    from app.services.audience_service import INTERNAL_COLUMNS

    for field in (
        *fields.PROGRAM_FIELDS,
        *fields.FLAG_FIELDS,
        "operating_mode_mask",
        "user_group_levels",
    ):
        assert field in INTERNAL_COLUMNS, field
    _approved_main_code(app, client, cast, wcnv_ids, tower_fan_program=10)
    login_as(client, cast["admin"])
    export = client.get("/api/v1/exports/working-set?format=json")
    assert export.status_code == 200
    rows = json.loads(export.get_data(as_text=True))
    rows = rows["items"] if isinstance(rows, dict) else rows
    assert rows[0]["tower_fan_program"] == 10 and "user_group_levels" in rows[0]


def test_withdrawing_and_deleting_a_code_removes_its_levels(app, client, cast, wcnv_ids):
    login_as(client, cast["engineer"])
    created = client.post(
        "/api/v1/status-codes",
        json=valid_payload(*wcnv_ids, user_groups=[{"slot": 1, "read": 1, "write": 5}]),
    )
    assert created.status_code == 201
    cr_id = (
        client.get("/api/v1/change-requests?mine=true").get_json()["items"][0]["id"]
        if False
        else None
    )
    from tests.helpers import cr_id_for_revision

    cr_id = cr_id_for_revision(app, created.get_json()["id"])
    withdrawn = client.post("/api/v1/change-requests/withdraw", json={"cr_ids": [cr_id]})
    assert withdrawn.status_code == 200
    with app.app_context():
        from sqlalchemy import text

        assert (
            db.session.execute(
                text("SELECT COUNT(*) FROM status_code_revision_user_group")
            ).scalar()
            == 0
        )
        assert db.session.query(StatusCode).count() == 1  # the empty shell stays until deleted


# -------------------------------------------------------------------------- defaults and the CSV import
def test_a_named_audience_value_brings_its_default_levels_and_explicit_levels_win(
    app, client, cast, wcnv_ids
):
    from sqlalchemy import text

    with app.app_context():
        covert = db.session.execute(
            text("SELECT id FROM lookup_top_access WHERE code = 'COVERT'")
        ).scalar()
    login_as(client, cast["engineer"])
    created = client.post(
        "/api/v1/status-codes",
        json=valid_payload(*wcnv_ids, turbine_operator_package_access=covert),
    )
    assert created.status_code == 201, created.get_json()
    # slot 5 is the Turbine Operator Package; Covert is read 50, write 50 on every code seen
    assert created.get_json()["user_groups"] == [{"slot": 5, "read": 50, "write": 50}]

    explicit = client.post(
        "/api/v1/status-codes",
        json=valid_payload(
            *wcnv_ids,
            title="Another converter fault",
            turbine_operator_package_access=covert,
            user_groups=[{"slot": 5, "read": 1, "write": 10}],
        ),
    )
    assert explicit.get_json()["user_groups"] == [{"slot": 5, "read": 1, "write": 10}]


def _csv_upload(client, row, dry_run=False):
    import csv as csv_module

    buffer = io.StringIO()
    writer = csv_module.DictWriter(buffer, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    return client.post(
        "/api/v1/imports",
        data={
            "file": (io.BytesIO(buffer.getvalue().encode()), "library.csv"),
            **({"dry_run": "true"} if dry_run else {}),
        },
        content_type="multipart/form-data",
    )


def test_the_csv_import_carries_the_new_columns_and_an_update_without_them_keeps_the_values(
    app, client, cast
):
    from app.services.import_service import TEMPLATE_HEADERS

    for column in (
        *fields.PROGRAM_FIELDS,
        *fields.FLAG_FIELDS,
        "operating_mode_mask",
        "user_group_levels",
    ):
        assert column in TEMPLATE_HEADERS
    row = {
        "functional_system_group": "WCNV",
        "functional_subgroup": "010xx",
        "turbine_platforms": "3XM",
        "title": "Imported converter fault",
        "description": "Imported through the spreadsheet with the program fields.",
        "status_category": "ERROR",
        "available_group": "27",
        "set_delay": "10ms",
        "reset_delay": "2min",
        "legacy_reference_number": "3777",
        "hydraulic_pump_program": "7",
        "availability_calc": "yes",
        "operating_mode_mask": "11111110000100000000",
        "task_call_frequency": "10",
        "user_group_levels": "1:1/5 2:1/10",
    }
    login_as(client, cast["engineer"])
    first = _csv_upload(client, row)
    assert first.status_code in (200, 202), first.get_json()
    revision = _revision(app)
    with app.app_context():
        revision = db.session.query(StatusCodeRevision).one()
        assert revision.hydraulic_pump_program == 7 and revision.availability_calc == 1
        assert revision.task_call_frequency == 10
        assert fields.user_groups(revision) == {
            1: {"read": 1, "write": 5},
            2: {"read": 1, "write": 10},
        }

    bad = dict(row, legacy_reference_number="3778", user_group_levels="1-1-5")
    refused = _csv_upload(client, bad, dry_run=True)
    assert "user_group_levels" in json.dumps(refused.get_json())

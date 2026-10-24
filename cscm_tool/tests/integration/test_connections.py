"""How status codes are connected: suppression by a cause, preconditions and escalation, read from the
imported programs (docs/03-srs.md FR-179).

TC-069. Requirements: FR-179, FR-048o, FR-092.
"""

import json
from pathlib import Path

import pytest

from app.extensions import db
from app.importers import stcd
from app.models.import_job import ImportJob, ImportSourceItem
from app.models.status_code import StatusCode
from app.services.connection_service import ConnectionService
from app.utils import utcnow_iso
from tests.helpers import login_as, make_cast
from tests.integration.test_st_import import _confirm, _preview

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "st"


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


# ------------------------------------------------------------------ the reader
def test_a_negated_active_flag_is_a_cause_and_a_plain_one_a_precondition():
    suppressed, required = stcd.condition_links(
        "A AND StatuscodeActiveArBo[StCd_2000.Idx] AND NOT (StatuscodeActiveArBo[StCd_2001.Idx])"
    )
    assert suppressed == [2001] and required == [2000]
    assert stcd.condition_links("NOT StatuscodeActiveArBo [ StCd_5 . Idx ]") == ([5], [])
    assert stcd.condition_links("SomeSignal_GBo") == ([], [])


def test_the_real_programs_name_their_cause_and_their_repeat_code():
    (code,), _ = stcd.parse_bytes((FIXTURES / "StCd_1000.st").read_bytes(), "StCd_1000.st")
    assert code.suppressed_by == [1045] and code.requires == []
    assert code.repeat_code == 9085 and code.disable_variable == "StCd3000DisableGpBo"


# ------------------------------------------------------------------ a small catalogue
def _code(wcnv_ids, owner_id, number, state="RELEASED"):
    from app.models.status_code import StatusCodeRevision

    group_id, subgroup_id = wcnv_ids
    code = StatusCode(
        status_code_identifier=f"StCd-{number:05d}",
        functional_system_group_id=group_id,
        functional_subgroup_id=subgroup_id,
        owner_id=owner_id,
        created_at=utcnow_iso(),
    )
    db.session.add(code)
    db.session.flush()
    db.session.add(
        StatusCodeRevision(
            status_code_id=code.id,
            revision_number=1,
            is_current=1,
            lifecycle_status=state,
            title=f"Code {number}",
            description="A synthetic code for the test.",
            status_category="ERROR",
            available_group=1,
            set_delay="0ms",
            reset_delay="0ms",
            owner_id=owner_id,
            created_by=owner_id,
            created_at=utcnow_iso(),
        )
    )
    return code


def _program(job_id, code, **parsed):
    db.session.add(
        ImportSourceItem(
            import_job_id=job_id,
            status_code_id=code.id,
            source_file="x.st",
            source_sha256="0" * 64,
            program_number=int(code.status_code_identifier[5:]),
            controller="MC",
            parsed_json=json.dumps(parsed),
        )
    )


@pytest.fixture()
def catalogue(app, cast, wcnv_ids):
    """B is a cause; A and X are suppressed by B; C by A (a chain B > A > C); D escalates to a code
    outside the catalogue, E to A; Y is suppressed by a code nobody has; P and Q suppress each other;
    R is suppressed by a deprecated code."""
    with app.app_context():
        owner = cast["admin"].id
        job = ImportJob(
            requested_by=owner,
            source_format="ST",
            source_file_reference="x",
            row_count=0,
            status="COMPLETE",
            created_at=utcnow_iso(),
        )
        db.session.add(job)
        db.session.flush()
        codes = {n: _code(wcnv_ids, owner, n) for n in (10, 11, 12, 13, 14, 15, 16, 17, 18, 19)}
        codes[20] = _code(wcnv_ids, owner, 20, state="DEPRECATED")
        a, b, c, d, e, x, y, p, q, r = (codes[n] for n in (10, 11, 12, 13, 14, 15, 16, 17, 18, 19))
        _program(job.id, a, suppressed_by=[11], requires=[], repeat_code=None)
        _program(job.id, c, suppressed_by=[10], requires=[], repeat_code=None)
        _program(job.id, x, suppressed_by=[11], requires=[12], repeat_code=None)
        _program(job.id, d, suppressed_by=[], requires=[], repeat_code=9085)
        _program(job.id, e, suppressed_by=[], requires=[], repeat_code=10)
        _program(job.id, y, suppressed_by=[99999], requires=[], repeat_code=None)
        _program(job.id, p, suppressed_by=[18], requires=[], repeat_code=None)
        _program(job.id, q, suppressed_by=[17], requires=[], repeat_code=None)
        _program(job.id, r, suppressed_by=[20], requires=[], repeat_code=None)
        db.session.commit()
        return {n: code.id for n, code in codes.items()}


def test_one_code_shows_what_it_depends_on_and_what_depends_on_it(app, catalogue):
    with app.app_context():
        mine = ConnectionService.for_code(catalogue[10])
        assert [(c["kind"], c["code"]["number"]) for c in mine["outgoing"]] == [
            ("SUPPRESSED_BY", 11)
        ]
        assert sorted(c["code"]["number"] for c in mine["incoming"]) == [
            12,
            14,
        ]  # C, and E escalates to it
        assert mine["known"]
        chain = ConnectionService.for_code(catalogue[12])
        assert [n["number"] for n in chain["causes"]] == [10, 11]  # C < A < B
        assert ConnectionService.for_code(catalogue[20])["known"]  # it suppresses R


def test_the_hierarchy_puts_the_cause_on_top_with_what_it_suppresses_below(app, catalogue):
    with app.app_context():
        data = ConnectionService.hierarchy()
        roots = {t["code"]["number"]: t for t in data["trees"]}
        assert set(roots) == {11, 20}  # the two causes that nothing suppresses
        top = roots[11]
        assert sorted(k["code"]["number"] for k in top["children"]) == [10, 15]
        a_branch = next(k for k in top["children"] if k["code"]["number"] == 10)
        assert [k["code"]["number"] for k in a_branch["children"]] == [12]
        assert data["counts"] == {"SUPPRESSED_BY": 7, "REQUIRES": 1, "ESCALATES_TO": 2}


def test_escalation_targets_say_which_are_outside_the_catalogue(app, catalogue):
    with app.app_context():
        targets = {e["number"]: e for e in ConnectionService.hierarchy()["escalation"]}
    assert targets[9085]["code"] is None and [s["number"] for s in targets[9085]["sources"]] == [13]
    assert targets[10]["code"]["number"] == 10


def test_what_looks_wrong_is_listed(app, catalogue):
    with app.app_context():
        findings = {
            (f["type"], f["code"]["number"]) for f in ConnectionService.hierarchy()["findings"]
        }
    assert ("UNKNOWN_CAUSE", 16) in findings  # suppressed by a code that does not exist
    assert ("DEAD_CAUSE", 19) in findings  # suppressed by a deprecated code
    assert {("LOOP", 17), ("LOOP", 18)} <= findings  # a loop has no cause on top


def test_the_hub_and_main_controller_can_be_looked_at_separately(app, catalogue):
    with app.app_context():
        assert ConnectionService.hierarchy("HC")["codes_with_connections"] == 0
        assert ConnectionService.hierarchy("MC")["codes_with_connections"] == 9


# ------------------------------------------------------------------ the screens and the API
def test_the_code_page_and_the_overview_show_the_connections(client, cast, catalogue):
    login_as(client, cast["engineer"])
    page = client.get(f"/status-codes/{catalogue[10]}").get_data(as_text=True)
    assert "Connections" in page and "Suppressed by" in page and "StCd-00011" in page
    chain = client.get(f"/status-codes/{catalogue[12]}").get_data(as_text=True)
    assert "Chain of causes" in chain
    overview = client.get("/status-codes/connections").get_data(as_text=True)
    assert "Causes and the codes they suppress" in overview and "StCd-00011" in overview
    assert "external" in overview and "9085" in overview
    assert "What looks wrong" in overview and "not in the catalogue" in overview
    assert "loop" in overview
    hub = client.get("/status-codes/connections?controller=HC").get_data(as_text=True)
    assert "No connections are known yet" in hub


def test_a_viewer_does_not_see_the_connections(client, cast, catalogue):
    login_as(client, cast["viewer"])
    assert client.get("/status-codes/connections").status_code in (302, 403)
    assert client.get(f"/api/v1/status-codes/{catalogue[10]}/connections").status_code == 403
    page = client.get(f"/status-codes/{catalogue[10]}").get_data(as_text=True)
    assert "Suppressed by" not in page


def test_the_api_returns_the_connections_of_a_code_and_of_the_catalogue(client, cast, catalogue):
    login_as(client, cast["engineer"])
    one = client.get(f"/api/v1/status-codes/{catalogue[12]}/connections").get_json()
    assert [n["number"] for n in one["causes"]] == [10, 11]
    everything = client.get("/api/v1/status-codes/connections").get_json()
    assert everything["counts"]["ESCALATES_TO"] == 2 and everything["trees"]
    assert client.get("/api/v1/status-codes/connections?controller=XX").status_code == 422
    assert client.get("/api/v1/status-codes/999999/connections").status_code == 404


def test_the_menu_offers_the_connections_to_the_working_roles_only(client, cast):
    login_as(client, cast["engineer"])
    assert "/status-codes/connections" in client.get("/").get_data(as_text=True)
    login_as(client, cast["viewer"])
    assert "/status-codes/connections" not in client.get("/").get_data(as_text=True)


# ------------------------------------------------------------------ from a real import
def test_an_imported_program_brings_its_cause_and_its_repeat_code(app, client, cast):
    login_as(client, cast["engineer"])
    preview = _preview(client, ["StCd_1000.st", "StCd_1002.st"]).get_json()
    assert _confirm(client, preview["token"]).status_code in (200, 201, 202)
    with app.app_context():
        data = ConnectionService.hierarchy()
        findings = {(f["type"], f["number"]) for f in data["findings"] if "number" in f}
        assert ("UNKNOWN_CAUSE", 1045) in findings  # StCd_1045 is not among the two files
        assert data["counts"]["SUPPRESSED_BY"] == 2 and data["counts"]["ESCALATES_TO"] == 2
        assert [e["number"] for e in data["escalation"]] == [9085]
        assert len(data["escalation"][0]["sources"]) == 2

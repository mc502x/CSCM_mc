"""The status category per program of a .st import, and the bulk delete of Drafts on the Status
Codes list (FR-181, FR-182).

TC-053, TC-070. Requirements: FR-181, FR-182, FR-026, FR-159.
"""

import io
from pathlib import Path

import pytest

from app.extensions import db
from app.models.status_code import StatusCode
from tests.helpers import cr_id_for_revision, login_as, make_cast, valid_payload

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "st"
MC_FILES = ["StCd_1000.st", "StCd_1001.st", "StCd_1002.st"]  # alarm types 1, 2, 1


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


def _preview(client, names=MC_FILES, **fields):
    data = {"files": [(io.BytesIO((FIXTURES / n).read_bytes()), n) for n in names], **fields}
    response = client.post(
        "/api/v1/imports/st/preview", data=data, content_type="multipart/form-data"
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def _categories(app):
    with app.app_context():
        return {
            c.revisions[0].title: c.revisions[0].status_category
            for c in db.session.query(StatusCode).all()
            if c.revisions
        }


# ------------------------------------------------------------------------------ category
def test_the_alarm_type_of_a_program_sets_its_category(app, client, cast):
    login_as(client, cast["engineer"])
    preview = _preview(
        client,
        default_category="INFO",
        alarm_type_categories='{"1": "ERROR", "2": "WARNING"}',
    )
    by_program = {i["program_number"]: i for i in preview["items"]}
    assert [by_program[n]["alarm_type"] for n in (1000, 1001, 1002)] == [1, 2, 1]
    assert [by_program[n]["category"] for n in (1000, 1001, 1002)] == ["ERROR", "WARNING", "ERROR"]
    assert client.post("/api/v1/imports/st", json={"token": preview["token"]}).status_code == 202
    assert sorted(_categories(app).values()) == ["ERROR", "ERROR", "WARNING"]


def test_a_type_without_a_choice_gets_the_default_category(client, cast):
    login_as(client, cast["engineer"])
    preview = _preview(client, default_category="WARNING", alarm_type_categories='{"1": "ERROR"}')
    assert {i["program_number"]: i["category"] for i in preview["items"]} == {
        1000: "ERROR",
        1001: "WARNING",
        1002: "ERROR",
    }


def test_a_category_chosen_for_one_program_wins(app, client, cast):
    login_as(client, cast["engineer"])
    preview = _preview(client, default_category="ERROR")
    key = next(i["key"] for i in preview["items"] if i["program_number"] == 1001)
    response = client.post(
        "/api/v1/imports/st", json={"token": preview["token"], "categories": {key: "info"}}
    )
    assert response.status_code == 202, response.get_json()
    assert sorted(_categories(app).values()) == ["ERROR", "ERROR", "INFO"]


def test_an_unknown_category_is_refused(client, cast):
    login_as(client, cast["engineer"])
    data = {
        "files": [(io.BytesIO((FIXTURES / "StCd_1000.st").read_bytes()), "StCd_1000.st")],
        "alarm_type_categories": '{"1": "FATAL"}',
    }
    bad = client.post("/api/v1/imports/st/preview", data=data, content_type="multipart/form-data")
    assert bad.status_code in (400, 422)
    broken = _preview(client, ["StCd_1000.st"])
    refused = client.post(
        "/api/v1/imports/st",
        json={"token": broken["token"], "categories": {broken["items"][0]["key"]: "FATAL"}},
    )
    assert refused.status_code in (400, 422)


def test_the_preview_page_lets_the_user_set_the_category_per_program(app, client, cast):
    login_as(client, cast["engineer"])
    form = client.get("/imports/st").get_data(as_text=True)
    assert 'name="alarm_type_1"' in form and 'name="alarm_type_3"' in form
    data = {
        "files": [(io.BytesIO((FIXTURES / n).read_bytes()), n) for n in MC_FILES],
        "default_category": "ERROR",
        "alarm_type_1": "",
        "alarm_type_2": "WARNING",
    }
    page = client.post("/imports/st", data=data, content_type="multipart/form-data")
    html = page.get_data(as_text=True)
    assert html.count('class="st-cat"') == 3 and "data-bulk-category" in html
    assert html.count("selected>WARNING") == 1
    token = html.split('name="token" value="')[1].split('"')[0]
    keys = [part.split('"')[0] for part in html.split('name="cat:')[1:]]
    chosen = {f"cat:{k}": "INFO" for k in keys[:2]}
    done = client.post("/imports/st/confirm", data={"token": token, "selected": keys, **chosen})
    assert done.status_code == 302
    assert sorted(_categories(app).values()) == ["ERROR", "INFO", "INFO"]


# ------------------------------------------------------------------------------ delete Drafts
def _drafts(client, user, wcnv_ids, n=3):
    login_as(client, user)
    ids = []
    for k in range(n):
        created = client.post(
            "/api/v1/status-codes", json=valid_payload(*wcnv_ids, title=f"Delete me {k}")
        )
        assert created.status_code == 201, created.get_json()
        ids.append(created.get_json()["id"])
    return ids


def test_the_list_offers_tick_boxes_for_the_own_drafts_and_deletes_the_ticked(
    app, client, cast, wcnv_ids
):
    revision_ids = _drafts(client, cast["engineer"], wcnv_ids)
    page = client.get("/status-codes").get_data(as_text=True)
    assert page.count('class="sc-row-check"') == 3
    assert 'data-check-all="sc-row-check"' in page and "Delete selected Drafts" in page
    ids = [cr_id_for_revision(app, r) for r in revision_ids]
    done = client.post(
        "/status-codes/withdraw-selected", data={"cr_id": ids[:2]}, follow_redirects=True
    )
    assert "2 Draft(s) deleted." in done.get_data(as_text=True)
    assert client.get("/status-codes").get_data(as_text=True).count('class="sc-row-check"') == 1
    none = client.post("/status-codes/withdraw-selected", data={}, follow_redirects=True)
    assert "Tick at least one" in none.get_data(as_text=True)


def test_all_own_drafts_of_a_filter_are_deleted_on_every_page(app, client, cast, wcnv_ids):
    _drafts(client, cast["engineer"], wcnv_ids, n=4)
    page = client.get("/status-codes?lifecycle_status=DRAFT").get_data(as_text=True)
    assert "Delete all my Drafts of this filter" in page
    assert "Delete all my Drafts" not in client.get("/status-codes").get_data(as_text=True)
    done = client.post(
        "/status-codes/withdraw-selected",
        data={"all_filtered": "1", "lifecycle_status": "DRAFT"},
        follow_redirects=True,
    )
    assert "4 Draft(s) deleted." in done.get_data(as_text=True)
    assert 'class="sc-row-check"' not in client.get("/status-codes").get_data(as_text=True)


def test_somebody_elses_drafts_cannot_be_ticked_or_deleted(app, client, cast, wcnv_ids):
    revision_ids = _drafts(client, cast["engineer"], wcnv_ids, n=2)
    ids = [cr_id_for_revision(app, r) for r in revision_ids]
    login_as(client, cast["admin"])
    assert 'class="sc-row-check"' not in client.get("/status-codes").get_data(as_text=True)
    refused = client.post(
        "/status-codes/withdraw-selected", data={"cr_id": ids}, follow_redirects=True
    )
    assert "0 Draft(s) deleted." not in refused.get_data(as_text=True)
    assert "Only the requesting Engineer" in refused.get_data(as_text=True)
    login_as(client, cast["reviewer"])
    assert client.post("/status-codes/withdraw-selected", data={"cr_id": ids}).status_code == 403
    assert 'class="sc-row-check"' not in client.get("/status-codes").get_data(as_text=True)

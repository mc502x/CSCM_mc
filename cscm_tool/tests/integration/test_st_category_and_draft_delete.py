"""The status category of a .st import is the type of the mapping row (FR-181 superseded by FR-192:
nothing is chosen at the import), and the bulk delete of Drafts on the Status Codes list (FR-182).

TC-053, TC-070. Requirements: FR-181, FR-182, FR-192, FR-026, FR-159.
"""

import io
from pathlib import Path

import pytest

from app.extensions import db
from app.models.status_code import StatusCode
from tests.helpers import cr_id_for_revision, login_as, make_cast, valid_payload

pytestmark = pytest.mark.usefixtures("st_mapping")
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
def test_the_type_of_a_program_is_the_type_of_its_mapping_row(app, client, cast):
    login_as(client, cast["engineer"])
    preview = _preview(client)
    by_program = {i["program_number"]: i for i in preview["items"]}
    assert [by_program[n]["alarm_type"] for n in (1000, 1001, 1002)] == [1, 2, 1]
    # the alarm type of the program has nothing to do with the type: that is the mapping's
    assert [by_program[n]["category"] for n in (1000, 1001, 1002)] == ["ERROR", "WARNING", "INFO"]
    assert client.post("/api/v1/imports/st", json={"token": preview["token"]}).status_code == 202
    assert sorted(_categories(app).values()) == ["ERROR", "INFO", "WARNING"]


def test_a_category_chosen_in_the_request_changes_nothing(app, client, cast):
    login_as(client, cast["engineer"])
    preview = _preview(
        client,
        default_category="INFO",
        alarm_type_categories='{"1": "WARNING"}',
    )
    assert preview["options"] == {
        "controller": "auto",
        "platforms": preview["options"]["platforms"],
    }
    key = next(i["key"] for i in preview["items"] if i["program_number"] == 1001)
    response = client.post(
        "/api/v1/imports/st", json={"token": preview["token"], "categories": {key: "info"}}
    )
    assert response.status_code == 202, response.get_json()
    assert sorted(_categories(app).values()) == ["ERROR", "INFO", "WARNING"]


def test_a_row_without_a_type_blocks_the_program(app, client, cast):
    from app.models.mapping import StatusCodeMapping

    with app.app_context():
        db.session.query(StatusCodeMapping).filter_by(new_number=1001).one().status_type = None
        db.session.commit()
    login_as(client, cast["engineer"])
    items = {i["program_number"]: i for i in _preview(client)["items"]}
    assert items[1001]["state"] == "blocked" and items[1000]["state"] == "ready"
    assert "has no type" in items[1001]["issues"][0]["message"]


def test_the_pages_have_no_category_controls_any_more(app, client, cast):
    login_as(client, cast["engineer"])
    form = client.get("/imports/st").get_data(as_text=True)
    assert 'name="alarm_type_1"' not in form and 'id="default_category"' not in form
    assert "come from the mapping" in form
    data = {"files": [(io.BytesIO((FIXTURES / n).read_bytes()), n) for n in MC_FILES]}
    html = client.post("/imports/st", data=data, content_type="multipart/form-data").get_data(
        as_text=True
    )
    assert 'class="st-cat"' not in html and "data-bulk-category" not in html
    assert "Type (from the mapping)" in html
    token = html.split('name="token" value="')[1].split('"')[0]
    keys = [part.split('"')[0] for part in html.split('name="selected" value="')[1:]]
    done = client.post("/imports/st/confirm", data={"token": token, "selected": keys})
    assert done.status_code == 302
    assert sorted(_categories(app).values()) == ["ERROR", "INFO", "WARNING"]


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

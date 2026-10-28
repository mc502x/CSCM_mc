"""A filter that has several values takes several at once: a panel of tick boxes instead of a single
select, on the status code list, the mapping, its requests and the legacy mapping page. The values
travel as repeated parameters or as one comma-joined string (saved searches and shared links).

TC-080. Requirements: FR-199, FR-026, FR-196.
"""

import pytest

from app.extensions import db
from app.models.mapping import StatusCodeMapping
from app.utils import join_multi, split_multi
from tests.helpers import create_draft, login_as, make_cast


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


def test_the_helpers_read_lists_repeats_and_comma_joined_strings():
    assert split_multi(None) == [] and split_multi("") == []
    assert split_multi("A,B") == ["A", "B"]
    assert split_multi(["A", "B,C", " A ", ""]) == ["A", "B", "C"]
    assert join_multi(["DRAFT", "REVIEW"]) == "DRAFT,REVIEW" and join_multi([]) is None


def test_the_status_filter_of_the_mapping_takes_several_values(app, client, cast, st_mapping):
    with app.app_context():
        db.session.query(StatusCodeMapping).filter_by(new_number=1000).one().status = "PROPOSED"
        db.session.query(StatusCodeMapping).filter_by(new_number=1001).one().status = "REJECTED"
        db.session.commit()
    login_as(client, cast["engineer"])
    both = client.get("/api/v1/mapping?status=PROPOSED&status=REJECTED").get_json()
    assert sorted(r["new_number"] for r in both["rows"]) == [1000, 1001]
    joined = client.get("/api/v1/mapping?status=PROPOSED,REJECTED").get_json()
    assert joined["total"] == 2
    one = client.get("/api/v1/mapping?status=PROPOSED").get_json()
    assert [r["new_number"] for r in one["rows"]] == [1000]
    assert client.get("/api/v1/mapping?status=PROPOSED,NOPE").status_code == 422
    families = client.get("/api/v1/mapping?family=MC&family=HC").get_json()
    assert families["total"] == 6


def test_the_page_shows_a_panel_of_tick_boxes_with_the_chosen_ones_ticked(
    app, client, cast, st_mapping
):
    login_as(client, cast["engineer"])
    page = client.get("/mapping?status=APPROVED&status=ISSUED").get_data(as_text=True)
    assert (
        'class="multi-select"' in page
        and 'type="checkbox" name="status" value="APPROVED" checked' in page
    )
    assert 'name="status" value="ISSUED" checked' in page
    assert (
        'name="status" value="PROPOSED">' in page
        and 'name="status" value="PROPOSED" checked' not in page
    )
    assert 'name="family" value="MC"' in page  # the controller is a panel too
    assert "<summary" in page and "APPROVED, ISSUED" in page  # the summary lists the choice


def test_the_requests_filter_takes_several_states(app, client, cast):
    login_as(client, cast["engineer"])
    made = client.post(
        "/api/v1/mapping-changes",
        json={
            "title": "t",
            "reason": "r",
            "items": [
                {
                    "action": "ADD",
                    "fields": {
                        "family": "MC",
                        "new_number": 1150,
                        "legacy_number": 3100,
                        "description": "Converter test code",
                        "functional_group": "Converter",
                        "logical_node": "WCNV",
                        "status_type": "ERROR",
                        "up_down_counter": "No",
                    },
                }
            ],
        },
    ).get_json()
    client.post(f"/api/v1/mapping-changes/{made['id']}/withdraw")
    assert len(client.get("/api/v1/mapping-changes?state=OPEN").get_json()["changes"]) == 0
    both = client.get("/api/v1/mapping-changes?state=OPEN&state=WITHDRAWN").get_json()
    assert [c["id"] for c in both["changes"]] == [made["id"]]
    page = client.get("/mapping-changes?state=OPEN&state=WITHDRAWN").get_data(as_text=True)
    assert 'name="state" value="WITHDRAWN" checked' in page and ">t<" in page


def test_the_status_code_list_takes_several_lifecycle_states_and_categories(
    app, client, cast, wcnv_ids
):
    revision, cr_id = create_draft(app, client, cast, wcnv_ids)  # a Draft, category ERROR
    login_as(client, cast["engineer"])
    one = client.get("/api/v1/status-codes?lifecycle_status=DRAFT").get_json()
    assert one["total"] == 1
    both = client.get("/api/v1/status-codes?lifecycle_status=DRAFT&lifecycle_status=RELEASED")
    assert both.get_json()["total"] == 1
    joined = client.get("/api/v1/status-codes?lifecycle_status=REVIEW,DRAFT").get_json()
    assert joined["total"] == 1
    none = client.get("/api/v1/status-codes?lifecycle_status=REVIEW&lifecycle_status=RELEASED")
    assert none.get_json()["total"] == 0
    cat = client.get("/api/v1/status-codes?status_category=INFO&status_category=ERROR").get_json()
    assert cat["total"] == 1
    page = client.get("/status-codes?lifecycle_status=DRAFT&lifecycle_status=REVIEW").get_data(
        as_text=True
    )
    assert 'name="lifecycle_status" value="DRAFT" checked' in page
    assert 'name="lifecycle_status" value="REVIEW" checked' in page
    assert 'name="lifecycle_status" value="RELEASED" checked' not in page
    assert "Draft, Review" in page
    platform = client.get("/api/v1/status-codes?turbine_platform=3XM&turbine_platform=2XM")
    assert platform.get_json()["total"] == 1  # a code on two chosen platforms is one row


def test_a_search_with_several_values_is_saved_and_comes_back(app, client, cast):
    login_as(client, cast["engineer"])
    saved = client.post(
        "/saved-searches",
        data={
            "name": "open work",
            "lifecycle_status": ["DRAFT", "REVIEW"],
            "status_category": "ERROR",
        },
    )
    assert saved.status_code == 302
    assert "lifecycle_status=DRAFT,REVIEW" in saved.headers["Location"]
    page = client.get(saved.headers["Location"]).get_data(as_text=True)
    assert 'name="lifecycle_status" value="DRAFT" checked' in page
    assert 'name="lifecycle_status" value="REVIEW" checked' in page


def test_the_legacy_mapping_page_and_api_take_several_values(app, client, cast):
    login_as(client, cast["engineer"])
    api = client.get("/api/v1/legacy-mapping?controller=MC&controller=HC&state=issued,reserved")
    assert api.status_code == 200
    assert client.get("/api/v1/legacy-mapping?controller=MC,XX").status_code == 422
    page = client.get("/legacy-mapping?controller=MC&controller=HC").get_data(as_text=True)
    assert (
        'name="controller" value="MC" checked' in page
        and 'name="controller" value="HC" checked' in page
    )
    assert client.get("/legacy-mapping/export.csv?controller=MC&controller=HC").status_code == 200

"""Business-rule and data-integrity checks: BR-001..BR-003, BR-009, FR-023a,
FR-024, FR-060..FR-064, TC-004, TC-008, TC-010..TC-013."""

import re

import pytest
from sqlalchemy.exc import DatabaseError, IntegrityError

from app.extensions import db
from app.models.status_code import StatusCode, StatusCodeRevision
from app.services.numbering_service import NumberingService
from tests.helpers import (
    create_draft,
    decide,
    domain_sign,
    drive_to_approved,
    drive_to_review,
    login_as,
    make_cast,
    release_revisions,
    submit,
    valid_payload,
)

REAL_ID = re.compile(r"^StCd-\d{5}$")
SANDBOX_ID = re.compile(r"^StCd-T\d{5}$")


# ---- TC-004 identifier formats --------------------------------------------------------------


def test_identifier_formats(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    real, _ = drive_to_review(app, client, cast, wcnv_ids)
    login_as(client, cast["admin"])
    sandbox = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, is_sandbox=True)
    ).get_json()

    current = client.get(f"/api/v1/status-codes/{real['status_code_id']}").get_json()
    assert REAL_ID.match(current["status_code_identifier"])
    assert SANDBOX_ID.match(sandbox["status_code_identifier"])


# ---- TC-008 sub-band independence -------------------------------------------------------------


def test_each_subgroup_sub_band_numbers_independently(app):
    from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup

    with app.app_context():
        group = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(LookupFunctionalSystemGroup.code == "WCNV")
            .one()
        )
        converter = (
            db.session.query(LookupFunctionalSubgroup)
            .filter(
                LookupFunctionalSubgroup.functional_system_group_id == group.id,
                LookupFunctionalSubgroup.code == "010xx",
            )
            .one()
        )
        grid = (
            db.session.query(LookupFunctionalSubgroup)
            .filter(
                LookupFunctionalSubgroup.functional_system_group_id == group.id,
                LookupFunctionalSubgroup.code == "012xx",
            )
            .one()
        )
        assert NumberingService.allocate_next_identifier(group.id, converter.id) == "StCd-01000"
        assert NumberingService.allocate_next_identifier(group.id, grid.id) == "StCd-01200"


def test_sequential_submits_in_two_subgroups_do_not_interfere(app, client, make_user, wcnv_ids):
    from app.models.lookup import LookupFunctionalSubgroup

    cast = make_cast(make_user)
    group_id, converter_id = wcnv_ids
    with app.app_context():
        grid_id = (
            db.session.query(LookupFunctionalSubgroup)
            .filter(
                LookupFunctionalSubgroup.functional_system_group_id == group_id,
                LookupFunctionalSubgroup.code == "012xx",
            )
            .one()
            .id
        )

    identifiers = []
    for sub_id in (converter_id, grid_id, converter_id):
        login_as(client, cast["engineer"])
        created = client.post(
            "/api/v1/status-codes",
            json=valid_payload(group_id, sub_id, title=f"Code in {sub_id} #{len(identifiers)}"),
        ).get_json()
        cr_id = _cr(app, created["id"])
        domain_sign(client, cast, cr_id)
        assert submit(client, cast, cr_id).status_code == 200
        login_as(client, cast["engineer"])
        identifiers.append(
            client.get(f"/api/v1/status-codes/{created['status_code_id']}").get_json()[
                "status_code_identifier"
            ]
        )
    assert identifiers == ["StCd-01000", "StCd-01200", "StCd-01001"]


def _cr(app, revision_id):
    from tests.helpers import cr_id_for_revision

    return cr_id_for_revision(app, revision_id)


# ---- TC-010 / TC-011 / TC-012 / BR-002 / BR-003 -----------------------------------------------


def test_duplicate_identifier_rejected_by_database(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, _ = drive_to_review(app, client, cast, wcnv_ids)
    with app.app_context():
        existing = db.session.get(StatusCodeRevision, revision["id"]).status_code
        duplicate = StatusCode(
            status_code_identifier=existing.status_code_identifier,
            functional_system_group_id=existing.functional_system_group_id,
            functional_subgroup_id=existing.functional_subgroup_id,
            is_sandbox=0,
            owner_id=existing.owner_id,
            created_at=existing.created_at,
        )
        db.session.add(duplicate)
        with pytest.raises(IntegrityError):
            db.session.flush()
        db.session.rollback()


def test_only_one_open_revision_per_code(app, client, make_user, wcnv_ids):
    """BR-003 / TC-012: a second revision cannot be opened while one is open."""
    cast = make_cast(make_user)
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids)
    release_revisions(client, cast, [revision["id"]])

    login_as(client, cast["engineer"])
    url = f"/api/v1/status-codes/{revision['status_code_id']}/revisions"
    first = client.post(url, json=valid_payload(*wcnv_ids, title="Second Revision"))
    assert first.status_code == 201
    second = client.post(url, json=valid_payload(*wcnv_ids, title="Third Revision"))
    assert second.status_code == 409

    # ...and the database enforces it independently of the service (BR-003).
    with app.app_context():
        open_rev = db.session.get(StatusCodeRevision, first.get_json()["id"])
        clone = StatusCodeRevision(
            status_code_id=open_rev.status_code_id,
            revision_number=99,
            is_current=0,
            lifecycle_status="DRAFT",
            title="Rogue",
            description="A rogue second open revision for the same code.",
            status_category="ERROR",
            available_group=27,
            set_delay="10ms",
            reset_delay="2min",
            created_by=open_rev.created_by,
            created_at=open_rev.created_at,
        )
        db.session.add(clone)
        with pytest.raises(DatabaseError):
            db.session.flush()
        db.session.rollback()


def test_exactly_one_current_revision_per_code(app, client, make_user, wcnv_ids):
    """BR-002 / TC-011."""
    cast = make_cast(make_user)
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids)
    release_revisions(client, cast, [revision["id"]])
    login_as(client, cast["engineer"])
    client.post(
        f"/api/v1/status-codes/{revision['status_code_id']}/revisions",
        json=valid_payload(*wcnv_ids, title="Revised Title Here"),
    )
    with app.app_context():
        flags = [
            r.is_current
            for r in db.session.query(StatusCodeRevision).filter(
                StatusCodeRevision.status_code_id == revision["status_code_id"]
            )
        ]
        assert sorted(flags) == [0, 1]
        db.session.add(
            StatusCodeRevision(
                status_code_id=revision["status_code_id"],
                revision_number=50,
                is_current=1,
                lifecycle_status="ARCHIVED",
                title="Another current",
                description="A second revision flagged current for the same code.",
                status_category="ERROR",
                available_group=27,
                set_delay="10ms",
                reset_delay="2min",
                created_by=1,
                created_at="2026-01-01T00:00:00.000Z",
            )
        )
        with pytest.raises(DatabaseError):
            db.session.flush()
        db.session.rollback()


def test_identifier_never_changes_after_allocation(app, client, make_user, wcnv_ids):
    """BR-001: a rejected-and-resubmitted CR keeps its identifier."""
    cast = make_cast(make_user)
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    before = client.get(f"/api/v1/status-codes/{revision['status_code_id']}").get_json()[
        "status_code_identifier"
    ]
    decide(client, cast["reviewer"], cr_id, "reviewer-signoff", decision="REJECT", comment="Fix it")
    assert submit(client, cast, cr_id).status_code == 200
    login_as(client, cast["engineer"])
    after = client.get(f"/api/v1/status-codes/{revision['status_code_id']}").get_json()[
        "status_code_identifier"
    ]
    assert before == after


# ---- FR-023a / FR-024 -------------------------------------------------------------------------


def test_submit_requires_a_turbine_platform(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    created = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, turbine_platforms=[])
    )
    # Either the draft is refused outright or it is accepted but cannot be submitted.
    if created.status_code == 201:
        cr_id = _cr(app, created.get_json()["id"])
        domain_sign(client, cast, cr_id)
        response = submit(client, cast, cr_id)
        assert response.status_code == 422
        assert "Turbine Platform" in response.get_json()["message"]
    else:
        assert created.status_code == 422


def test_draft_can_be_saved_repeatedly_without_workflow_transitions(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    revision, _ = create_draft(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    for n in range(3):
        response = client.patch(
            f"/api/v1/revisions/{revision['id']}",
            json=valid_payload(*wcnv_ids, title=f"Edited title number {n}"),
        )
        assert response.status_code == 200, response.get_json()
        assert response.get_json()["lifecycle_status"] == "DRAFT"
        assert response.get_json()["title"] == f"Edited title number {n}"


def test_in_flight_revision_cannot_be_edited_in_place(app, client, make_user, wcnv_ids):
    """FR-025: Review and later states are locked."""
    cast = make_cast(make_user)
    revision, _ = drive_to_review(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    response = client.patch(
        f"/api/v1/revisions/{revision['id']}", json=valid_payload(*wcnv_ids, title="Sneaky edit")
    )
    assert response.status_code == 409


# ---- FR-060..FR-064 search, filter, sort, paginate, history ---------------------------------


def _three_drafts(app, client, cast, wcnv_ids):
    for title in ("Alpha converter trip", "Bravo converter trip", "Charlie grid fault"):
        create_draft(app, client, cast, wcnv_ids, title=title)
    login_as(client, cast["engineer"])


def test_full_text_search_matches_identifier_title_and_description(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    revision, _ = drive_to_review(app, client, cast, wcnv_ids, title="Searchable Title Zulu")
    create_draft(
        app,
        client,
        cast,
        wcnv_ids,
        title="Other",
        description="A description containing the marker word quokka.",
    )
    login_as(client, cast["engineer"])
    identifier = client.get(f"/api/v1/status-codes/{revision['status_code_id']}").get_json()[
        "status_code_identifier"
    ]

    def total(q):
        return client.get("/api/v1/status-codes", query_string={"q": q}).get_json()["total"]

    assert total("Zulu") == 1
    assert total("quokka") == 1
    assert total(identifier) == 1
    assert total("nomatchatall") == 0


def test_filters_sort_and_pagination(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _three_drafts(app, client, cast, wcnv_ids)

    listing = client.get("/api/v1/status-codes?sort=title").get_json()
    titles = [i["title"] for i in listing["items"]]
    assert titles == sorted(titles)
    desc = client.get("/api/v1/status-codes?sort=-title").get_json()
    assert [i["title"] for i in desc["items"]] == sorted(titles, reverse=True)

    page = client.get("/api/v1/status-codes?page=2&page_size=2&sort=title").get_json()
    assert (page["total"], page["page"], page["page_size"], len(page["items"])) == (3, 2, 2, 1)
    assert client.get("/api/v1/status-codes?page_size=100000").get_json()["page_size"] == 200

    group_id, subgroup_id = wcnv_ids
    for params, expected in (
        ({"functional_system_group": group_id}, 3),
        ({"functional_subgroup": subgroup_id}, 3),
        ({"turbine_platform": "3XM"}, 3),
        ({"turbine_platform": "2XM"}, 0),
        ({"lifecycle_status": "DRAFT"}, 3),
        ({"lifecycle_status": "RELEASED"}, 0),
        ({"owner_id": 99999}, 0),
        ({"functional_system_group": group_id, "turbine_platform": "2XM"}, 0),
    ):
        assert (
            client.get("/api/v1/status-codes", query_string=params).get_json()["total"] == expected
        ), params


def test_revision_history_visible_to_viewer_only_once_decided(app, client, make_user, wcnv_ids):
    """FR-064 / BR-009."""
    cast = make_cast(make_user)
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids)
    release_revisions(client, cast, [revision["id"]])
    login_as(client, cast["engineer"])
    client.post(
        f"/api/v1/status-codes/{revision['status_code_id']}/revisions",
        json=valid_payload(*wcnv_ids, title="Open second revision"),
    )

    login_as(client, cast["viewer"])
    history = client.get(f"/api/v1/status-codes/{revision['status_code_id']}/revisions").get_json()
    assert [r["revision_number"] for r in history] == [1]
    login_as(client, cast["engineer"])
    history = client.get(f"/api/v1/status-codes/{revision['status_code_id']}/revisions").get_json()
    assert [r["revision_number"] for r in history] == [1, 2]


def test_new_revision_of_a_released_code_keeps_its_identifier(app, client, make_user, wcnv_ids):
    """BR-001 / FR-021: the identifier is allocated once, not again per revision."""
    cast = make_cast(make_user)
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids)
    release_revisions(client, cast, [revision["id"]])
    login_as(client, cast["engineer"])
    original = client.get(f"/api/v1/status-codes/{revision['status_code_id']}").get_json()[
        "status_code_identifier"
    ]

    second = client.post(
        f"/api/v1/status-codes/{revision['status_code_id']}/revisions",
        json=valid_payload(*wcnv_ids, title="Revised for the identifier test"),
    ).get_json()
    cr_id = _cr(app, second["id"])
    domain_sign(client, cast, cr_id)
    assert submit(client, cast, cr_id).status_code == 200

    login_as(client, cast["engineer"])
    after = client.get(f"/api/v1/status-codes/{revision['status_code_id']}").get_json()
    assert after["status_code_identifier"] == original
    assert after["revision_number"] == 2


def test_released_code_stays_visible_to_viewers_while_a_new_revision_is_open(
    app, client, make_user, wcnv_ids
):
    """BR-009: opening revision 2 (a Draft) must not make the Released revision 1
    disappear for a Viewer, in the detail view or in search."""
    cast = make_cast(make_user)
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids, title="Visible released code")
    release_revisions(client, cast, [revision["id"]])
    login_as(client, cast["engineer"])
    client.post(
        f"/api/v1/status-codes/{revision['status_code_id']}/revisions",
        json=valid_payload(*wcnv_ids, title="Draft revision two"),
    )

    login_as(client, cast["viewer"])
    detail = client.get(f"/api/v1/status-codes/{revision['status_code_id']}")
    assert detail.status_code == 200
    assert detail.get_json()["revision_number"] == 1
    assert detail.get_json()["lifecycle_status"] == "RELEASED"
    found = client.get("/api/v1/status-codes", query_string={"q": "Visible released"}).get_json()
    assert [i["revision_number"] for i in found["items"]] == [1]
    # ...and the Draft title never leaks.
    assert (
        client.get("/api/v1/status-codes", query_string={"q": "Draft revision two"}).get_json()[
            "total"
        ]
        == 0
    )

    login_as(client, cast["engineer"])  # authors still see the working revision
    assert (
        client.get(f"/api/v1/status-codes/{revision['status_code_id']}").get_json()[
            "revision_number"
        ]
        == 2
    )

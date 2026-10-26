"""TC-030: UAT-01 .. UAT-13 (docs/13-test-strategy.md §7) as scripted
acceptance scenarios against the running application (API + server-rendered
UI). These automate the scenarios' observable outcomes; the business
sign-off on them is still a human UAT pass (docs/16-mvp-roadmap.md exit
criteria)."""

import csv
import io

from app.extensions import db
from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup
from tests.helpers import (
    PASSWORD,
    cr_id_for_revision,
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


def ui_login(client, user):
    from app.auth.rate_limit import reset_for_testing

    reset_for_testing()
    client.post("/logout")
    assert (
        client.post("/login", data={"username": user.username, "password": PASSWORD}).status_code
        == 302
    )


def _state(client, cast, who, status_code_id):
    login_as(client, cast[who])
    return client.get(f"/api/v1/status-codes/{status_code_id}").get_json()


def test_uat_01_new_code_has_no_identifier_until_submitted(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, cr_id = create_draft(app, client, cast, wcnv_ids)
    assert revision["status_code_identifier"] is None
    ui_login(client, cast["engineer"])
    assert "Not yet assigned" in client.get(f"/change-requests/{cr_id}").get_data(as_text=True)

    domain_sign(client, cast, cr_id)
    assert submit(client, cast, cr_id).status_code == 200
    identifier = _state(client, cast, "engineer", revision["status_code_id"])[
        "status_code_identifier"
    ]
    assert identifier.startswith("StCd-01")


def test_uat_02_either_signoff_order_reaches_pending_approval_automatically(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    assert decide(client, cast["admin"], cr_id, "admin-signoff").get_json()["state"] == "REVIEW"
    assert (
        decide(client, cast["reviewer"], cr_id, "reviewer-signoff").get_json()["state"]
        == "PENDING_APPROVAL"
    )


def test_uat_03_chief_engineer_approval_visible_to_the_engineer(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids)
    assert (
        _state(client, cast, "engineer", revision["status_code_id"])["lifecycle_status"]
        == "APPROVED"
    )
    ui_login(client, cast["engineer"])
    assert "Approved" in client.get("/change-requests/mine").get_data(as_text=True)


def test_uat_04_rejection_comment_visible_and_prior_signoff_cleared(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    decide(client, cast["admin"], cr_id, "admin-signoff")  # admin signs first...
    decide(
        client,
        cast["reviewer"],
        cr_id,
        "reviewer-signoff",
        decision="REJECT",
        comment="Set delay is not plausible for this trip.",
    )

    login_as(client, cast["engineer"])
    cr = client.get(f"/api/v1/change-requests/{cr_id}").get_json()
    assert any("not plausible" in c["comment_text"] for c in cr["comments"])
    assert (
        _state(client, cast, "engineer", revision["status_code_id"])["lifecycle_status"] == "DRAFT"
    )

    edited = client.patch(
        f"/api/v1/revisions/{revision['id']}", json=valid_payload(*wcnv_ids, set_delay="20ms")
    )
    assert edited.status_code == 200
    assert submit(client, cast, cr_id).status_code == 200
    # ...the Administrator's earlier sign-off was discarded: one sign-off alone leaves it in Review.
    assert (
        decide(client, cast["reviewer"], cr_id, "reviewer-signoff").get_json()["state"] == "REVIEW"
    )


def test_uat_05_cross_domain_signoff_unblocks_submit(app, client, make_user):
    cast = make_cast(make_user)
    electrical = make_user("ENGINEER", engineering_domains=["ELECTRICAL"])
    with app.app_context():
        group = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(LookupFunctionalSystemGroup.code == "WGEN")
            .one()
        )
        subgroup = (
            db.session.query(LookupFunctionalSubgroup)
            .filter(
                LookupFunctionalSubgroup.functional_system_group_id == group.id,
                LookupFunctionalSubgroup.code == "020xx",
            )
            .one()
        )
        ids = (group.id, subgroup.id)

    login_as(client, electrical)
    created = client.post(
        "/api/v1/status-codes", json=valid_payload(*ids, title="Generator trip")
    ).get_json()
    cr_id = cr_id_for_revision(app, created["id"])
    assert client.post(f"/api/v1/change-requests/{cr_id}/submit").status_code == 422  # blocked

    assert (
        client.post(
            f"/api/v1/change-requests/{cr_id}/domain-signoff-requests",
            json={"engineering_domain": "CONTROLS", "target_user_id": cast["controls_engineer"].id},
        ).status_code
        == 201
    )
    domain_sign(client, cast, cr_id)
    login_as(client, electrical)
    assert client.post(f"/api/v1/change-requests/{cr_id}/submit").status_code == 200


def test_uat_06_release_build_excludes_unselected_and_sandbox(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    included, _ = drive_to_approved(app, client, cast, wcnv_ids, title="Included code")
    excluded, _ = drive_to_approved(app, client, cast, wcnv_ids, title="Excluded code")
    login_as(client, cast["admin"])
    client.post("/api/v1/status-codes", json=valid_payload(*wcnv_ids, is_sandbox=True))

    release = client.post("/api/v1/releases", json={"name": "R", "version_label": "v1"}).get_json()
    candidates = client.get(f"/api/v1/releases/{release['id']}/candidates").get_json()
    assert {c["id"] for c in candidates} == {included["id"], excluded["id"]}  # no sandbox
    client.put(
        f"/api/v1/releases/{release['id']}/items",
        json={"status_code_revision_ids": [included["id"]]},
    )
    assert client.post(f"/api/v1/releases/{release['id']}/publish").status_code == 200

    assert (
        _state(client, cast, "admin", included["status_code_id"])["lifecycle_status"] == "RELEASED"
    )
    assert (
        _state(client, cast, "admin", excluded["status_code_id"])["lifecycle_status"] == "APPROVED"
    )


def test_uat_07_viewer_searches_and_exports_released_catalogue_for_one_group(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids, title="Released converter code")
    release_revisions(client, cast, [revision["id"]])

    login_as(client, cast["viewer"])
    found = client.get("/api/v1/status-codes", query_string={"q": "Released converter"}).get_json()
    assert found["total"] == 1
    export = client.get(
        "/api/v1/exports/released",
        query_string={"format": "csv", "functional_system_group": wcnv_ids[0]},
    )
    rows = list(csv.DictReader(io.StringIO(export.get_data(as_text=True))))
    assert [r["title"] for r in rows] == ["Released converter code"]


def test_uat_08_sandbox_lifecycle_and_traceable_deletion(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["admin"])
    sandbox = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, is_sandbox=True)
    ).get_json()
    release = client.post("/api/v1/releases", json={"name": "R", "version_label": "v1"}).get_json()
    rejected = client.put(
        f"/api/v1/releases/{release['id']}/items",
        json={"status_code_revision_ids": [sandbox["id"]]},
    )
    assert rejected.status_code == 422

    assert client.delete(f"/api/v1/status-codes/{sandbox['status_code_id']}").status_code == 204
    entries = client.get(
        "/api/v1/audit-log", query_string={"entity_id": sandbox["status_code_id"]}
    ).get_json()
    assert {"SANDBOX_CREATE", "SANDBOX_DELETE"} <= {e["action"] for e in entries}


def test_uat_09_nobody_can_decide_their_own_submission(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    # An Administrator authors the CR, so they hold both the author and approver capability.
    _, cr_id = create_draft(app, client, cast, wcnv_ids, who="admin")
    domain_sign(client, cast, cr_id)
    assert submit(client, cast, cr_id, who="admin").status_code == 200

    assert decide(client, cast["admin"], cr_id, "admin-signoff").status_code == 403  # point 2 (API)
    ui_login(client, cast["admin"])
    client.post(f"/change-requests/{cr_id}/admin-signoff", data={"decision": "APPROVE"})  # (UI)
    login_as(client, cast["admin"])
    state = client.get(f"/api/v1/change-requests/{cr_id}").get_json()
    assert state["state"] == "REVIEW"


def test_uat_09b_chief_engineer_cannot_be_a_prior_signer_or_author(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    decide(client, cast["reviewer"], cr_id, "reviewer-signoff")
    decide(client, cast["admin"], cr_id, "admin-signoff")
    for who in ("engineer", "reviewer", "admin"):
        assert decide(client, cast[who], cr_id, "chief-engineer-decide").status_code == 403
    assert decide(client, cast["chief_engineer"], cr_id, "chief-engineer-decide").status_code == 200


def test_uat_10_full_database_export_is_administrator_only(app, client, make_user):
    cast = make_cast(make_user)
    for who in ("engineer", "reviewer", "chief_engineer", "viewer"):
        login_as(client, cast[who])
        assert client.post("/api/v1/exports/full-database").status_code == 403
    login_as(client, cast["admin"])
    response = client.post("/api/v1/exports/full-database")
    assert response.status_code == 200
    assert response.data[:16] == b"SQLite format 3\x00"


def test_uat_11_import_creates_only_governed_drafts_and_an_error_report(app, client, make_user):
    cast = make_cast(make_user)
    rows = [
        {
            "functional_system_group": "WCNV",
            "functional_subgroup": "010xx",
            "turbine_platforms": "3XM",
            "title": title,
            "description": "Imported via CSV library import UAT scenario.",
            "status_category": category,
            "available_group": "27",
            "set_delay": "10ms",
            "reset_delay": "2min",
        }
        for title, category in (("Good one", "ERROR"), ("Good two", "WARNING"), ("Bad row", "NOPE"))
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)

    login_as(client, cast["engineer"])
    job = client.post(
        "/api/v1/imports",
        data={"file": (io.BytesIO(buffer.getvalue().encode()), "library.csv")},
        content_type="multipart/form-data",
    ).get_json()
    assert (job["created_count"], job["error_count"]) == (2, 1)

    listing = client.get("/api/v1/status-codes", query_string={"q": "Good"}).get_json()
    assert {i["lifecycle_status"] for i in listing["items"]} == {"DRAFT"}
    report = client.get(f"/api/v1/imports/{job['id']}/errors")
    assert report.status_code == 200
    lines = report.get_data(as_text=True).strip().splitlines()
    # I-05e: one line per problem with row, column, value, error and a fix hint
    assert lines[0] == "row,column,value,error,how_to_fix" and lines[1].startswith(
        "4,"
    )  # header is row 1; "Bad row" is row 4


def test_uat_12_subgroup_is_mandatory_and_overlaps_are_refused(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    payload = valid_payload(*wcnv_ids)
    del payload["functional_subgroup"]
    assert client.post("/api/v1/status-codes", json=payload).status_code == 422

    login_as(client, cast["admin"])
    free_group = client.post(
        "/api/v1/lookups/functional-system-groups",
        json={"code": "WNEW", "label": "New Subsystem", "range_start": 15000, "range_end": 15999},
    )
    assert free_group.status_code == 201
    group_id = free_group.get_json()["id"]
    sub = {
        "functional_system_group": group_id,
        "code": "150xx",
        "label": "First",
        "sub_range_start": 15000,
        "sub_range_end": 15099,
    }
    assert (
        client.post("/api/v1/lookups/functional-subgroups", json={**sub, "code": "a"}).status_code
        == 201
    )
    overlap = client.post(
        "/api/v1/lookups/functional-subgroups",
        json={**sub, "code": "b", "sub_range_start": 15050, "sub_range_end": 15150},
    )
    assert overlap.status_code in (409, 422)
    assert client.post(
        "/api/v1/lookups/functional-system-groups",
        json={"code": "WCLS", "label": "Clash", "range_start": 15500, "range_end": 16500},
    ).status_code in (409, 422)


def test_uat_13_failed_form_keeps_input_and_dropdowns_explain_themselves(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    ui_login(client, cast["engineer"])
    response = client.post(
        "/status-codes/new",
        data={
            "functional_system_group": wcnv_ids[0],
            "functional_subgroup": wcnv_ids[1],
            "turbine_platforms": ["3XM"],
            "title": "Kept after failure",
            "description": "short",  # invalid
            "status_category": "ERROR",
            "available_group": "27",
            "set_delay": "10ms",
            "reset_delay": "2min",
        },
    )
    html = response.get_data(as_text=True)
    assert "Kept after failure" in html and "description" in html
    assert 'data-help="help_available_group"' in html and 'data-help="help_customer_access"' in html

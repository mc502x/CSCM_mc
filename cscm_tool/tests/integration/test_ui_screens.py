"""S1–S19 server-rendered UI: every screen renders for the roles that can
reach it, the reworked CR-detail controls appear for the right roles, and
forms never discard entered data (NFR-007a / TC-036, UAT-13)."""

import pytest

from app.auth.rate_limit import reset_for_testing
from tests.helpers import (
    PASSWORD,
    create_draft,
    domain_sign,
    drive_to_review,
    login_as,
    make_cast,
    valid_payload,
)


def ui_login(client, user):
    reset_for_testing()
    client.post("/logout")  # the login view ignores a POST while someone is signed in
    response = client.post("/login", data={"username": user.username, "password": PASSWORD})
    assert response.status_code == 302


def test_every_screen_renders_for_an_administrator(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    login_as(client, cast["admin"])
    release = client.post("/api/v1/releases", json={"name": "R", "version_label": "v1"}).get_json()
    sandbox = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, is_sandbox=True)
    ).get_json()

    ui_login(client, cast["admin"])
    pages = [
        "/",
        "/status-codes",
        "/status-codes/new",
        "/status-codes/new-sandbox",
        f"/status-codes/{revision['status_code_id']}",
        f"/status-codes/{revision['status_code_id']}?tab=history",
        f"/status-codes/{sandbox['status_code_id']}",
        f"/change-requests/{cr_id}",
        "/change-requests/mine",
        "/change-requests/review-queue",
        "/releases",
        "/releases/new",
        f"/releases/{release['id']}",
        f"/releases/{release['id']}/builder",
        "/imports/new",
        "/admin/users",
        "/admin/lookups",
        "/admin/lookups?vocabulary=development-access",
        "/admin/audit-log",
        "/exports",
        "/account",
    ]
    for path in pages:
        response = client.get(path)
        assert response.status_code == 200, path


@pytest.mark.parametrize(
    "who,path",
    [
        ("engineer", "/change-requests/mine"),
        ("engineer", "/exports"),
        ("reviewer", "/change-requests/review-queue"),
        ("chief_engineer", "/change-requests/approval-queue"),
        ("viewer", "/status-codes"),
        ("viewer", "/exports"),
    ],
)
def test_role_specific_screens_render(app, client, make_user, who, path):
    cast = make_cast(make_user)
    ui_login(client, cast[who])
    assert client.get(path).status_code == 200


def test_cr_detail_shows_role_specific_controls(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = create_draft(app, client, cast, wcnv_ids)

    ui_login(client, cast["engineer"])
    page = client.get(f"/change-requests/{cr_id}").get_data(as_text=True)
    assert "Request a Sign-Off" in page  # FR-028, requester only
    assert "Assign Reviewer" not in page
    assert "Add Comment" not in page

    ui_login(client, cast["admin"])
    page = client.get(f"/change-requests/{cr_id}").get_data(as_text=True)
    assert "Assign Reviewer" in page  # FR-039
    assert "Add Comment" in page  # FR-038
    assert "Request a Sign-Off" not in page
    assert "(new code)" in page  # FR-032


def test_admin_signoff_form_offers_access_override_and_submit_override(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    ui_login(client, cast["admin"])
    page = client.get(f"/change-requests/{cr_id}").get_data(as_text=True)
    assert "Confirm or override Audience Access" in page

    _, draft_cr = create_draft(app, client, cast, wcnv_ids, who="admin", title="Admin Draft")
    ui_login(client, cast["admin"])
    page = client.get(f"/change-requests/{draft_cr}").get_data(as_text=True)
    assert "Override identifier" in page  # FR-021a, admin requester only


def test_sign_off_request_listed_on_my_change_requests(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = create_draft(app, client, cast, wcnv_ids)
    ui_login(client, cast["engineer"])
    response = client.post(
        f"/change-requests/{cr_id}/domain-signoff-requests",
        data={"engineering_domain": "CONTROLS", "target_user_id": cast["controls_engineer"].id},
    )
    assert response.status_code == 302

    ui_login(client, cast["controls_engineer"])
    assert "Sign-Off Requests For You" in client.get("/change-requests/mine").get_data(as_text=True)
    dashboard = client.get("/").get_data(as_text=True)
    assert "Domain Sign-Off" in dashboard or "domain" in dashboard.lower()


def test_ui_comment_reviewer_assignment_and_override_flow(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids)

    ui_login(client, cast["admin"])
    assert (
        client.post(
            f"/change-requests/{cr_id}/comments", data={"comment": "Looks plausible."}
        ).status_code
        == 302
    )
    client.post(
        f"/change-requests/{cr_id}/reviewer-assignment", data={"reviewer_id": cast["reviewer"].id}
    )
    page = client.get(f"/change-requests/{cr_id}").get_data(as_text=True)
    assert "Looks plausible." in page
    assert cast["reviewer"].full_name in page

    ui_login(client, cast["reviewer"])
    client.post(f"/change-requests/{cr_id}/reviewer-signoff", data={"decision": "APPROVE"})
    ui_login(client, cast["admin"])
    development_id = client.get("/api/v1/lookups/development-access").get_json()[0]["id"]
    client.post(
        f"/change-requests/{cr_id}/admin-signoff",
        data={"decision": "APPROVE", "development_access": development_id},
    )
    login_as(client, cast["admin"])
    current = client.get(f"/api/v1/status-codes/{revision['status_code_id']}").get_json()
    assert current["development_access_id"] == development_id
    assert current["lifecycle_status"] == "PENDING_APPROVAL"


def test_failed_form_submission_keeps_every_entered_value(app, client, make_user, wcnv_ids):
    """NFR-007a / TC-036 / UAT-13."""
    cast = make_cast(make_user)
    ui_login(client, cast["engineer"])
    response = client.post(
        "/status-codes/new",
        data={
            "functional_system_group": wcnv_ids[0],
            "functional_subgroup": wcnv_ids[1],
            "turbine_platforms": ["3XM", "4XM"],
            "title": "A Distinctive Title 12345",
            "description": "A long enough description that should survive a failed save.",
            "status_category": "ERROR",
            "available_group": "27",
            "set_delay": "10minutes",  # invalid unit
            "reset_delay": "2min",
            "software_version": "9.9.9.9",
        },
    )
    html = response.get_data(as_text=True)
    assert "set_delay" in html  # the error is reported
    assert "A Distinctive Title 12345" in html
    assert "A long enough description that should survive a failed save." in html
    assert 'value="9.9.9.9"' in html
    assert 'value="10minutes"' in html
    assert html.count("checked") >= 2  # both platforms still ticked


def test_lookup_selects_carry_inline_help_hooks(app, client, make_user):
    """NFR-007b: each lookup-backed select has a help target and per-option text."""
    cast = make_cast(make_user)
    ui_login(client, cast["admin"])
    form = client.get("/status-codes/new").get_data(as_text=True)
    for field in (
        "functional_system_group",
        "functional_subgroup",
        "available_group",
        "development_access",
        "customer_access",
    ):
        assert f'data-help="help_{field}"' in form
        assert f'id="help_{field}"' in form
    assert "data-description=" in form


def test_lookup_description_is_editable_and_flows_to_form_and_api(app, client, make_user):
    cast = make_cast(make_user)
    login_as(client, cast["admin"])
    first = client.get("/api/v1/lookups/development-access").get_json()[0]
    assert first["description"] is None

    ui_login(client, cast["admin"])
    client.post(
        f"/admin/lookups/development-access/{first['id']}/update",
        data={
            "label": first["label"],
            "description": "Can operate the turbine from SCADA.",
            "is_active": "on",
        },
    )
    login_as(client, cast["admin"])
    updated = client.get("/api/v1/lookups/development-access").get_json()[0]
    assert updated["description"] == "Can operate the turbine from SCADA."
    ui_login(client, cast["admin"])
    assert "Can operate the turbine from SCADA." in client.get("/status-codes/new").get_data(
        as_text=True
    )


def test_default_role_for_new_user_is_viewer(app, client, make_user):
    """SEC-012."""
    admin = make_user("ADMINISTRATOR")
    login_as(client, admin)
    created = client.post(
        "/api/v1/users",
        json={
            "username": "newbie",
            "email": "newbie@example.com",
            "full_name": "New Bie",
            "password": "a genuinely long passphrase",
        },
    )
    assert created.status_code == 201
    assert created.get_json()["role"] == "VIEWER"


def test_comments_api_validates_and_is_role_restricted(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    url = f"/api/v1/change-requests/{cr_id}/comments"

    login_as(client, cast["engineer"])
    assert client.post(url, json={"comment": "hi"}).status_code == 403

    login_as(client, cast["chief_engineer"])
    assert client.post(url, json={"comment": "   "}).status_code == 422
    ok = client.post(url, json={"comment": "Please double-check the delay."})
    assert ok.status_code == 201
    assert ok.get_json()["comments"][-1]["comment_text"] == "Please double-check the delay."
    # a comment changes no state
    assert ok.get_json()["state"] == "REVIEW"


def test_draft_cr_page_says_it_must_still_be_submitted(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = create_draft(app, client, cast, wcnv_ids)
    ui_login(client, cast["engineer"])
    assert "Waiting for cross-domain sign-off" in client.get(f"/change-requests/{cr_id}").get_data(
        as_text=True
    )

    domain_sign(client, cast, cr_id)
    ui_login(client, cast["engineer"])
    page = client.get(f"/change-requests/{cr_id}").get_data(as_text=True)
    assert "Not yet submitted" in page
    ui_login(client, cast["reviewer"])
    assert "author has to submit it" in client.get(f"/change-requests/{cr_id}").get_data(
        as_text=True
    )


def test_people_are_shown_by_name_and_lists_show_the_title(app, client, make_user, wcnv_ids):
    """Authors, signers and commenters appear as "Full Name (Role)", never "User #n";
    the change-request lists show identifier and title."""
    cast = make_cast(make_user)
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids, title="Titled Converter Trip")
    login_as(client, cast["admin"])
    client.post(f"/api/v1/change-requests/{cr_id}/comments", json={"comment": "looks fine"})
    login_as(client, cast["reviewer"])
    client.post(f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"})

    ui_login(client, cast["admin"])
    detail = client.get(f"/change-requests/{cr_id}").get_data(as_text=True)
    assert "User #" not in detail
    assert f"{cast['engineer'].full_name} (Engineer)" in detail  # author
    assert f"{cast['reviewer'].full_name} (Reviewer)" in detail  # signer and commenter
    assert "Reviewer approved" in detail and "REVIEWER_APPROVE" not in detail
    assert f"{cast['admin'].full_name} (Administrator)" in detail  # commenter

    queue = client.get("/change-requests/review-queue").get_data(as_text=True)
    assert "Titled Converter Trip" in queue and cast["engineer"].full_name in queue

    ui_login(client, cast["engineer"])
    mine = client.get("/change-requests/mine").get_data(as_text=True)
    assert "Titled Converter Trip" in mine and "StCd-" in mine
    assert "User #" not in mine
    ui_login(client, cast["admin"])
    audit_page = client.get("/admin/audit-log").get_data(as_text=True)
    assert f"{cast['engineer'].full_name} (Engineer)" in audit_page  # actor column by name

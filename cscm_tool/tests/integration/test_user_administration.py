"""Viewing, deactivating and deleting users (docs/03-srs.md FR-158, BR-025, SEC-032). An account that
was never used can be deleted; one with history can only be deactivated, so the audit trail stays
attributable. Only an Administrator, with the password again.

TC-055. Requirements: FR-158, BR-025, SEC-032, FR-012, AUD-076.
"""

import json

import pytest

from app.extensions import db
from app.models.audit import AuditLogEntry
from app.models.user import User
from tests.helpers import PASSWORD, login_as, make_cast, valid_payload


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


def _new_user(client, name="fresh", role="VIEWER", domains=("CONTROLS",)):
    created = client.post(
        "/api/v1/users",
        json={
            "username": name,
            "email": f"{name}@example.com",
            "full_name": f"Fresh {name}",
            "password": "a genuinely long passphrase",
            "role": role,
            "engineering_domains": list(domains),
        },
    )
    assert created.status_code == 201, created.get_json()
    return created.get_json()["id"]


def _delete(client, user_id, password=PASSWORD):
    body = {} if password is None else {"current_password": password}
    return client.post(f"/api/v1/users/{user_id}/delete", json=body)


# ------------------------------------------------------------------------------ delete
def test_an_account_that_was_never_used_can_be_deleted_and_the_deletion_is_audited(
    app, client, cast
):
    login_as(client, cast["admin"])
    user_id = _new_user(client)
    usage = client.get(f"/api/v1/users/{user_id}/usage").get_json()
    assert usage["deletable"] is True and usage["references"] == {}
    assert _delete(client, user_id).status_code == 204
    assert client.get(f"/api/v1/users/{user_id}").status_code == 404
    with app.app_context():
        assert db.session.get(User, user_id) is None
        from sqlalchemy import text

        assert not db.session.execute(
            text("SELECT 1 FROM user_engineering_domain WHERE user_id = :i"), {"i": user_id}
        ).first()  # the domain tags went with the account
        entry = (
            db.session.query(AuditLogEntry).filter_by(action="USER_DELETE", entity_id=user_id).one()
        )
        before = json.loads(entry.before_value)
        assert before["username"] == "fresh" and before["role"] == "VIEWER"
        assert before["engineering_domains"] == ["CONTROLS"]
        assert entry.actor_id == cast["admin"].id


def test_an_account_with_history_cannot_be_deleted_only_deactivated(app, client, cast, wcnv_ids):
    login_as(client, cast["engineer"])
    created = client.post("/api/v1/status-codes", json=valid_payload(*wcnv_ids))
    assert created.status_code == 201
    engineer_id = cast["engineer"].id

    login_as(client, cast["admin"])
    usage = client.get(f"/api/v1/users/{engineer_id}/usage").get_json()
    assert usage["deletable"] is False and usage["reference_total"] > 0
    assert any(k.startswith("change_request.") for k in usage["references"])
    refused = _delete(client, engineer_id)
    assert (
        refused.status_code == 409
        and "Deactivate the account instead" in refused.get_json()["message"]
    )
    with app.app_context():
        assert db.session.get(User, engineer_id) is not None

    deactivated = client.patch(f"/api/v1/users/{engineer_id}", json={"is_active": False})
    assert deactivated.status_code == 200 and deactivated.get_json()["is_active"] is False
    client.post("/api/v1/auth/logout")
    login = client.post(
        "/api/v1/auth/login",
        json={"username": cast["engineer"].username, "password": PASSWORD},
    )
    assert login.status_code in (401, 403)  # the account cannot sign in any more


def test_a_deactivated_account_can_be_activated_again(client, cast):
    login_as(client, cast["admin"])
    viewer_id = cast["viewer"].id
    client.patch(f"/api/v1/users/{viewer_id}", json={"is_active": False})
    assert client.patch(f"/api/v1/users/{viewer_id}", json={"is_active": True}).get_json()[
        "is_active"
    ]


def test_deleting_needs_the_administrators_password_and_an_administrator(client, cast):
    login_as(client, cast["admin"])
    user_id = _new_user(client)
    missing = _delete(client, user_id, password=None)
    assert missing.status_code == 403 and missing.get_json()["error"] == "step_up_required"
    wrong = _delete(client, user_id, password="not the password at all")
    assert wrong.status_code == 403 and wrong.get_json()["error"] == "step_up_failed"
    for who in ("stcd_owner", "chief_engineer", "reviewer", "engineer", "viewer"):
        login_as(client, cast[who])
        assert _delete(client, user_id).status_code == 403, who
    login_as(client, cast["admin"])
    assert client.get(f"/api/v1/users/{user_id}").status_code == 200  # still there
    assert _delete(client, user_id).status_code == 204


def test_nobody_deletes_their_own_account(client, cast):
    login_as(client, cast["admin"])
    refused = _delete(client, cast["admin"].id)
    assert refused.status_code == 403 and "own account" in refused.get_json()["message"]
    assert _delete(client, 99999).status_code == 404


def test_usage_is_open_to_the_user_list_roles_only(client, cast):
    target = cast["viewer"].id
    for who, allowed in (("stcd_owner", True), ("engineer", False), ("viewer", False)):
        login_as(client, cast[who])
        assert (client.get(f"/api/v1/users/{target}/usage").status_code == 200) is allowed, who


# ------------------------------------------------------------------------------ screens
def test_the_user_list_offers_view_edit_deactivate_and_delete_to_an_administrator(client, cast):
    login_as(client, cast["admin"])
    page = client.get("/admin/users").get_data(as_text=True)
    assert page.count(">View</a>") >= 7 and "Deactivate</button>" in page
    assert "Edit</summary>" in page and ">Delete</a>" in page
    assert f'href="/admin/users/{cast["viewer"].id}#delete"' in page


def test_the_stcd_owner_sees_view_and_set_role_but_no_delete_or_deactivate(client, cast):
    login_as(client, cast["stcd_owner"])
    page = client.get("/admin/users").get_data(as_text=True)
    assert ">View</a>" in page and "Set role" in page
    assert "Deactivate</button>" not in page and ">Delete</a>" not in page
    detail = client.get(f"/admin/users/{cast['viewer'].id}").get_data(as_text=True)
    assert "Set role" in detail and "Delete user" not in detail
    assert (
        client.post(f"/admin/users/{cast['viewer'].id}/active", data={"active": "0"}).status_code
        == 403
    )
    assert client.post(f"/admin/users/{cast['viewer'].id}/delete", data={}).status_code == 403


def test_the_detail_page_shows_history_and_the_buttons_follow_it(client, cast, wcnv_ids):
    login_as(client, cast["admin"])
    unused = _new_user(client, "unused")
    page = client.get(f"/admin/users/{unused}").get_data(as_text=True)
    assert "never been used" in page and "Delete user" in page and "Deactivate</button>" in page

    login_as(client, cast["engineer"])
    client.post("/api/v1/status-codes", json=valid_payload(*wcnv_ids))
    login_as(client, cast["admin"])
    used = client.get(f"/admin/users/{cast['engineer'].id}").get_data(as_text=True)
    assert "change_request.requested_by" in used and "Delete user" not in used
    assert "cannot be deleted" in used or "Not possible" in used


def test_the_buttons_deactivate_activate_and_delete_through_the_screens(app, client, cast):
    login_as(client, cast["admin"])
    user_id = _new_user(client, "screens")
    off = client.post(f"/admin/users/{user_id}/active", data={"active": "0"}, follow_redirects=True)
    assert "User deactivated." in off.get_data(as_text=True)
    on = client.post(f"/admin/users/{user_id}/active", data={"active": "1"}, follow_redirects=True)
    assert "User activated." in on.get_data(as_text=True)
    wrong = client.post(
        f"/admin/users/{user_id}/delete",
        data={"current_password": "wrong password here"},
        follow_redirects=True,
    )
    assert "User deleted." not in wrong.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(User, user_id) is not None  # a wrong password deletes nothing
    done = client.post(
        f"/admin/users/{user_id}/delete", data={"current_password": PASSWORD}, follow_redirects=True
    )
    assert "User deleted." in done.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(User, user_id) is None

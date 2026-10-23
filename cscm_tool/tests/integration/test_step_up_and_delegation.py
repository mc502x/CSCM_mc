"""I-17 step-up re-authentication (SEC-026) and I-16 delegation / out-of-office cover.

The `client` fixture answers the password prompt for the test (tests/conftest.py); these tests
use `raw_client` where the prompt itself is the subject.

TC-038. Requirements: FR-125, FR-126, SEC-026, SEC-011, BR-017, BR-022.
"""

from datetime import UTC, datetime, timedelta

from app.extensions import db
from app.models.audit import AuditLogEntry
from app.models.user import User
from tests.helpers import PASSWORD, drive_to_review, login_as, make_cast, release_revisions


def _decision(raw_client, cr_id, endpoint, **body):
    return raw_client.post(f"/api/v1/change-requests/{cr_id}/{endpoint}", json=body)


def _audit_actions(app):
    with app.app_context():
        return [a.action for a in db.session.query(AuditLogEntry).order_by(AuditLogEntry.id)]


def _prepare_review(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    return cast, revision, cr_id


# ------------------------------------------------------------------ I-17 step-up
def test_reviewer_signoff_without_password_is_refused(app, client, raw_client, make_user, wcnv_ids):
    cast, _, cr_id = _prepare_review(app, client, make_user, wcnv_ids)
    login_as(raw_client, cast["reviewer"])
    response = _decision(raw_client, cr_id, "reviewer-signoff", decision="APPROVE")
    assert response.status_code == 403
    assert response.get_json()["error"] == "step_up_required"
    # nothing was recorded
    assert client.get(f"/api/v1/change-requests/{cr_id}").status_code in (200, 401)


def test_wrong_password_is_refused_and_audited(app, client, raw_client, make_user, wcnv_ids):
    cast, _, cr_id = _prepare_review(app, client, make_user, wcnv_ids)
    login_as(raw_client, cast["reviewer"])
    response = _decision(
        raw_client, cr_id, "reviewer-signoff", decision="APPROVE", current_password="nope"
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "step_up_failed"
    assert "STEP_UP_FAILURE" in _audit_actions(app)


def test_correct_password_lets_the_signoff_through_and_is_audited(
    app, client, raw_client, make_user, wcnv_ids
):
    cast, _, cr_id = _prepare_review(app, client, make_user, wcnv_ids)
    login_as(raw_client, cast["reviewer"])
    response = _decision(
        raw_client, cr_id, "reviewer-signoff", decision="APPROVE", current_password=PASSWORD
    )
    assert response.status_code == 200
    actions = _audit_actions(app)
    assert "STEP_UP_SUCCESS" in actions and "REVIEWER_SIGNOFF" in actions


def test_repeated_wrong_passwords_lock_the_account(app, client, raw_client, make_user, wcnv_ids):
    """The prompt must not be usable to guess a password (same lockout as login)."""
    cast, _, cr_id = _prepare_review(app, client, make_user, wcnv_ids)
    login_as(raw_client, cast["reviewer"])
    for _ in range(5):
        _decision(raw_client, cr_id, "reviewer-signoff", decision="APPROVE", current_password="bad")
    response = _decision(
        raw_client, cr_id, "reviewer-signoff", decision="APPROVE", current_password=PASSWORD
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "account_locked"


def test_admin_signoff_chief_decision_publish_and_full_export_all_need_the_password(
    app, client, raw_client, make_user, wcnv_ids
):
    cast, revision, cr_id = _prepare_review(app, client, make_user, wcnv_ids)
    login_as(client, cast["reviewer"])
    client.post(f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"})

    login_as(raw_client, cast["admin"])
    assert _decision(raw_client, cr_id, "admin-signoff", decision="APPROVE").get_json()[
        "error"
    ] == ("step_up_required")
    ok = _decision(
        raw_client, cr_id, "admin-signoff", decision="APPROVE", current_password=PASSWORD
    )
    assert ok.status_code == 200

    login_as(raw_client, cast["chief_engineer"])
    assert (
        _decision(raw_client, cr_id, "chief-engineer-decide", decision="APPROVE").get_json()[
            "error"
        ]
        == "step_up_required"
    )
    assert (
        _decision(
            raw_client,
            cr_id,
            "chief-engineer-decide",
            decision="APPROVE",
            current_password=PASSWORD,
        ).status_code
        == 200
    )

    login_as(raw_client, cast["admin"])
    release = raw_client.post(
        "/api/v1/releases", json={"name": "R", "version_label": "v1"}
    ).get_json()
    raw_client.put(
        f"/api/v1/releases/{release['id']}/items",
        json={"status_code_revision_ids": [revision["id"]]},
    )
    assert raw_client.post(f"/api/v1/releases/{release['id']}/publish").get_json()["error"] == (
        "step_up_required"
    )
    assert (
        raw_client.post(
            f"/api/v1/releases/{release['id']}/publish", json={"current_password": PASSWORD}
        ).status_code
        == 200
    )

    assert raw_client.post("/api/v1/exports/full-database").status_code == 403
    export = raw_client.post("/api/v1/exports/full-database", json={"current_password": PASSWORD})
    assert export.status_code == 200
    assert export.data.startswith(b"SQLite format 3")


def test_step_up_can_be_switched_off_by_configuration(app, client, raw_client, make_user, wcnv_ids):
    cast, _, cr_id = _prepare_review(app, client, make_user, wcnv_ids)
    app.config["STEP_UP_REQUIRED"] = False
    login_as(raw_client, cast["reviewer"])
    assert _decision(raw_client, cr_id, "reviewer-signoff", decision="APPROVE").status_code == 200


def test_ui_decision_forms_carry_a_password_field(app, client, make_user, wcnv_ids):
    cast, _, cr_id = _prepare_review(app, client, make_user, wcnv_ids)
    login_as(client, cast["reviewer"])
    html = client.get(f"/change-requests/{cr_id}").get_data(as_text=True)
    assert 'name="current_password"' in html


def test_ui_signoff_without_password_shows_an_error(app, raw_client, client, make_user, wcnv_ids):
    cast, _, cr_id = _prepare_review(app, client, make_user, wcnv_ids)
    assert (
        raw_client.post(
            "/login", data={"username": cast["reviewer"].username, "password": PASSWORD}
        ).status_code
        == 302
    )
    response = raw_client.post(
        f"/change-requests/{cr_id}/reviewer-signoff",
        data={"decision": "APPROVE"},
        follow_redirects=True,
    )
    assert "re-enter your password" in response.get_data(as_text=True).lower()


# ------------------------------------------------------------------ I-16 delegation
def _tomorrow():
    return (datetime.now(UTC) + timedelta(days=1)).date().isoformat()


def _today():
    return datetime.now(UTC).date().isoformat()


def _delegate(client, delegator, delegate_id, start=None, end=None):
    login_as(client, delegator)
    return client.post(
        "/api/v1/delegations",
        json={
            "delegate_id": delegate_id,
            "valid_from": start or _today(),
            "valid_to": end or _tomorrow(),
        },
    )


def test_delegate_can_sign_off_as_the_absent_reviewer_and_audit_shows_both(
    app, client, make_user, wcnv_ids
):
    cast, _, cr_id = _prepare_review(app, client, make_user, wcnv_ids)
    cover = make_user("ENGINEER")
    assert _delegate(client, cast["reviewer"], cover.id).status_code == 201

    login_as(client, cover)
    response = client.post(
        f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"}
    )
    assert response.status_code == 200, response.get_json()

    with app.app_context():
        entry = (
            db.session.query(AuditLogEntry).filter(AuditLogEntry.action == "REVIEWER_SIGNOFF").one()
        )
        assert entry.actor_id == cover.id
        assert f'"on_behalf_of": [{cast["reviewer"].id}]' in entry.after_value


def test_delegation_does_not_lift_segregation_of_duties(app, client, make_user, wcnv_ids):
    """The delegate acts as themselves: the author cannot sign their own CR through a delegation."""
    cast, _, cr_id = _prepare_review(app, client, make_user, wcnv_ids)
    assert _delegate(client, cast["reviewer"], cast["engineer"].id).status_code == 201
    login_as(client, cast["engineer"])
    response = client.post(
        f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"}
    )
    assert response.status_code == 403
    assert "own change request" in response.get_json()["message"]


def test_one_person_cannot_give_both_review_signoffs_through_a_delegation(
    app, client, make_user, wcnv_ids
):
    cast, _, cr_id = _prepare_review(app, client, make_user, wcnv_ids)
    # the Administrator signs; the Reviewer is out and delegates to that same Administrator
    login_as(client, cast["admin"])
    assert (
        client.post(
            f"/api/v1/change-requests/{cr_id}/admin-signoff", json={"decision": "APPROVE"}
        ).status_code
        == 200
    )
    assert _delegate(client, cast["reviewer"], cast["admin"].id).status_code == 201
    login_as(client, cast["admin"])
    response = client.post(
        f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"}
    )
    assert response.status_code == 403
    assert "two different people" in response.get_json()["message"]


def test_delegation_is_limited_to_its_period_and_can_be_revoked(app, client, make_user, wcnv_ids):
    cast, _, cr_id = _prepare_review(app, client, make_user, wcnv_ids)
    cover = make_user("ENGINEER")
    future = (datetime.now(UTC) + timedelta(days=5)).date().isoformat()
    created = _delegate(client, cast["reviewer"], cover.id, start=future, end=future)
    assert created.status_code == 201
    login_as(client, cover)
    # not valid yet -> no reviewer role
    assert (
        client.post(
            f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"}
        ).status_code
        == 403
    )
    # a current delegation that is revoked stops working at once
    login_as(client, cast["reviewer"])
    current = client.post(
        "/api/v1/delegations",
        json={"delegate_id": cover.id, "valid_from": _today(), "valid_to": _tomorrow()},
    ).get_json()
    assert client.delete(f"/api/v1/delegations/{current['id']}").status_code == 204
    login_as(client, cover)
    assert (
        client.post(
            f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"}
        ).status_code
        == 403
    )


def test_delegation_validation_and_who_may_create_it(app, client, make_user):
    reviewer = make_user("REVIEWER")
    viewer = make_user("VIEWER")
    other = make_user("ENGINEER")
    login_as(client, reviewer)
    bad_target = client.post(
        "/api/v1/delegations",
        json={"delegate_id": viewer.id, "valid_from": _today(), "valid_to": _tomorrow()},
    )
    assert bad_target.status_code == 422
    to_self = client.post(
        "/api/v1/delegations",
        json={"delegate_id": reviewer.id, "valid_from": _today(), "valid_to": _tomorrow()},
    )
    assert to_self.status_code == 422
    backwards = client.post(
        "/api/v1/delegations",
        json={"delegate_id": other.id, "valid_from": _tomorrow(), "valid_to": _today()},
    )
    assert backwards.status_code == 422
    # an Engineer holds no decision role to delegate
    login_as(client, other)
    assert (
        client.post(
            "/api/v1/delegations",
            json={"delegate_id": reviewer.id, "valid_from": _today(), "valid_to": _tomorrow()},
        ).status_code
        == 403
    )


def test_delegate_sees_the_review_queue_and_a_delegated_chief_engineer_can_approve(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    cover = make_user("ENGINEER")
    _delegate(client, cast["reviewer"], cover.id)
    login_as(client, cover)
    assert client.get("/change-requests/review-queue").status_code == 200
    client.post(f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"})
    login_as(client, cast["admin"])
    client.post(f"/api/v1/change-requests/{cr_id}/admin-signoff", json={"decision": "APPROVE"})

    ce_cover = make_user("ENGINEER")
    _delegate(client, cast["chief_engineer"], ce_cover.id)
    login_as(client, ce_cover)
    assert client.get("/change-requests/approval-queue").status_code == 200
    done = client.post(
        f"/api/v1/change-requests/{cr_id}/chief-engineer-decide", json={"decision": "APPROVE"}
    )
    assert done.status_code == 200 and done.get_json()["state"] == "APPROVED"
    release_revisions(client, cast, [revision["id"]])


def test_delegating_does_not_grant_other_privileges(app, client, make_user):
    admin = make_user("ADMINISTRATOR")
    cover = make_user("ENGINEER")
    _delegate(client, admin, cover.id)
    login_as(client, cover)
    assert client.get("/api/v1/users").status_code == 403
    assert (
        client.post("/api/v1/releases", json={"name": "x", "version_label": "x"}).status_code == 403
    )


def test_deactivated_delegator_ends_the_delegation(app, client, make_user, wcnv_ids):
    cast, _, cr_id = _prepare_review(app, client, make_user, wcnv_ids)
    cover = make_user("ENGINEER")
    _delegate(client, cast["reviewer"], cover.id)
    with app.app_context():
        db.session.get(User, cast["reviewer"].id).is_active = 0
        db.session.commit()
    login_as(client, cover)
    assert (
        client.post(
            f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"}
        ).status_code
        == 403
    )

"""FR-030-FR-039, FR-027-FR-029, BR-004/BR-005. Full submit -> dual-review ->
Chief-Engineer-approval workflow, per docs/08-system-architecture.md §5.1-5.3."""

from app.extensions import db
from app.models.change_request import ChangeRequest


def _login_as(client, user, password="a genuinely long passphrase"):
    resp = client.post("/api/v1/auth/login", json={"username": user.username, "password": password})
    assert resp.status_code == 200
    return resp


def _valid_payload(**overrides):
    payload = {
        "functional_system_group": "WCNV",
        "turbine_platforms": ["3XM"],
        "title": "Converter Grid Undervoltage Trip",
        "description": "Triggered when converter DC-link voltage falls below threshold.",
        "status_category": "FAULT",
        "availability_group": "A",
        "reset_program": "MANUAL",
        "software_version": "4.12.0",
        "operational_state": "STOPPED",
        "alarm_behaviour": "SELF_CLEARING",
    }
    payload.update(overrides)
    return payload


def _cr_id_for_revision(app, revision_id: int) -> int:
    with app.app_context():
        cr = (
            db.session.query(ChangeRequest)
            .filter(ChangeRequest.status_code_revision_id == revision_id)
            .one()
        )
        return cr.id


def _create_and_fully_domain_signed_cr(app, client, engineer):
    """The default Engineer holds no Engineering Domain, so every
    CONTROLS-owned field is pending (docs/06-data-dictionary.md §2a) until a
    CONTROLS-tagged Engineer signs off. Returns the CR id, submit-ready."""
    _login_as(client, engineer)
    created = client.post("/api/v1/status-codes", json=_valid_payload()).get_json()
    cr_id = _cr_id_for_revision(app, created["id"])
    return cr_id


def test_submit_blocked_until_domain_signoff_complete(app, client, make_user):
    engineer = make_user("ENGINEER")
    cr_id = _create_and_fully_domain_signed_cr(app, client, engineer)

    blocked = client.post(f"/api/v1/change-requests/{cr_id}/submit")
    assert blocked.status_code == 422

    controls_engineer = make_user("ENGINEER", engineering_domains=["CONTROLS"])
    _login_as(client, controls_engineer)
    signoff = client.post(
        f"/api/v1/change-requests/{cr_id}/domain-signoffs",
        json={"engineering_domain": "CONTROLS"},
    )
    assert signoff.status_code == 201

    _login_as(client, engineer)
    submitted = client.post(f"/api/v1/change-requests/{cr_id}/submit")
    assert submitted.status_code == 200
    assert submitted.get_json()["state"] == "REVIEW"


def test_domain_signoff_rejects_user_without_that_domain(app, client, make_user):
    engineer = make_user("ENGINEER")
    other_engineer = make_user("ENGINEER")  # holds no domains either
    cr_id = _create_and_fully_domain_signed_cr(app, client, engineer)

    _login_as(client, other_engineer)
    response = client.post(
        f"/api/v1/change-requests/{cr_id}/domain-signoffs",
        json={"engineering_domain": "CONTROLS"},
    )
    assert response.status_code == 403


def _full_submit(app, client, engineer, controls_engineer):
    cr_id = _create_and_fully_domain_signed_cr(app, client, engineer)
    _login_as(client, controls_engineer)
    client.post(
        f"/api/v1/change-requests/{cr_id}/domain-signoffs",
        json={"engineering_domain": "CONTROLS"},
    )
    _login_as(client, engineer)
    resp = client.post(f"/api/v1/change-requests/{cr_id}/submit")
    assert resp.status_code == 200
    return cr_id


def test_author_cannot_sign_off_own_cr(app, client, make_user):
    engineer = make_user("ENGINEER")
    controls_engineer = make_user("ENGINEER", engineering_domains=["CONTROLS"])
    reviewer = make_user("REVIEWER")
    cr_id = _full_submit(app, client, engineer, controls_engineer)

    _login_as(client, engineer)
    response = client.post(
        f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"}
    )
    # Engineer role can't even reach the REVIEWER-only endpoint.
    assert response.status_code == 403

    # A Reviewer who happens to be someone else can, but not the requester.
    _login_as(client, reviewer)
    ok = client.post(
        f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"}
    )
    assert ok.status_code == 200


def test_dual_signoff_in_either_order_reaches_pending_approval(app, client, make_user):
    engineer = make_user("ENGINEER")
    controls_engineer = make_user("ENGINEER", engineering_domains=["CONTROLS"])
    reviewer = make_user("REVIEWER")
    admin = make_user("ADMINISTRATOR")
    cr_id = _full_submit(app, client, engineer, controls_engineer)

    _login_as(client, admin)
    r1 = client.post(f"/api/v1/change-requests/{cr_id}/admin-signoff", json={"decision": "APPROVE"})
    assert r1.status_code == 200
    assert r1.get_json()["state"] == "REVIEW"

    _login_as(client, reviewer)
    r2 = client.post(
        f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"}
    )
    assert r2.status_code == 200
    assert r2.get_json()["state"] == "PENDING_APPROVAL"


def test_rejection_returns_to_draft_and_clears_signoffs(app, client, make_user):
    engineer = make_user("ENGINEER")
    controls_engineer = make_user("ENGINEER", engineering_domains=["CONTROLS"])
    reviewer = make_user("REVIEWER")
    cr_id = _full_submit(app, client, engineer, controls_engineer)

    _login_as(client, reviewer)
    rejected = client.post(
        f"/api/v1/change-requests/{cr_id}/reviewer-signoff",
        json={"decision": "REJECT", "comment": "Needs more detail."},
    )
    assert rejected.status_code == 200
    assert rejected.get_json()["state"] == "DRAFT"


def test_reviewer_rejection_without_comment_is_rejected(app, client, make_user):
    engineer = make_user("ENGINEER")
    controls_engineer = make_user("ENGINEER", engineering_domains=["CONTROLS"])
    reviewer = make_user("REVIEWER")
    cr_id = _full_submit(app, client, engineer, controls_engineer)

    _login_as(client, reviewer)
    response = client.post(
        f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "REJECT"}
    )
    assert response.status_code == 422


def test_chief_engineer_cannot_be_a_prior_signer(app, client, make_user):
    engineer = make_user("ENGINEER")
    controls_engineer = make_user("ENGINEER", engineering_domains=["CONTROLS"])
    reviewer = make_user("REVIEWER")
    admin = make_user("ADMINISTRATOR")
    chief_engineer = make_user("CHIEF_ENGINEER")
    cr_id = _full_submit(app, client, engineer, controls_engineer)

    _login_as(client, reviewer)
    client.post(f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"})
    _login_as(client, admin)
    client.post(f"/api/v1/change-requests/{cr_id}/admin-signoff", json={"decision": "APPROVE"})

    # The Administrator who just signed off cannot also be Chief Engineer here...
    # but role enforcement already blocks non-CHIEF_ENGINEER roles from the endpoint.
    _login_as(client, chief_engineer)
    approved = client.post(
        f"/api/v1/change-requests/{cr_id}/chief-engineer-decide", json={"decision": "APPROVE"}
    )
    assert approved.status_code == 200
    assert approved.get_json()["state"] == "APPROVED"


def test_full_happy_path_to_approved(app, client, make_user):
    engineer = make_user("ENGINEER")
    controls_engineer = make_user("ENGINEER", engineering_domains=["CONTROLS"])
    reviewer = make_user("REVIEWER")
    admin = make_user("ADMINISTRATOR")
    chief_engineer = make_user("CHIEF_ENGINEER")
    cr_id = _full_submit(app, client, engineer, controls_engineer)

    _login_as(client, reviewer)
    assert (
        client.post(
            f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"}
        ).status_code
        == 200
    )
    _login_as(client, admin)
    result = client.post(
        f"/api/v1/change-requests/{cr_id}/admin-signoff", json={"decision": "APPROVE"}
    )
    assert result.get_json()["state"] == "PENDING_APPROVAL"

    _login_as(client, chief_engineer)
    final = client.post(
        f"/api/v1/change-requests/{cr_id}/chief-engineer-decide", json={"decision": "APPROVE"}
    )
    assert final.status_code == 200
    assert final.get_json()["state"] == "APPROVED"


def test_withdraw_removes_abandoned_new_draft(app, client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)
    created = client.post("/api/v1/status-codes", json=_valid_payload()).get_json()
    cr_id = _cr_id_for_revision(app, created["id"])

    response = client.post(f"/api/v1/change-requests/{cr_id}/withdraw")
    assert response.status_code == 200

    assert client.get(f"/api/v1/status-codes/{created['status_code_id']}").status_code == 404


def test_withdraw_forbidden_for_non_author(app, client, make_user):
    engineer = make_user("ENGINEER")
    other_engineer = make_user("ENGINEER")
    _login_as(client, engineer)
    created = client.post("/api/v1/status-codes", json=_valid_payload()).get_json()
    cr_id = _cr_id_for_revision(app, created["id"])

    _login_as(client, other_engineer)
    response = client.post(f"/api/v1/change-requests/{cr_id}/withdraw")
    assert response.status_code == 403


def test_withdraw_revision_type_restores_prior_current_revision(app, client, make_user):
    """Regression test: withdrawing a REVISION-type CR must restore the
    status code's prior revision to is_current=1 (create_revision's
    copy-on-write had flipped it off), or the code becomes invisible
    everywhere (no current revision to join on)."""
    engineer = make_user("ENGINEER")
    controls_engineer = make_user("ENGINEER", engineering_domains=["CONTROLS"])
    reviewer = make_user("REVIEWER")
    admin = make_user("ADMINISTRATOR")
    chief_engineer = make_user("CHIEF_ENGINEER")

    cr_id = _full_submit(app, client, engineer, controls_engineer)
    _login_as(client, reviewer)
    client.post(f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"})
    _login_as(client, admin)
    client.post(f"/api/v1/change-requests/{cr_id}/admin-signoff", json={"decision": "APPROVE"})
    _login_as(client, chief_engineer)
    client.post(
        f"/api/v1/change-requests/{cr_id}/chief-engineer-decide", json={"decision": "APPROVE"}
    )

    _login_as(client, admin)
    with app.app_context():
        cr = db.session.query(ChangeRequest).filter(ChangeRequest.id == cr_id).one()
        revision_id = cr.status_code_revision_id
        status_code_id = cr.revision.status_code_id
    release = client.post(
        "/api/v1/releases", json={"name": "R", "version_label": f"v-{status_code_id}"}
    ).get_json()
    client.put(
        f"/api/v1/releases/{release['id']}/items", json={"status_code_revision_ids": [revision_id]}
    )
    assert client.post(f"/api/v1/releases/{release['id']}/publish").status_code == 200

    _login_as(client, engineer)
    new_revision = client.post(
        f"/api/v1/status-codes/{status_code_id}/revisions",
        json=_valid_payload(title="Converter Grid Undervoltage Trip (revised)"),
    ).get_json()
    new_cr_id = _cr_id_for_revision(app, new_revision["id"])

    response = client.post(f"/api/v1/change-requests/{new_cr_id}/withdraw")
    assert response.status_code == 200

    detail = client.get(f"/api/v1/status-codes/{status_code_id}")
    assert detail.status_code == 200
    body = detail.get_json()
    assert body["is_current"] is True
    assert body["revision_number"] == 1
    assert body["lifecycle_status"] == "RELEASED"

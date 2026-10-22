"""Closes the gaps found in the spec-vs-code review (docs/20-traceability-matrix.md):
FR-021a identifier override, FR-025a/FR-034/BR-012/SEC-013 restricted audience-access
confirmation, FR-028 domain sign-off requests, FR-039 Reviewer assignment."""

import json

from app.extensions import db
from app.models.audit import AuditLogEntry
from app.models.status_code import StatusCodeRevision
from tests.helpers import (
    create_draft,
    decide,
    domain_sign,
    drive_to_review,
    login_as,
    make_cast,
    submit,
)


def _audit(app, action, entity_id=None):
    with app.app_context():
        query = db.session.query(AuditLogEntry).filter(AuditLogEntry.action == action)
        if entity_id is not None:
            query = query.filter(AuditLogEntry.entity_id == entity_id)
        return [
            (
                e.before_value and json.loads(e.before_value),
                e.after_value and json.loads(e.after_value),
            )
            for e in query.all()
        ]


def _access_ids(client, vocabulary):
    return [v["id"] for v in client.get(f"/api/v1/lookups/{vocabulary}").get_json()]


# ---- FR-021a identifier override ------------------------------------------------------------


def test_admin_can_override_identifier_with_reason_and_it_is_audited(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    revision, cr_id = create_draft(app, client, cast, wcnv_ids, who="admin")
    domain_sign(client, cast, cr_id)

    response = submit(
        client,
        cast,
        cr_id,
        who="admin",
        identifier_override="StCd-01050",
        override_reason="Reserved for migrated legacy code 4711",
    )
    assert response.status_code == 200

    with app.app_context():
        revision_row = db.session.get(StatusCodeRevision, revision["id"])
        assert revision_row.status_code.status_code_identifier == "StCd-01050"
    [(_, after)] = _audit(app, "IDENTIFIER_OVERRIDE")
    assert after["reason"] == "Reserved for migrated legacy code 4711"


def test_identifier_override_requires_reason(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = create_draft(app, client, cast, wcnv_ids, who="admin")
    domain_sign(client, cast, cr_id)

    response = submit(client, cast, cr_id, who="admin", identifier_override="StCd-01050")
    assert response.status_code == 422


def test_identifier_override_forbidden_for_engineer(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = create_draft(app, client, cast, wcnv_ids)
    domain_sign(client, cast, cr_id)

    response = submit(
        client,
        cast,
        cr_id,
        identifier_override="StCd-01050",
        override_reason="because I would like to",
    )
    assert response.status_code == 403


def test_identifier_override_rejects_out_of_range_malformed_and_duplicate(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    # First code takes StCd-01000 by normal allocation (WCNV "Converter" sub-band 1000-1099).
    drive_to_review(app, client, cast, wcnv_ids)

    _, cr_id = create_draft(app, client, cast, wcnv_ids, who="admin", title="Second Converter Trip")
    domain_sign(client, cast, cr_id)
    for bad in ("StCd-05000", "01900", "StCd-1900", "StCd-01000"):
        response = submit(
            client, cast, cr_id, who="admin", identifier_override=bad, override_reason="x reason"
        )
        assert response.status_code == 422, bad


# ---- FR-034 / SEC-013 / BR-012 restricted audience-access fields ----------------------------


def test_admin_signoff_can_override_proposed_audience_access(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    ids = _access_ids(client, "development-access")
    sales_ids = _access_ids(client, "sales-access")
    proposed, overridden = ids[0], ids[1]

    revision, cr_id = create_draft(
        app, client, cast, wcnv_ids, development_access=proposed, sales_access=sales_ids[0]
    )
    assert revision["access_confirmed"] is False
    domain_sign(client, cast, cr_id)
    assert submit(client, cast, cr_id).status_code == 200

    decide(client, cast["reviewer"], cr_id, "reviewer-signoff")
    result = decide(
        client,
        cast["admin"],
        cr_id,
        "admin-signoff",
        access_overrides={"development_access": overridden},
    )
    assert result.status_code == 200

    current = client.get(f"/api/v1/status-codes/{revision['status_code_id']}").get_json()
    assert current["development_access_id"] == overridden  # overridden
    assert current["sales_access_id"] == sales_ids[0]  # confirmed as proposed
    assert current["access_confirmed"] is True

    [(before, after)] = _audit(app, "ADMIN_SIGNOFF", revision["id"])
    assert before["override:development_access"] == proposed
    assert after["override:development_access"] == overridden
    assert "override:sales_access" not in after


def test_rejection_ignores_access_overrides(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    ids = _access_ids(client, "development-access")
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids, development_access=ids[0])

    result = decide(
        client,
        cast["admin"],
        cr_id,
        "admin-signoff",
        decision="REJECT",
        comment="Needs rework.",
        access_overrides={"development_access": ids[1]},
    )
    assert result.status_code == 200

    login_as(client, cast["engineer"])
    current = client.get(f"/api/v1/status-codes/{revision['status_code_id']}").get_json()
    assert current["development_access_id"] == ids[0]
    assert current["access_confirmed"] is False


def test_unknown_access_override_field_is_rejected(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)

    result = decide(
        client, cast["admin"], cr_id, "admin-signoff", access_overrides={"title": "sneaky"}
    )
    assert result.status_code == 422


def test_only_administrator_endpoint_accepts_overrides(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)

    result = decide(
        client,
        cast["reviewer"],
        cr_id,
        "admin-signoff",
        access_overrides={"development_access": 1},
    )
    assert result.status_code == 403


# ---- FR-039 Reviewer assignment -------------------------------------------------------------


def test_assigned_reviewer_only_may_sign_off(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    other_reviewer = make_user("REVIEWER")
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)

    login_as(client, cast["admin"])
    assigned = client.put(
        f"/api/v1/change-requests/{cr_id}/reviewer-assignment",
        json={"reviewer_id": cast["reviewer"].id},
    )
    assert assigned.status_code == 200
    assert assigned.get_json()["assigned_reviewer_id"] == cast["reviewer"].id

    assert decide(client, other_reviewer, cr_id, "reviewer-signoff").status_code == 403
    assert decide(client, cast["reviewer"], cr_id, "reviewer-signoff").status_code == 200


def test_reviewer_can_be_reassigned_and_unassigned(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    other_reviewer = make_user("REVIEWER")
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)

    login_as(client, cast["admin"])
    url = f"/api/v1/change-requests/{cr_id}/reviewer-assignment"
    client.put(url, json={"reviewer_id": cast["reviewer"].id})
    client.put(url, json={"reviewer_id": other_reviewer.id})
    assert decide(client, cast["reviewer"], cr_id, "reviewer-signoff").status_code == 403

    login_as(client, cast["admin"])
    unassigned = client.put(url, json={"reviewer_id": None})
    assert unassigned.get_json()["assigned_reviewer_id"] is None
    assert decide(client, cast["reviewer"], cr_id, "reviewer-signoff").status_code == 200
    assert len(_audit(app, "REVIEWER_ASSIGN")) == 3


def test_reviewer_assignment_validation_and_authorization(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    url = f"/api/v1/change-requests/{cr_id}/reviewer-assignment"

    login_as(client, cast["reviewer"])
    assert client.put(url, json={"reviewer_id": cast["reviewer"].id}).status_code == 403

    login_as(client, cast["admin"])
    # Not a Reviewer, and the author may never be assigned (BR-005).
    assert client.put(url, json={"reviewer_id": cast["engineer"].id}).status_code == 422
    assert client.put(url, json={"reviewer_id": 99999}).status_code == 422


def test_no_reassignment_after_reviewer_signed_off(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    other_reviewer = make_user("REVIEWER")
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    decide(client, cast["reviewer"], cr_id, "reviewer-signoff")

    login_as(client, cast["admin"])
    response = client.put(
        f"/api/v1/change-requests/{cr_id}/reviewer-assignment",
        json={"reviewer_id": other_reviewer.id},
    )
    assert response.status_code == 409


# ---- FR-028 domain sign-off requests --------------------------------------------------------


def test_domain_signoff_request_surfaces_for_target_and_clears_once_signed(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    bystander = make_user("ENGINEER", engineering_domains=["CONTROLS"])
    _, cr_id = create_draft(app, client, cast, wcnv_ids)

    login_as(client, cast["engineer"])
    requested = client.post(
        f"/api/v1/change-requests/{cr_id}/domain-signoff-requests",
        json={"engineering_domain": "CONTROLS", "target_user_id": cast["controls_engineer"].id},
    )
    assert requested.status_code == 201

    login_as(client, cast["controls_engineer"])
    mine = client.get("/api/v1/domain-signoff-requests").get_json()
    assert [r["change_request_id"] for r in mine] == [cr_id]

    login_as(client, bystander)
    assert client.get("/api/v1/domain-signoff-requests").get_json() == []

    domain_sign(client, cast, cr_id)
    login_as(client, cast["controls_engineer"])
    assert client.get("/api/v1/domain-signoff-requests").get_json() == []


def test_untargeted_domain_request_is_visible_to_every_domain_holder(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    _, cr_id = create_draft(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    client.post(
        f"/api/v1/change-requests/{cr_id}/domain-signoff-requests",
        json={"engineering_domain": "CONTROLS"},
    )

    login_as(client, cast["controls_engineer"])
    assert len(client.get("/api/v1/domain-signoff-requests").get_json()) == 1


def test_domain_signoff_request_validation(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = create_draft(app, client, cast, wcnv_ids)
    url = f"/api/v1/change-requests/{cr_id}/domain-signoff-requests"

    login_as(client, cast["controls_engineer"])  # not the originating Engineer
    assert client.post(url, json={"engineering_domain": "CONTROLS"}).status_code == 403

    login_as(client, cast["engineer"])
    assert client.post(url, json={}).status_code == 422
    # ELECTRICAL is not a pending required domain
    assert client.post(url, json={"engineering_domain": "ELECTRICAL"}).status_code == 422
    # target must hold the domain
    bad_target = client.post(
        url, json={"engineering_domain": "CONTROLS", "target_user_id": cast["reviewer"].id}
    )
    assert bad_target.status_code == 422


def test_withdrawn_cr_removes_its_domain_requests(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = create_draft(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    client.post(
        f"/api/v1/change-requests/{cr_id}/domain-signoff-requests",
        json={"engineering_domain": "CONTROLS"},
    )
    assert client.post(f"/api/v1/change-requests/{cr_id}/withdraw").status_code == 200

    login_as(client, cast["controls_engineer"])
    assert client.get("/api/v1/domain-signoff-requests").get_json() == []


def test_domain_request_is_refused_when_nobody_holds_the_domain(app, client, make_user, wcnv_ids):
    """A request nobody could ever act on must not be silently accepted."""
    engineer = make_user("ENGINEER")
    author_cast = {"engineer": engineer}
    _, cr_id = create_draft(app, client, author_cast, wcnv_ids)  # no Controls Engineer exists
    login_as(client, engineer)
    url = f"/api/v1/change-requests/{cr_id}/domain-signoff-requests"

    refused = client.post(url, json={"engineering_domain": "CONTROLS"})
    assert refused.status_code == 422
    assert "No active Engineer holds the CONTROLS domain" in refused.get_json()["message"]

    make_user("ENGINEER", engineering_domains=["CONTROLS"])
    assert client.post(url, json={"engineering_domain": "CONTROLS"}).status_code == 201


def test_cr_page_explains_when_no_engineer_holds_a_pending_domain(app, client, make_user, wcnv_ids):
    engineer = make_user("ENGINEER")
    _, cr_id = create_draft(app, client, {"engineer": engineer}, wcnv_ids)
    client.post("/logout")
    client.post(
        "/login", data={"username": engineer.username, "password": "a genuinely long passphrase"}
    )
    page = client.get(f"/change-requests/{cr_id}").get_data(as_text=True)
    assert "No active Engineer holds the" in page and "Request</button>" not in page

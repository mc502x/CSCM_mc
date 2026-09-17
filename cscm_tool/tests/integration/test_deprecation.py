"""FR-050-FR-052, BR-006, docs/05-governance-handbook.md §5, §11."""

from datetime import UTC, datetime, timedelta

from app.auth.rate_limit import reset_for_testing
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


def _make_cast(make_user):
    return {
        "engineer": make_user("ENGINEER"),
        "controls_engineer": make_user("ENGINEER", engineering_domains=["CONTROLS"]),
        "reviewer": make_user("REVIEWER"),
        "admin": make_user("ADMINISTRATOR"),
        "chief_engineer": make_user("CHIEF_ENGINEER"),
    }


def _get_released_status_code(app, client, cast):
    """Drives a status code all the way to RELEASED via a full CR +
    Release-publish cycle, and returns its status_code_id."""
    _login_as(client, cast["engineer"])
    created = client.post("/api/v1/status-codes", json=_valid_payload()).get_json()
    status_code_id = created["status_code_id"]
    revision_id = created["id"]

    with app.app_context():
        cr_id = (
            db.session.query(ChangeRequest)
            .filter(ChangeRequest.status_code_revision_id == revision_id)
            .one()
            .id
        )

    _login_as(client, cast["controls_engineer"])
    client.post(
        f"/api/v1/change-requests/{cr_id}/domain-signoffs",
        json={"engineering_domain": "CONTROLS"},
    )
    _login_as(client, cast["engineer"])
    assert client.post(f"/api/v1/change-requests/{cr_id}/submit").status_code == 200

    _login_as(client, cast["reviewer"])
    client.post(f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"})
    _login_as(client, cast["admin"])
    client.post(f"/api/v1/change-requests/{cr_id}/admin-signoff", json={"decision": "APPROVE"})
    _login_as(client, cast["chief_engineer"])
    client.post(
        f"/api/v1/change-requests/{cr_id}/chief-engineer-decide", json={"decision": "APPROVE"}
    )

    _login_as(client, cast["admin"])
    release = client.post(
        "/api/v1/releases", json={"name": "R", "version_label": f"v-{status_code_id}"}
    ).get_json()
    client.put(
        f"/api/v1/releases/{release['id']}/items",
        json={"status_code_revision_ids": [revision_id]},
    )
    publish = client.post(f"/api/v1/releases/{release['id']}/publish")
    assert publish.status_code == 200

    return status_code_id


def test_second_revision_does_not_violate_current_uniqueness(app, client, make_user):
    """Regression test: create_revision must flip the old current revision's
    is_current flag off before inserting the new one, or
    ux_revision_current_per_code rejects the insert."""
    cast = _make_cast(make_user)
    status_code_id = _get_released_status_code(app, client, cast)

    _login_as(client, cast["engineer"])
    response = client.post(
        f"/api/v1/status-codes/{status_code_id}/revisions",
        json=_valid_payload(title="Converter Grid Undervoltage Trip (revised)"),
    )
    assert response.status_code == 201
    assert response.get_json()["is_current"] is True
    assert response.get_json()["revision_number"] == 2

    history = client.get(f"/api/v1/status-codes/{status_code_id}/revisions").get_json()
    current_flags = [r["is_current"] for r in history]
    assert current_flags.count(True) == 1


def test_deprecation_requires_released_state(client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)
    created = client.post("/api/v1/status-codes", json=_valid_payload()).get_json()

    response = client.post(
        f"/api/v1/status-codes/{created['status_code_id']}/deprecation-requests",
        json={"reason": "Superseded by revised undervoltage threshold logic."},
    )
    assert response.status_code == 409


def test_full_deprecation_cycle(app, client, make_user):
    cast = _make_cast(make_user)
    status_code_id = _get_released_status_code(app, client, cast)
    # Getting to RELEASED and then through the whole deprecation cycle adds
    # up to more login calls than the IP rate limit allows within one
    # 5-minute window (docs/11-security-architecture.md §5) — realistic in
    # production spread over time, but not from one test client "IP" in a
    # single test. These are two separate scenarios sharing setup.
    reset_for_testing()

    _login_as(client, cast["engineer"])
    dep = client.post(
        f"/api/v1/status-codes/{status_code_id}/deprecation-requests",
        json={"reason": "Superseded by revised undervoltage threshold logic."},
    )
    assert dep.status_code == 201
    dep_revision = dep.get_json()
    assert dep_revision["lifecycle_status"] == "DRAFT"
    assert dep_revision["revision_number"] == 2

    with app.app_context():
        cr_id = (
            db.session.query(ChangeRequest)
            .filter(ChangeRequest.status_code_revision_id == dep_revision["id"])
            .one()
            .id
        )

    _login_as(client, cast["controls_engineer"])
    client.post(
        f"/api/v1/change-requests/{cr_id}/domain-signoffs",
        json={"engineering_domain": "CONTROLS"},
    )
    _login_as(client, cast["engineer"])
    assert client.post(f"/api/v1/change-requests/{cr_id}/submit").status_code == 200

    _login_as(client, cast["reviewer"])
    client.post(f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"})
    _login_as(client, cast["admin"])
    client.post(f"/api/v1/change-requests/{cr_id}/admin-signoff", json={"decision": "APPROVE"})
    _login_as(client, cast["chief_engineer"])
    decide = client.post(
        f"/api/v1/change-requests/{cr_id}/chief-engineer-decide", json={"decision": "APPROVE"}
    )
    assert decide.status_code == 200

    final = client.get(f"/api/v1/status-codes/{status_code_id}")
    body = final.get_json()
    assert body["lifecycle_status"] == "DEPRECATED"
    assert body["deprecated_reason"] == "Superseded by revised undervoltage threshold logic."


def test_archive_blocked_before_retention_period_elapses(app, client, make_user):
    cast = _make_cast(make_user)
    status_code_id = _get_released_status_code(app, client, cast)

    # Directly move the revision to DEPRECATED with a DEPRECATE audit entry
    # timestamped "now" to isolate the retention check from the full CR cycle.
    with app.app_context():
        from app.models.status_code import StatusCodeRevision
        from app.services.audit_service import AuditService

        revision = (
            db.session.query(StatusCodeRevision)
            .filter(
                StatusCodeRevision.status_code_id == status_code_id,
                StatusCodeRevision.is_current == 1,
            )
            .one()
        )
        revision.lifecycle_status = "DEPRECATED"
        revision.deprecated_reason = "Test deprecation."
        AuditService.log("StatusCodeRevision", revision.id, "DEPRECATE", actor=None)
        db.session.commit()

    _login_as(client, cast["admin"])
    response = client.post(f"/api/v1/status-codes/{status_code_id}/archive")
    # Retention-not-elapsed is a business-rule failure (DomainError -> 422),
    # distinct from "not Deprecated at all" (InvalidTransitionError -> 409).
    assert response.status_code == 422


def test_archive_succeeds_after_retention_period(app, client, make_user):
    cast = _make_cast(make_user)
    status_code_id = _get_released_status_code(app, client, cast)

    with app.app_context():
        from app.models.status_code import StatusCodeRevision
        from app.services.audit_service import AuditService
        from app.utils import format_iso

        revision = (
            db.session.query(StatusCodeRevision)
            .filter(
                StatusCodeRevision.status_code_id == status_code_id,
                StatusCodeRevision.is_current == 1,
            )
            .one()
        )
        revision.lifecycle_status = "DEPRECATED"
        revision.deprecated_reason = "Test deprecation."
        entry = AuditService.log("StatusCodeRevision", revision.id, "DEPRECATE", actor=None)
        entry.occurred_at = format_iso(datetime.now(UTC) - timedelta(days=200))
        db.session.commit()

    _login_as(client, cast["admin"])
    response = client.post(f"/api/v1/status-codes/{status_code_id}/archive")
    assert response.status_code == 200
    assert response.get_json()["lifecycle_status"] == "ARCHIVED"


def test_reinstate_deprecated_code(app, client, make_user):
    cast = _make_cast(make_user)
    status_code_id = _get_released_status_code(app, client, cast)

    with app.app_context():
        from app.models.status_code import StatusCodeRevision

        revision = (
            db.session.query(StatusCodeRevision)
            .filter(
                StatusCodeRevision.status_code_id == status_code_id,
                StatusCodeRevision.is_current == 1,
            )
            .one()
        )
        revision.lifecycle_status = "DEPRECATED"
        revision.deprecated_reason = "Test deprecation."
        db.session.commit()

    _login_as(client, cast["admin"])
    response = client.post(
        f"/api/v1/status-codes/{status_code_id}/reinstate",
        json={"reason": "Deprecation was made in error; threshold logic still valid."},
    )
    assert response.status_code == 200
    assert response.get_json()["lifecycle_status"] == "RELEASED"


def test_non_admin_cannot_archive_or_reinstate(client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)
    assert client.post("/api/v1/status-codes/1/archive").status_code == 403
    assert client.post("/api/v1/status-codes/1/reinstate", json={"reason": "x"}).status_code == 403

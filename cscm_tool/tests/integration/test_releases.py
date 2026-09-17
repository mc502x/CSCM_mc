"""FR-040-FR-048, BR-006-BR-008."""

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


def _approve_a_status_code(
    app, client, engineer, controls_engineer, reviewer, admin, chief_engineer
):
    """Drives one status code all the way to APPROVED and returns its
    current revision id."""
    _login_as(client, engineer)
    created = client.post("/api/v1/status-codes", json=_valid_payload()).get_json()
    revision_id = created["id"]

    with app.app_context():
        cr_id = (
            db.session.query(ChangeRequest)
            .filter(ChangeRequest.status_code_revision_id == revision_id)
            .one()
            .id
        )

    _login_as(client, controls_engineer)
    client.post(
        f"/api/v1/change-requests/{cr_id}/domain-signoffs",
        json={"engineering_domain": "CONTROLS"},
    )

    _login_as(client, engineer)
    assert client.post(f"/api/v1/change-requests/{cr_id}/submit").status_code == 200

    _login_as(client, reviewer)
    client.post(f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"})
    _login_as(client, admin)
    client.post(f"/api/v1/change-requests/{cr_id}/admin-signoff", json={"decision": "APPROVE"})
    _login_as(client, chief_engineer)
    result = client.post(
        f"/api/v1/change-requests/{cr_id}/chief-engineer-decide", json={"decision": "APPROVE"}
    )
    assert result.get_json()["state"] == "APPROVED"
    return revision_id


def _make_cast(make_user):
    return {
        "engineer": make_user("ENGINEER"),
        "controls_engineer": make_user("ENGINEER", engineering_domains=["CONTROLS"]),
        "reviewer": make_user("REVIEWER"),
        "admin": make_user("ADMINISTRATOR"),
        "chief_engineer": make_user("CHIEF_ENGINEER"),
    }


def test_non_admin_cannot_create_release(client, make_user):
    cast = _make_cast(make_user)
    _login_as(client, cast["engineer"])
    response = client.post(
        "/api/v1/releases", json={"name": "Q1 Release", "version_label": "2026.1"}
    )
    assert response.status_code == 403


def test_full_release_lifecycle(app, client, make_user):
    cast = _make_cast(make_user)
    revision_id = _approve_a_status_code(app, client, **cast)

    _login_as(client, cast["admin"])
    release = client.post(
        "/api/v1/releases",
        json={
            "name": "Q1 Release",
            "version_label": "2026.1",
            "scope_filter": {"functional_system_group": "WCNV"},
        },
    ).get_json()
    assert release["status"] == "BUILDING"

    candidates = client.get(f"/api/v1/releases/{release['id']}/candidates").get_json()
    assert any(c["id"] == revision_id for c in candidates)

    set_items = client.put(
        f"/api/v1/releases/{release['id']}/items",
        json={"status_code_revision_ids": [revision_id]},
    )
    assert set_items.status_code == 200
    assert set_items.get_json()["item_count"] == 1

    publish = client.post(f"/api/v1/releases/{release['id']}/publish")
    assert publish.status_code == 200
    assert publish.get_json()["status"] == "PUBLISHED"

    released_revision = client.get("/api/v1/status-codes").get_json()["items"][0]
    assert released_revision["lifecycle_status"] == "RELEASED"
    assert released_revision["effective_date"] is not None


def test_cannot_change_items_after_publish(app, client, make_user):
    cast = _make_cast(make_user)
    revision_id = _approve_a_status_code(app, client, **cast)

    _login_as(client, cast["admin"])
    release = client.post(
        "/api/v1/releases", json={"name": "Q1 Release", "version_label": "2026.1"}
    ).get_json()
    client.put(
        f"/api/v1/releases/{release['id']}/items",
        json={"status_code_revision_ids": [revision_id]},
    )
    client.post(f"/api/v1/releases/{release['id']}/publish")

    response = client.put(
        f"/api/v1/releases/{release['id']}/items",
        json={"status_code_revision_ids": []},
    )
    assert response.status_code == 409


def test_sandbox_revision_rejected_from_release_items(client, make_user):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)
    sandbox = client.post("/api/v1/status-codes", json=_valid_payload(is_sandbox=True)).get_json()

    release = client.post(
        "/api/v1/releases", json={"name": "Sandbox Test", "version_label": "2026.9"}
    ).get_json()
    response = client.put(
        f"/api/v1/releases/{release['id']}/items",
        json={"status_code_revision_ids": [sandbox["id"]]},
    )
    assert response.status_code == 422


def test_csv_export_of_a_release(app, client, make_user):
    cast = _make_cast(make_user)
    revision_id = _approve_a_status_code(app, client, **cast)

    _login_as(client, cast["admin"])
    release = client.post(
        "/api/v1/releases", json={"name": "Export Test", "version_label": "2026.2"}
    ).get_json()
    client.put(
        f"/api/v1/releases/{release['id']}/items",
        json={"status_code_revision_ids": [revision_id]},
    )
    client.post(f"/api/v1/releases/{release['id']}/publish")

    response = client.get(f"/api/v1/releases/{release['id']}/export?format=csv")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert b"StCd-" in response.data


def test_full_database_export_requires_administrator(client, make_user):
    engineer = make_user("ENGINEER")
    admin = make_user("ADMINISTRATOR")

    _login_as(client, engineer)
    assert client.get("/api/v1/exports/full-database").status_code == 403

    _login_as(client, admin)
    response = client.get("/api/v1/exports/full-database")
    assert response.status_code == 200
    assert response.data[:16] == b"SQLite format 3\x00"

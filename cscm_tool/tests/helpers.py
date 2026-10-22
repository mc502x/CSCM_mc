"""Shared workflow drivers for integration tests. Logins reset the in-process
rate limiter first: a full lifecycle needs more logins than the per-IP limit
allows from one test-client "IP" within a window (docs/11-security-architecture.md
§5), which is a production safeguard, not something these tests exercise."""

from app.auth.rate_limit import reset_for_testing
from app.extensions import db
from app.models.change_request import ChangeRequest

PASSWORD = "a genuinely long passphrase"


def login_as(client, user, password=PASSWORD):
    reset_for_testing()
    resp = client.post("/api/v1/auth/login", json={"username": user.username, "password": password})
    assert resp.status_code == 200, resp.get_json()
    return resp


def valid_payload(group_id, subgroup_id, **overrides):
    payload = {
        "functional_system_group": group_id,
        "functional_subgroup": subgroup_id,
        "turbine_platforms": ["3XM"],
        "title": "Converter Grid Undervoltage Trip",
        "description": "Triggered when converter DC-link voltage falls below threshold.",
        "status_category": "ERROR",
        "available_group": 27,
        "set_delay": "10ms",
        "reset_delay": "2min",
    }
    payload.update(overrides)
    return payload


def cr_id_for_revision(app, revision_id: int) -> int:
    with app.app_context():
        return (
            db.session.query(ChangeRequest)
            .filter(ChangeRequest.status_code_revision_id == revision_id)
            .one()
            .id
        )


def make_cast(make_user):
    return {
        "engineer": make_user("ENGINEER"),
        "controls_engineer": make_user("ENGINEER", engineering_domains=["CONTROLS"]),
        "reviewer": make_user("REVIEWER"),
        "admin": make_user("ADMINISTRATOR"),
        "chief_engineer": make_user("CHIEF_ENGINEER"),
        "viewer": make_user("VIEWER"),
    }


def create_draft(app, client, cast, wcnv_ids, who="engineer", **overrides):
    """Creates a Draft as `who`; returns (revision_json, cr_id)."""
    login_as(client, cast[who])
    created = client.post("/api/v1/status-codes", json=valid_payload(*wcnv_ids, **overrides))
    assert created.status_code == 201, created.get_json()
    revision = created.get_json()
    return revision, cr_id_for_revision(app, revision["id"])


def domain_sign(client, cast, cr_id):
    login_as(client, cast["controls_engineer"])
    resp = client.post(
        f"/api/v1/change-requests/{cr_id}/domain-signoffs",
        json={"engineering_domain": "CONTROLS"},
    )
    assert resp.status_code == 201, resp.get_json()


def submit(client, cast, cr_id, who="engineer", **body):
    login_as(client, cast[who])
    return client.post(f"/api/v1/change-requests/{cr_id}/submit", json=body)


def decide(client, user, cr_id, endpoint, decision="APPROVE", **extra):
    login_as(client, user)
    return client.post(
        f"/api/v1/change-requests/{cr_id}/{endpoint}", json={"decision": decision, **extra}
    )


def drive_to_review(app, client, cast, wcnv_ids, **overrides):
    revision, cr_id = create_draft(app, client, cast, wcnv_ids, **overrides)
    domain_sign(client, cast, cr_id)
    assert submit(client, cast, cr_id).status_code == 200
    return revision, cr_id


def drive_to_approved(app, client, cast, wcnv_ids, **overrides):
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids, **overrides)
    assert decide(client, cast["reviewer"], cr_id, "reviewer-signoff").status_code == 200
    assert decide(client, cast["admin"], cr_id, "admin-signoff").status_code == 200
    final = decide(client, cast["chief_engineer"], cr_id, "chief-engineer-decide")
    assert final.get_json()["state"] == "APPROVED"
    return revision, cr_id


def release_revisions(client, cast, revision_ids, label="v1"):
    login_as(client, cast["admin"])
    release = client.post("/api/v1/releases", json={"name": "R", "version_label": label}).get_json()
    client.put(
        f"/api/v1/releases/{release['id']}/items", json={"status_code_revision_ids": revision_ids}
    )
    assert client.post(f"/api/v1/releases/{release['id']}/publish").status_code == 200
    return release["id"]

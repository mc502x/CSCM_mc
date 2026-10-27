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
        "stcd_owner": make_user("STCD_OWNER"),
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


# The mapping rows of the six programs in tests/fixtures/st (the titles read as the English version of
# the German names, so the glossary check is silent); the Hub numbers are the ones of the former
# numbering proposal 1.
_MAPPED_LEVELS_MC = {
    "development_access": "Department",
    "sales_access": "Sales",
    "tcc_access": "Telenotdienst",
    "service_access": "Service and Maintenance",
    "turbine_operator_package_access": "Preventive Maintenance",
    "grid_operator_access": "Covert",
    "service_partner_access": "Ext. Service Provider",
    "customer_access": "See only",
}
_MAPPED_LEVELS_HC = {
    "development_access": "See only",
    "sales_access": "See only",
    "tcc_access": "See only",
    "service_access": "See only",
    "turbine_operator_package_access": "Covert",
    "grid_operator_access": "Covert",
    "service_partner_access": "Covert",
    "customer_access": "See only",
}
ST_MAPPING = [
    # family, legacy, new, English title, group, node, type, up/down
    ("MC", 3000, 1000, "Converter not ready", "Converter", "WCNV", "ERROR", 0),
    ("MC", 3005, 1001, "Conv. fuse tripped", "Converter", "WCNV", "WARNING", 0),
    ("MC", 3010, 1002, "Converter communication fault", "Converter", "WCNV", "INFO", 1),
    ("HC", 14000, 12501, "Rotor overspeed", "Rotor", "WROT", "ERROR", 0),
    ("HC", 14005, 12502, "Rotor overspeed test", "Rotor", "WROT", "INFO", 0),
    ("HC", 14025, 12503, "Stop speed setpoint angle check", "Rotor", "WROT", "WARNING", 1),
]


def seed_st_mapping(status="APPROVED", **per_number):
    """Inserts the six mapping rows; `per_number={1000: {"status_type": None}}` changes a row."""
    from app.models.mapping import StatusCodeMapping
    from app.utils import utcnow_iso

    now = utcnow_iso()
    for family, legacy, new, title, group, node, kind, counter in ST_MAPPING:
        row = {
            "family": family,
            "legacy_number": legacy,
            "new_number": new,
            "description": title,
            "functional_group": group,
            "logical_node": node,
            "status_type": kind,
            "up_down_counter": counter,
            "status": status,
            "source": "test fixture",
            **(_MAPPED_LEVELS_MC if family == "MC" else _MAPPED_LEVELS_HC),
        }
        row.update(per_number.get(new, {}))
        db.session.add(StatusCodeMapping(created_at=now, updated_at=now, version=1, **row))
    db.session.commit()


def add_mapping_row(new_number, legacy_number=None, family="MC", **fields):
    """One more mapping row (approved, complete) for a program the test makes up."""
    from app.models.mapping import StatusCodeMapping
    from app.utils import utcnow_iso

    now = utcnow_iso()
    row = {
        "family": family,
        "legacy_number": legacy_number,
        "new_number": new_number,
        "description": "Made up test code",
        "functional_group": "Converter",
        "logical_node": "WCNV",
        "status_type": "ERROR",
        "up_down_counter": 0,
        "status": "APPROVED",
        "source": "test",
    }
    row.update(fields)
    db.session.add(StatusCodeMapping(created_at=now, updated_at=now, version=1, **row))
    db.session.commit()

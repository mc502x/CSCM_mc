"""FR-056, FR-070, FR-072, FR-073, NFR-006, TC-015, TC-015a: the audit trail
records every governed action exactly once and can never be altered."""

import io
import json
from collections import Counter

import pytest
from sqlalchemy.exc import DatabaseError

from app.extensions import db
from app.models.audit import AuditLogEntry
from tests.helpers import (
    drive_to_approved,
    login_as,
    make_cast,
    release_revisions,
    valid_payload,
)


def _actions(app):
    with app.app_context():
        return Counter(a for (a,) in db.session.query(AuditLogEntry.action).all())


def test_each_lifecycle_action_is_audited_exactly_once(app, client, make_user, wcnv_ids):
    """TC-015: one entry per state-changing action across the whole lifecycle."""
    cast = make_cast(make_user)
    revision, _cr_id = drive_to_approved(app, client, cast, wcnv_ids)
    release_revisions(client, cast, [revision["id"]])
    login_as(client, cast["admin"])
    client.get("/api/v1/exports/released?format=csv")

    counts = _actions(app)
    for action in (
        "CREATE",
        "DOMAIN_SIGNOFF",
        "SUBMIT_FOR_REVIEW",
        "REVIEWER_SIGNOFF",
        "ADMIN_SIGNOFF",
        "CHIEF_ENGINEER_APPROVE",
        "RELEASE_CREATE",
        "RELEASE_ITEMS_SET",
        "RELEASE_PUBLISH",
        "CATALOGUE_EXPORT",
    ):
        assert counts[action] == 1, (action, counts)
    # 6 users created in make_cast, none of them audited with an actor id of None being dropped
    assert counts["USER_CREATE"] == 6
    assert counts["LOGIN_SUCCESS"] >= 5


def test_sandbox_delete_keeps_full_snapshot_and_creation_entry(app, client, make_user, wcnv_ids):
    """TC-015a / FR-056 / FR-073."""
    cast = make_cast(make_user)
    login_as(client, cast["admin"])
    sandbox = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, is_sandbox=True)
    ).get_json()
    identifier = sandbox["status_code_identifier"]

    assert client.delete(f"/api/v1/status-codes/{sandbox['status_code_id']}").status_code == 204
    assert client.get(f"/api/v1/status-codes/{sandbox['status_code_id']}").status_code == 404

    with app.app_context():
        entries = (
            db.session.query(AuditLogEntry)
            .filter(AuditLogEntry.entity_id == sandbox["status_code_id"])
            .filter(AuditLogEntry.action.in_(("SANDBOX_CREATE", "SANDBOX_DELETE")))
            .all()
        )
        by_action = {e.action: e for e in entries}
        assert set(by_action) == {"SANDBOX_CREATE", "SANDBOX_DELETE"}  # FR-073
        snapshot = json.loads(by_action["SANDBOX_DELETE"].before_value)
        assert snapshot["status_code_identifier"] == identifier
        assert snapshot["functional_system_group"] == "WCNV"
        assert snapshot["revisions"][0]["title"] == "Converter Grid Undervoltage Trip"
        assert snapshot["revisions"][0]["turbine_platforms"] == ["3XM"]


def test_audit_log_entries_cannot_be_updated_or_deleted(app, client, make_user):
    """FR-072: append-only at the database layer, not just by omission."""
    make_user("ADMINISTRATOR")  # produces a USER_CREATE entry
    with app.app_context():
        entry = db.session.query(AuditLogEntry).first()
        assert entry is not None
        entry_id = entry.id

        with pytest.raises(DatabaseError, match="append-only"):
            db.session.execute(
                db.text("UPDATE audit_log_entry SET action = 'X' WHERE id = :i"), {"i": entry_id}
            )
        db.session.rollback()
        with pytest.raises(DatabaseError, match="append-only"):
            db.session.execute(
                db.text("DELETE FROM audit_log_entry WHERE id = :i"), {"i": entry_id}
            )
        db.session.rollback()
        assert db.session.get(AuditLogEntry, entry_id).action == "USER_CREATE"


def test_subgroup_creation_is_audited_as_subgroup_create(client, make_user, wcnv_ids, app):
    admin = make_user("ADMINISTRATOR")
    login_as(client, admin)
    response = client.post(
        "/api/v1/lookups/functional-subgroups",
        json={
            "code": "019xx",
            "label": "Converter Diagnostics",
            "functional_system_group": wcnv_ids[0],
            "sub_range_start": 1900,
            "sub_range_end": 1999,
        },
    )
    assert response.status_code == 201
    assert _actions(app)["SUBGROUP_CREATE"] == 1


def _csv(rows):
    import csv

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _import_row(**overrides):
    row = {
        "functional_system_group": "WCNV",
        "functional_subgroup": "010xx",
        "turbine_platforms": "3XM",
        "title": "Imported Converter Fault",
        "description": "Imported via CSV library import audit test.",
        "status_category": "ERROR",
        "available_group": "27",
        "set_delay": "10ms",
        "reset_delay": "2min",
    }
    row.update(overrides)
    return row


def test_import_lifecycle_is_audited(app, client, make_user):
    engineer = make_user("ENGINEER")
    login_as(client, engineer)
    response = client.post(
        "/api/v1/imports",
        data={
            "file": (
                io.BytesIO(_csv([_import_row(), _import_row(status_category="BOGUS")])),
                "lib.csv",
            )
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 202

    counts = _actions(app)
    assert counts["IMPORT_STARTED"] == 1
    assert counts["IMPORT_COMPLETED"] == 1
    assert counts["IMPORT_FAILED"] == 0
    with app.app_context():
        completed = (
            db.session.query(AuditLogEntry).filter(AuditLogEntry.action == "IMPORT_COMPLETED").one()
        )
        after = json.loads(completed.after_value)
        assert (after["row_count"], after["created_count"], after["error_count"]) == (2, 1, 1)


def test_unexpected_import_failure_marks_job_failed_and_is_audited(
    app, client, make_user, monkeypatch
):
    from app.models.import_job import ImportJob
    from app.services.status_code_service import StatusCodeService

    def boom(*args, **kwargs):
        raise RuntimeError("disk exploded")

    monkeypatch.setattr(StatusCodeService, "create_draft", staticmethod(boom))
    engineer = make_user("ENGINEER")
    login_as(client, engineer)
    client.application.config["PROPAGATE_EXCEPTIONS"] = False

    response = client.post(
        "/api/v1/imports",
        data={"file": (io.BytesIO(_csv([_import_row()])), "lib.csv")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 500

    assert _actions(app)["IMPORT_FAILED"] == 1
    with app.app_context():
        assert db.session.query(ImportJob).one().status == "FAILED"


def test_user_and_auth_events_are_audited(app, client, make_user):
    admin = make_user("ADMINISTRATOR")
    login_as(client, admin)
    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json={"username": admin.username, "password": "wrong"})

    counts = _actions(app)
    assert counts["LOGIN_SUCCESS"] == 1
    assert counts["LOGOUT"] == 1
    assert counts["LOGIN_FAILURE"] == 1

"""I-18 tamper-evident audit log, I-09 verified backups, I-21 readiness / metrics / log file.

TC-044. Requirements: FR-150, FR-151, FR-152, FR-153, AUD-072, AUD-073, AUD-074, AUD-075, SEC-029, SEC-030, NFR-011, NFR-012, BR-020.
"""

import gzip
import json
import logging
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from app.audit_chain import AuditChainService, verify_sqlite_file
from app.audit_hash import GENESIS, canonical_bytes, compute_hash
from app.extensions import db
from app.models.audit import AuditLogEntry
from app.services import backup_service
from tests.helpers import PASSWORD, login_as, make_cast, valid_payload


def _make_rows(client, cast, wcnv_ids, count=3):
    login_as(client, cast["engineer"])
    for i in range(count):
        resp = client.post(
            "/api/v1/status-codes", json=valid_payload(*wcnv_ids, title=f"Chain test code {i}")
        )
        assert resp.status_code == 201


@pytest.fixture()
def seeded_file_app(file_app):
    """A file-backed app with an engineer and a handful of audit rows."""
    with file_app.app_context():
        from app.services.user_service import UserService

        UserService.create_user(
            username="eng",
            email="eng@example.com",
            full_name="Eng",
            role_code="ENGINEER",
            password=PASSWORD,
            actor=None,
        )
    client = file_app.test_client()
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "eng", "password": PASSWORD}
        ).status_code
        == 200
    )
    for i in range(3):
        resp = client.post(
            "/api/v1/status-codes",
            json={
                "functional_system_group": _ids(file_app)[0],
                "functional_subgroup": _ids(file_app)[1],
                "turbine_platforms": ["3XM"],
                "title": f"Backup test code {i}",
                "description": "Created for the backup and chain tests.",
                "status_category": "ERROR",
                "available_group": 27,
                "set_delay": "10ms",
                "reset_delay": "2min",
            },
        )
        assert resp.status_code == 201, resp.get_json()
    return file_app


def _ids(application):
    with application.app_context():
        from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup

        group = db.session.query(LookupFunctionalSystemGroup).filter_by(code="WCNV").one()
        sub = (
            db.session.query(LookupFunctionalSubgroup)
            .filter_by(functional_system_group_id=group.id, code="010xx")
            .one()
        )
        return group.id, sub.id


def _db_path(application):
    with application.app_context():
        return db.engine.url.database


def _raw(application):
    return sqlite3.connect(_db_path(application))


# ------------------------------------------------------------------ chain: writing
def test_every_audit_row_is_chained_to_its_predecessor(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _make_rows(client, cast, wcnv_ids)
    with app.app_context():
        rows = db.session.query(AuditLogEntry).order_by(AuditLogEntry.id).all()
        assert len(rows) >= 3
        assert rows[0].prev_hash == GENESIS
        for previous, row in zip(rows, rows[1:], strict=False):
            assert row.prev_hash == previous.entry_hash
        assert all(len(r.entry_hash) == 64 for r in rows)
        assert AuditChainService.verify(update_anchor=False)["ok"] is True


def test_the_hash_is_reproducible_from_the_stored_fields(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _make_rows(client, cast, wcnv_ids, 1)
    with app.app_context():
        row = db.session.query(AuditLogEntry).order_by(AuditLogEntry.id.desc()).first()
        payload = canonical_bytes(
            row.entity_type,
            row.entity_id,
            row.action,
            row.actor_id,
            row.occurred_at,
            row.before_value,
            row.after_value,
            row.ip_address,
            row.request_id,
            row.prev_hash,
        )
        assert compute_hash(payload) == row.entry_hash


def test_a_configured_key_makes_the_chain_keyed(app, client, make_user, wcnv_ids):
    app.config["AUDIT_HMAC_KEY"] = "k" * 32
    cast = make_cast(make_user)
    _make_rows(client, cast, wcnv_ids, 1)
    with app.app_context():
        row = db.session.query(AuditLogEntry).order_by(AuditLogEntry.id.desc()).first()
        payload = canonical_bytes(
            row.entity_type,
            row.entity_id,
            row.action,
            row.actor_id,
            row.occurred_at,
            row.before_value,
            row.after_value,
            row.ip_address,
            row.request_id,
            row.prev_hash,
        )
        assert compute_hash(payload) != row.entry_hash  # not the unkeyed hash
        assert compute_hash(payload, b"k" * 32) == row.entry_hash
        app.config["AUDIT_HMAC_KEY"] = "another key entirely"
        assert AuditChainService.verify(update_anchor=False)["ok"] is False  # wrong key


# ------------------------------------------------------------------ chain: tamper detection
def _drop_triggers(connection):
    connection.execute("DROP TRIGGER IF EXISTS trg_audit_no_update")
    connection.execute("DROP TRIGGER IF EXISTS trg_audit_no_delete")


def test_an_edited_row_is_found_and_named(seeded_file_app):
    with seeded_file_app.app_context():
        assert AuditChainService.verify()["ok"] is True
    connection = _raw(seeded_file_app)
    _drop_triggers(connection)
    target = connection.execute(
        "SELECT id FROM audit_log_entry ORDER BY id LIMIT 1 OFFSET 1"
    ).fetchone()[0]
    connection.execute("UPDATE audit_log_entry SET action = 'FORGED' WHERE id = ?", (target,))
    connection.commit()
    connection.close()
    with seeded_file_app.app_context():
        result = AuditChainService.verify()
        assert result["ok"] is False and result["first_bad_id"] == target
        assert "hash" in result["reason"]


def test_a_removed_row_breaks_the_link(seeded_file_app):
    connection = _raw(seeded_file_app)
    _drop_triggers(connection)
    middle = connection.execute(
        "SELECT id FROM audit_log_entry ORDER BY id LIMIT 1 OFFSET 1"
    ).fetchone()[0]
    connection.execute("DELETE FROM audit_log_entry WHERE id = ?", (middle,))
    connection.commit()
    connection.close()
    with seeded_file_app.app_context():
        result = AuditChainService.verify(update_anchor=False)
        assert result["ok"] is False and "link" in result["reason"]


def test_truncating_the_tail_is_caught_by_the_anchor(seeded_file_app):
    with seeded_file_app.app_context():
        assert AuditChainService.verify()["ok"] is True  # writes the anchor
        assert AuditChainService.read_anchor()["count"] >= 3
    connection = _raw(seeded_file_app)
    _drop_triggers(connection)
    connection.execute(
        "DELETE FROM audit_log_entry WHERE id = (SELECT MAX(id) FROM audit_log_entry)"
    )
    connection.commit()
    connection.close()
    with seeded_file_app.app_context():
        result = AuditChainService.verify()
        assert result["ok"] is False and "shorter" in result["reason"]


def test_a_forged_row_cannot_be_repaired_without_the_key(file_app):
    file_app.config["AUDIT_HMAC_KEY"] = "s" * 40
    with file_app.app_context():
        from app.services.audit_service import AuditService

        for i in range(3):
            AuditService.log("Thing", i, "CREATE", actor=None, after={"n": i})
        db.session.commit()
    connection = _raw(file_app)
    _drop_triggers(connection)
    rows = connection.execute(
        "SELECT id, entity_type, entity_id, action, actor_id, occurred_at, before_value, after_value,"
        " ip_address, request_id, prev_hash FROM audit_log_entry ORDER BY id"
    ).fetchall()
    first = rows[0]
    # An attacker who edits row 1 and recomputes the hashes *without the key*:
    connection.execute("UPDATE audit_log_entry SET action = 'FORGED' WHERE id = ?", (first[0],))
    forged = compute_hash(
        canonical_bytes(
            first[1],
            first[2],
            "FORGED",
            first[4],
            first[5],
            first[6],
            first[7],
            first[8],
            first[9],
            first[10],
        )
    )
    connection.execute("UPDATE audit_log_entry SET entry_hash = ? WHERE id = ?", (forged, first[0]))
    connection.commit()
    connection.close()
    with file_app.app_context():
        assert AuditChainService.verify(update_anchor=False)["ok"] is False


def test_the_append_only_triggers_still_stop_edits_inside_the_application(
    app, client, make_user, wcnv_ids
):
    _make_rows(client, make_cast(make_user), wcnv_ids, 1)
    with app.app_context():
        with pytest.raises(Exception, match="append-only"):
            db.session.execute(db.text("UPDATE audit_log_entry SET action = 'X'"))
        db.session.rollback()


def test_rows_without_hashes_before_the_chain_started_are_tolerated(file_app):
    connection = _raw(file_app)
    _drop_triggers(connection)
    connection.execute(
        "INSERT INTO audit_log_entry (entity_type, entity_id, action, occurred_at, request_id) "
        "VALUES ('Legacy', 1, 'CREATE', '2020-01-01T00:00:00.000Z', 'legacy')"
    )
    connection.commit()
    connection.close()
    with file_app.app_context():
        from app.services.audit_service import AuditService

        AuditService.log("Thing", 1, "CREATE", actor=None)
        db.session.commit()
        assert AuditChainService.verify(update_anchor=False)["ok"] is True


def test_verify_tail_detects_recent_tampering_cheaply(seeded_file_app):
    with seeded_file_app.app_context():
        assert AuditChainService.verify_tail(50)["ok"] is True
    connection = _raw(seeded_file_app)
    _drop_triggers(connection)
    connection.execute(
        "UPDATE audit_log_entry SET action = 'FORGED' WHERE id = (SELECT MAX(id) FROM audit_log_entry)"
    )
    connection.commit()
    connection.close()
    with seeded_file_app.app_context():
        assert AuditChainService.verify_tail(50)["ok"] is False


# ------------------------------------------------------------------ archive
def test_archive_exports_old_rows_with_a_hash_and_deletes_nothing(seeded_file_app, tmp_path):
    with seeded_file_app.app_context():
        before = db.session.query(AuditLogEntry).count()
        future = datetime.now(UTC) + timedelta(days=365 * 8)
        result = AuditChainService.archive(tmp_path / "archive", 7, now=future)
        assert result["archived"] == before
        path = tmp_path / "archive" / result["file"].split("\\")[-1].split("/")[-1]
        assert path.is_file()
        digest_line = (tmp_path / "archive" / (path.name + ".sha256")).read_text()
        assert result["sha256"] in digest_line
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            lines = [json.loads(line) for line in handle]
        assert len(lines) == before and lines[0]["prev_hash"] == GENESIS
        assert db.session.query(AuditLogEntry).count() == before + 1  # + the AUDIT_ARCHIVE entry
        assert db.session.query(AuditLogEntry).filter_by(action="AUDIT_ARCHIVE").count() == 1
        # idempotent: a second run archives only what is new (the archive entry itself)
        again = AuditChainService.archive(tmp_path / "archive", 7, now=future)
        assert again["archived"] == 1
        assert AuditChainService.verify(update_anchor=False)["ok"] is True


def test_archive_with_nothing_old_enough_does_nothing(seeded_file_app, tmp_path):
    with seeded_file_app.app_context():
        assert AuditChainService.archive(tmp_path / "a", 7)["archived"] == 0
        assert not (tmp_path / "a").exists()


# ------------------------------------------------------------------ backups
def test_a_backup_is_written_verified_and_recorded(seeded_file_app, tmp_path):
    with seeded_file_app.app_context():
        status = backup_service.create_backup(tmp_path / "bk")
        assert (
            status["ok"]
            and status["integrity_ok"]
            and status["restore_ok"]
            and status["audit_chain_ok"]
        )
        assert status["row_counts"]["status_code"] == 3
        backup_file = tmp_path / "bk" / status["last_file"]
        assert backup_file.is_file()
        recorded = json.loads((tmp_path / "bk" / "backup_status.json").read_text())
        assert (
            recorded["sha256"] == status["sha256"]
            and recorded["last_good_file"] == status["last_file"]
        )
        assert verify_sqlite_file(backup_file)["ok"] is True


def test_only_the_newest_generations_are_kept(seeded_file_app, tmp_path):
    destination = tmp_path / "bk"
    destination.mkdir()
    for day in range(1, 6):
        (destination / f"cscm_backup_2020010{day}_000000.db").write_bytes(b"old")
    with seeded_file_app.app_context():
        status = backup_service.create_backup(destination, keep=3)
    assert len(status["generations"]) == 3 and status["last_file"] in status["generations"]
    with seeded_file_app.app_context(), pytest.raises(ValueError):
        backup_service.create_backup(destination, keep=0)


def test_a_corrupt_backup_fails_verification(seeded_file_app, tmp_path):
    with seeded_file_app.app_context():
        status = backup_service.create_backup(tmp_path / "bk")
        good = tmp_path / "bk" / status["last_file"]
        bad = tmp_path / "bk" / "corrupt.db"
        bad.write_bytes(good.read_bytes()[:2000])
        assert backup_service.verify_backup(bad)["ok"] is False
        assert backup_service.verify_backup(tmp_path / "missing.db")["error"] == "file not found"


def test_a_tampered_audit_log_inside_a_backup_is_flagged(seeded_file_app, tmp_path):
    with seeded_file_app.app_context():
        status = backup_service.create_backup(tmp_path / "bk")
    copy = tmp_path / "bk" / status["last_file"]
    connection = sqlite3.connect(copy)
    _drop_triggers(connection)
    connection.execute("UPDATE audit_log_entry SET action = 'FORGED' WHERE id = 1")
    connection.commit()
    connection.close()
    with seeded_file_app.app_context():
        result = backup_service.verify_backup(copy)
        assert (
            result["integrity_ok"] and result["audit_chain_ok"] is False and result["ok"] is False
        )


def test_a_restored_backup_runs_the_application(seeded_file_app, tmp_path):
    """The restore drill from docs/14 §5 in miniature: back up, start an app on the copy, log in."""
    from app import create_app

    with seeded_file_app.app_context():
        status = backup_service.create_backup(tmp_path / "bk")
    restored = tmp_path / "restored.db"
    restored.write_bytes((tmp_path / "bk" / status["last_file"]).read_bytes())
    application = create_app(
        "testing", {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{restored.as_posix()}"}
    )
    client = application.test_client()
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "eng", "password": PASSWORD}
        ).status_code
        == 200
    )
    assert len(client.get("/api/v1/status-codes?page_size=50").get_json()["items"]) == 3
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def test_backup_needs_a_file_database():
    """An in-memory database cannot be backed up; built explicitly so the test also holds when
    the whole suite runs on a file database (CSCM_TEST_DB=file)."""
    from app import create_app

    in_memory = create_app("testing", {"SQLALCHEMY_DATABASE_URI": "sqlite://"})
    with in_memory.app_context(), pytest.raises(RuntimeError, match="file-based"):
        backup_service.create_backup("somewhere")


def test_cli_backup_verify_and_audit_commands(seeded_file_app, tmp_path):
    runner = seeded_file_app.test_cli_runner()
    destination = tmp_path / "cli-backup"
    result = runner.invoke(args=["backup-db", "--dest", str(destination)])
    assert result.exit_code == 0, result.output
    produced = json.loads(result.output.strip().splitlines()[-1])
    assert produced["ok"] is True
    verified = runner.invoke(args=["verify-backup", str(destination / produced["last_file"])])
    assert verified.exit_code == 0 and json.loads(verified.output)["ok"] is True
    assert runner.invoke(args=["audit-verify"]).exit_code == 0
    archive = runner.invoke(args=["audit-archive", "--dest", str(tmp_path / "arch")])
    assert archive.exit_code == 0 and json.loads(archive.output)["archived"] == 0
    assert runner.invoke(args=["send-reminders"]).exit_code == 0
    seeded_file_app.config["BACKUP_DIR"] = None
    assert runner.invoke(args=["backup-db"]).exit_code != 0  # no destination known


def test_cli_audit_verify_fails_with_a_non_zero_exit_when_broken(seeded_file_app):
    connection = _raw(seeded_file_app)
    _drop_triggers(connection)
    connection.execute("UPDATE audit_log_entry SET action = 'FORGED' WHERE id = 1")
    connection.commit()
    connection.close()
    result = seeded_file_app.test_cli_runner().invoke(args=["audit-verify"])
    assert result.exit_code != 0 and "FAILED" in result.output


# ------------------------------------------------------------------ readiness
def test_ready_reports_ok_and_degraded_by_backup_state(seeded_file_app, tmp_path):
    client = seeded_file_app.test_client()
    body = client.get("/api/v1/health/ready").get_json()
    assert body["checks"]["database"]["state"] == "ok" and body["checks"]["schema"]["state"] == "ok"
    assert body["checks"]["backup"]["state"] == "missing" and body["status"] == "degraded"
    with seeded_file_app.app_context():
        backup_service.create_backup(seeded_file_app.config["BACKUP_DIR"])
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200 and response.get_json()["status"] == "ok"
    seeded_file_app.config["BACKUP_MAX_AGE_HOURS"] = -1
    assert client.get("/api/v1/health/ready").get_json()["checks"]["backup"]["state"] == "stale"
    seeded_file_app.config["BACKUP_DIR"] = None
    assert (
        client.get("/api/v1/health/ready").get_json()["checks"]["backup"]["state"]
        == "not_configured"
    )


def test_ready_is_503_when_the_chain_is_broken_or_the_schema_outdated(seeded_file_app):
    client = seeded_file_app.test_client()
    connection = _raw(seeded_file_app)
    connection.execute("UPDATE alembic_version SET version_num = 'old'")
    connection.commit()
    response = client.get("/api/v1/health/ready")
    assert (
        response.status_code == 503
        and response.get_json()["checks"]["schema"]["state"] == "outdated"
    )
    connection.execute(
        "UPDATE alembic_version SET version_num = ?",
        (response.get_json()["checks"]["schema"]["head"],),
    )
    _drop_triggers(connection)
    connection.execute(
        "UPDATE audit_log_entry SET action = 'FORGED' WHERE id = (SELECT MAX(id) FROM audit_log_entry)"
    )
    connection.commit()
    connection.close()
    broken = client.get("/api/v1/health/ready")
    assert (
        broken.status_code == 503
        and broken.get_json()["checks"]["audit_chain"]["state"] == "broken"
    )


def test_ready_needs_no_login_and_reveals_no_business_data(client):
    body = client.get("/api/v1/health/ready").get_json()
    assert set(body) == {"status", "version", "checks"}
    assert "title" not in json.dumps(body)


# ------------------------------------------------------------------ metrics and log file
def test_metrics_are_refused_outside_the_allowed_networks(app, client):
    resp = client.get("/metrics", environ_overrides={"REMOTE_ADDR": "8.8.8.8"})
    assert resp.status_code == 403
    ok = client.get("/metrics", environ_overrides={"REMOTE_ADDR": "127.0.0.1"})
    assert ok.status_code == 200 and b"cscm_http_requests_total" in ok.data
    for name in (
        "cscm_http_request_duration_seconds_bucket",
        "cscm_db_lock_wait_seconds",
        "cscm_backup_ok",
    ):
        assert name.encode() in ok.data


def test_a_metrics_token_admits_an_address_outside_the_networks(app, client):
    app.config["METRICS_TOKEN"] = "scrape-me"
    outside = {"REMOTE_ADDR": "8.8.8.8"}
    assert client.get("/metrics", environ_overrides=outside).status_code == 403
    assert (
        client.get(
            "/metrics", environ_overrides=outside, headers={"Authorization": "Bearer wrong"}
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/metrics", environ_overrides=outside, headers={"Authorization": "Bearer scrape-me"}
        ).status_code
        == 200
    )


def test_metrics_count_requests_and_hold_no_business_data(app, client, make_user, wcnv_ids):
    login_as(client, make_cast(make_user)["engineer"])
    client.post("/api/v1/status-codes", json=valid_payload(*wcnv_ids, title="Secret metrics title"))
    text = client.get("/metrics", environ_overrides={"REMOTE_ADDR": "127.0.0.1"}).get_data(
        as_text=True
    )
    assert 'method="POST",status="2xx"' in text
    assert "Secret metrics title" not in text


def test_requests_are_logged_to_the_configured_file(tmp_path):
    from app import create_app

    log_file = tmp_path / "logs" / "cscm.log"
    application = create_app("testing", {"LOG_FILE": str(log_file)})
    application.test_client().get("/api/v1/health")
    logger = logging.getLogger("cscm")
    handlers = [h for h in logger.handlers if getattr(h, "_cscm_file", False)]
    for handler in handlers:
        handler.flush()
    try:
        assert log_file.is_file() and '"path": "/api/v1/health"' in log_file.read_text(
            encoding="utf-8"
        )
    finally:
        for handler in handlers:  # the logger is process-global: do not leak the file handler
            logger.removeHandler(handler)
            handler.close()

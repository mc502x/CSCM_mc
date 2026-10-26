"""Automated backups with a verified restore (I-09).

`create_backup` uses SQLite's online-backup API (safe while the application is running),
keeps the newest N generations, and then *proves* the new file is usable instead of
trusting it: `PRAGMA integrity_check`, a restore into a scratch database, a comparison of
row counts, the Alembic version, and the audit hash chain of the copy. The result goes to
`backup_status.json` next to the backups; /api/v1/health/ready reads it, so a missing or
stale backup shows up in monitoring.

Run it from the OS scheduler (deploy/*): `flask backup-db`. Restore procedure and the
quarterly drill: docs/14-deployment-architecture.md §5."""

import json
import shutil
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from flask import current_app
from sqlalchemy import inspect

from app.audit_chain import verify_sqlite_file
from app.extensions import db
from app.services import manifest_service
from app.utils import format_iso, parse_iso

STATUS_FILE = "backup_status.json"
FILE_PREFIX = "cscm_backup_"
# Tables whose row counts must survive the backup/restore round trip unchanged.
_COUNTED_TABLES = (
    "user",
    "status_code",
    "status_code_revision",
    "change_request",
    "release",
    "audit_log_entry",
)


def _count_rows(connection: sqlite3.Connection, table: str) -> int:
    if table not in _COUNTED_TABLES:  # the name is interpolated, so only ever a known table
        raise ValueError(f"not a counted table: {table}")
    statement = f'SELECT COUNT(*) FROM "{table}"'  # nosec B608
    return connection.execute(statement).fetchone()[0]


def _database_file() -> Path:
    database = db.engine.url.database
    if not database or database == ":memory:":
        raise RuntimeError("Backups need a file-based SQLite database.")
    return Path(database)


def _head_revision() -> str | None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    migrations = Path(current_app.root_path).parent / "migrations"
    config = Config(str(migrations / "alembic.ini"))
    config.set_main_option("script_location", str(migrations))
    return ScriptDirectory.from_config(config).get_current_head()


def verify_backup(path: str | Path, expected_counts: dict | None = None) -> dict:
    """Integrity check + restore smoke test of one backup file. Never touches the live DB."""
    path = Path(path)
    result: dict = {"file": str(path), "integrity_ok": False, "restore_ok": False, "ok": False}
    if not path.is_file():
        result["error"] = "file not found"
        return result

    source = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        result["integrity_ok"] = source.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        counts = {
            table: source.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]  # nosec B608
            for table in _COUNTED_TABLES
        }
        version_row = source.execute("SELECT version_num FROM alembic_version").fetchone()
        result["schema_version"] = version_row[0] if version_row else None
    except sqlite3.DatabaseError as exc:
        result["error"] = str(exc)
        return result
    finally:
        source.close()

    # Restore into a scratch database exactly as an operator would, then read it back.
    with tempfile.TemporaryDirectory() as scratch:
        restored = Path(scratch) / "restored.db"
        shutil.copyfile(path, restored)
        connection = sqlite3.connect(restored)
        try:
            restored_counts = {table: _count_rows(connection, table) for table in _COUNTED_TABLES}
            connection.execute("PRAGMA foreign_key_check")
        finally:
            connection.close()
        result["restore_ok"] = restored_counts == counts and (
            expected_counts is None or all(counts[t] >= expected_counts.get(t, 0) for t in counts)
        )
        result["row_counts"] = counts

    chain_key = current_app.config.get("AUDIT_HMAC_KEY")
    chain = verify_sqlite_file(path, chain_key.encode("utf-8") if chain_key else None)
    result["audit_chain_ok"] = bool(chain["ok"])
    result["audit_rows"] = chain["checked"]
    result["ok"] = bool(
        result["integrity_ok"] and result["restore_ok"] and result["audit_chain_ok"]
    )
    return result


def create_backup(dest_dir: str | Path, keep: int = 14) -> dict:
    """Write a new backup generation to `dest_dir`, verify it, prune old ones, record status."""
    if keep < 1:
        raise ValueError("keep must be at least 1")
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    database = _database_file()
    expected = {}
    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    target = dest / f"{FILE_PREFIX}{stamp}.db"

    db.session.rollback()  # no open transaction may hold the write lock during the copy
    live = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        for table in _COUNTED_TABLES:
            expected[table] = _count_rows(live, table)
        copy = sqlite3.connect(target)
        try:
            live.backup(copy)
        finally:
            copy.close()
    finally:
        live.close()

    verification = verify_backup(target, expected_counts=None)
    status = {
        "last_attempt_at": format_iso(datetime.now(UTC)),
        "last_success_at": None,
        "last_file": target.name,
        "size_bytes": target.stat().st_size,
        "sha256": manifest_service.sha256_hex(target.read_bytes()),
        "ok": verification.get("ok", False),
        "integrity_ok": verification.get("integrity_ok", False),
        "restore_ok": verification.get("restore_ok", False),
        "audit_chain_ok": verification.get("audit_chain_ok", False),
        "schema_version": verification.get("schema_version"),
        "row_counts": verification.get("row_counts"),
    }
    previous = read_status(dest)
    if status["ok"]:
        status["last_success_at"] = status["last_attempt_at"]
    else:
        # A bad backup is kept for diagnosis but never counts as the last good one.
        status["last_success_at"] = previous.get("last_success_at") if previous else None
        status["last_good_file"] = previous.get("last_good_file") if previous else None
    if status["ok"]:
        status["last_good_file"] = target.name

    generations = sorted(dest.glob(f"{FILE_PREFIX}*.db"))
    for old in generations[: max(0, len(generations) - keep)]:
        old.unlink(missing_ok=True)
    status["generations"] = [p.name for p in sorted(dest.glob(f"{FILE_PREFIX}*.db"))]
    (dest / STATUS_FILE).write_text(json.dumps(status, indent=2), encoding="utf-8")
    return status


def read_status(dest_dir: str | Path | None = None) -> dict | None:
    dest = Path(dest_dir) if dest_dir else None
    if dest is None:
        configured = current_app.config.get("BACKUP_DIR")
        if not configured:
            return None
        dest = Path(configured)
    path = dest / STATUS_FILE
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def status_summary() -> dict:
    """For the readiness probe: configured? how old is the last verified-good backup?"""
    if not current_app.config.get("BACKUP_DIR"):
        return {"state": "not_configured"}
    status = read_status()
    if status is None or not status.get("last_success_at"):
        return {"state": "missing"}
    age_hours = (datetime.now(UTC) - parse_iso(status["last_success_at"])).total_seconds() / 3600
    state = "ok" if age_hours <= current_app.config["BACKUP_MAX_AGE_HOURS"] else "stale"
    if not status.get("ok") and state == "ok":
        state = "last_attempt_failed"
    return {
        "state": state,
        "age_hours": round(age_hours, 1),
        "last_success_at": status["last_success_at"],
        "last_file": status.get("last_good_file") or status.get("last_file"),
    }


def migration_state() -> dict:
    """Is the database at the Alembic head this code expects?"""
    connection = db.session.connection()
    inspector = inspect(connection)
    if "alembic_version" not in inspector.get_table_names():
        return {"ok": False, "current": None, "head": _head_revision()}
    current = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
    head = _head_revision()
    return {"ok": current == head, "current": current, "head": head}

"""audit hash chain (I-18) and the FTS5 search index (I-31)

* audit_log_entry gains prev_hash / entry_hash. Existing rows are chained in id
  order. The append-only trigger is dropped for the duration of the back-fill
  (the only moment anything but INSERT is allowed) and recreated afterwards.
* The optional FTS5 index (docs/artifacts/schema-fts5.sql) is created and filled
  when the SQLite build has the module; otherwise it is skipped and catalogue
  search falls back to substring matching.

Revision ID: f8b2d4e6a012
Revises: e7a1c3d5f901
Create Date: 2026-10-22 18:30:00.000000

"""

import hashlib
import hmac
import json
import logging
import sqlite3

import sqlalchemy as sa
from alembic import op
from flask import current_app

from app.schema_sql import FTS_SQL_PATH, split_statements

revision = "f8b2d4e6a012"
down_revision = "e7a1c3d5f901"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.env")

_NO_UPDATE_TRIGGER = """
CREATE TRIGGER trg_audit_no_update
BEFORE UPDATE ON audit_log_entry
BEGIN
    SELECT RAISE(ABORT, 'audit_log_entry is append-only');
END
"""


def _canonical(row, prev_hash: str) -> bytes:
    # Frozen copy of app.audit_hash.canonical_bytes (a test keeps them identical).
    return json.dumps(
        [row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], prev_hash],
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _hash(payload: bytes, key: bytes | None) -> str:
    if key:
        return hmac.new(key, payload, hashlib.sha256).hexdigest()
    return hashlib.sha256(payload).hexdigest()


def _columns(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def _audit_key() -> bytes | None:
    try:
        raw = current_app.config.get("AUDIT_HMAC_KEY")
    except RuntimeError:  # offline / no app context
        raw = None
    return raw.encode("utf-8") if raw else None


def upgrade():
    bind = op.get_bind()

    for column in ("prev_hash", "entry_hash"):
        if column not in _columns(bind, "audit_log_entry"):
            op.execute(f"ALTER TABLE audit_log_entry ADD COLUMN {column} TEXT")

    pending = bind.execute(
        sa.text("SELECT COUNT(*) FROM audit_log_entry WHERE entry_hash IS NULL")
    ).scalar()
    if pending:
        key = _audit_key()
        prev = bind.execute(
            sa.text(
                "SELECT entry_hash FROM audit_log_entry WHERE entry_hash IS NOT NULL "
                "ORDER BY id DESC LIMIT 1"
            )
        ).scalar()
        prev = prev or "GENESIS"
        rows = bind.execute(
            sa.text(
                "SELECT entity_type, entity_id, action, actor_id, occurred_at, before_value, "
                "after_value, ip_address, request_id, id FROM audit_log_entry "
                "WHERE entry_hash IS NULL ORDER BY id"
            )
        ).fetchall()
        op.execute("DROP TRIGGER IF EXISTS trg_audit_no_update")
        for row in rows:
            digest = _hash(_canonical(row, prev), key)
            bind.execute(
                sa.text("UPDATE audit_log_entry SET prev_hash = :p, entry_hash = :h WHERE id = :i"),
                {"p": prev, "h": digest, "i": row[9]},
            )
            prev = digest
        op.execute(_NO_UPDATE_TRIGGER)

    _create_fts(bind)


def _create_fts(bind) -> None:
    raw = bind.connection.dbapi_connection
    if not isinstance(raw, sqlite3.Connection):
        return
    try:
        raw.execute("CREATE VIRTUAL TABLE temp._fts_probe USING fts5(x)")
        raw.execute("DROP TABLE temp._fts_probe")
    except sqlite3.OperationalError:
        log.warning("SQLite has no FTS5 module; catalogue search will use substring matching.")
        return

    for stmt in split_statements(FTS_SQL_PATH.read_text(encoding="utf-8")):
        op.execute(stmt)
    already = bind.execute(sa.text("SELECT COUNT(*) FROM status_code_fts")).scalar()
    if not already:
        op.execute(
            "INSERT INTO status_code_fts (rowid, identifier, title, description, remedy_text) "
            "SELECT r.id, COALESCE(sc.status_code_identifier, ''), r.title, r.description, "
            "COALESCE(r.remedy_text, '') FROM status_code_revision r "
            "JOIN status_code sc ON sc.id = r.status_code_id"
        )


def downgrade():
    for name in (
        "trg_fts_code_identifier",
        "trg_fts_revision_delete",
        "trg_fts_revision_update",
        "trg_fts_revision_insert",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
    op.execute("DROP TABLE IF EXISTS status_code_fts_vocab")
    op.execute("DROP TABLE IF EXISTS status_code_fts")

    bind = op.get_bind()
    for column in ("entry_hash", "prev_hash"):
        if column in _columns(bind, "audit_log_entry"):
            try:
                op.execute(f"ALTER TABLE audit_log_entry DROP COLUMN {column}")
            except sa.exc.OperationalError:
                pass

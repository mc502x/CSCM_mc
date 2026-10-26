"""Tamper-evident audit log (I-18, AUD-074) and its 7-year archive job.

*Writing:* a `before_flush` hook gives every new audit row its `prev_hash`/`entry_hash`,
in insertion order, continuing from the last stored row. The write transaction already
holds SQLite's write lock (BEGIN IMMEDIATE), so two requests can never extend the chain
from the same predecessor.

*Verifying:* `AuditChainService.verify()` walks the table and reports the first row whose
link or hash does not fit - a removed, reordered or edited row. The append-only triggers
stop in-application edits; the chain makes edits by someone *with database access*
detectable, and with `AUDIT_HMAC_KEY` configured, impossible to repair without the key.
Truncation at the very end leaves no trace in the rows themselves, so every verification
records an *anchor* (row count + head hash); the next verification checks the anchor row is
still there unchanged.

*Archiving:* rows older than the retention period are exported to a compressed file with a
hash and an audit entry describing it. Nothing is ever deleted."""

import gzip
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from flask import current_app
from sqlalchemy import event, text
from sqlalchemy.orm import Session, attributes

from app.audit_hash import GENESIS, canonical_bytes, compute_hash
from app.extensions import db
from app.models.audit import AuditLogEntry
from app.services import manifest_service
from app.utils import format_iso


def _key() -> bytes | None:
    raw = current_app.config.get("AUDIT_HMAC_KEY")
    return raw.encode("utf-8") if raw else None


@event.listens_for(Session, "before_flush")
def _chain_new_audit_rows(session: Session, flush_context, instances) -> None:
    rows = [obj for obj in session.new if isinstance(obj, AuditLogEntry)]
    if not rows:
        return
    rows.sort(key=lambda obj: attributes.instance_state(obj).insert_order or 0)
    last = session.execute(
        text("SELECT entry_hash FROM audit_log_entry ORDER BY id DESC LIMIT 1")
    ).scalar()
    prev = last or GENESIS
    key = _key()
    for row in rows:
        row.prev_hash = prev
        row.entry_hash = compute_hash(
            canonical_bytes(
                row.entity_type,
                row.entity_id,
                row.action,
                row.actor_id,
                row.occurred_at,
                row.before_value,
                row.after_value,
                row.ip_address,
                row.request_id,
                prev,
            ),
            key,
        )
        prev = row.entry_hash


_COLUMNS = (
    "id, entity_type, entity_id, action, actor_id, occurred_at, before_value, after_value, "
    "ip_address, request_id, prev_hash, entry_hash"
)


def verify_rows(rows, key: bytes | None, anchor: dict | None = None) -> dict:
    """Pure chain check over an iterable of DB rows (works on a live DB and on a backup)."""
    prev = GENESIS
    checked = 0
    head = None
    anchor_ok = True
    started = False
    for row in rows:
        (rid, entity_type, entity_id, action, actor_id, occurred_at, before, after, ip, request_id,
         prev_hash, entry_hash) = row  # fmt: skip
        checked += 1
        if entry_hash is None:
            if started:
                return _bad(rid, "a row without a hash follows hashed rows", checked, head)
            continue  # un-migrated legacy rows before the chain started
        started = True
        if prev_hash != prev:
            return _bad(
                rid, "broken link: prev_hash does not match the previous row", checked, head
            )
        expected = compute_hash(
            canonical_bytes(
                entity_type,
                entity_id,
                action,
                actor_id,
                occurred_at,
                before,
                after,
                ip,
                request_id,
                prev,
            ),
            key,
        )
        if expected != entry_hash:
            return _bad(rid, "row content does not match its hash", checked, head)
        prev = entry_hash
        head = entry_hash
        if anchor and checked == anchor.get("count") and entry_hash != anchor.get("head_hash"):
            anchor_ok = False
    if anchor and checked < int(anchor.get("count", 0)):
        anchor_ok = False
    result = {"ok": anchor_ok, "checked": checked, "head_hash": head, "first_bad_id": None}
    if not anchor_ok:
        result["reason"] = (
            "the log is shorter than at the last verification or an earlier row changed "
            "(rows were removed or altered)"
        )
    return result


def _bad(row_id: int, reason: str, checked: int, head: str | None) -> dict:
    return {
        "ok": False,
        "checked": checked,
        "head_hash": head,
        "first_bad_id": row_id,
        "reason": reason,
    }


class AuditChainService:
    @staticmethod
    def _anchor_path() -> Path:
        return Path(current_app.instance_path) / "audit_chain_anchor.json"

    @staticmethod
    def read_anchor() -> dict | None:
        path = AuditChainService._anchor_path()
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    @staticmethod
    def verify(update_anchor: bool = True) -> dict:
        """Full verification of the live table (+ the anchor of the previous run)."""
        # A read-only walk: do not hold the write lock while hashing a large table.
        db.session.rollback()
        rows = db.session.execute(
            text(f"SELECT {_COLUMNS} FROM audit_log_entry ORDER BY id")  # noqa: S608  # nosec B608
        )
        result = verify_rows(rows, _key(), AuditChainService.read_anchor())
        result["verified_at"] = format_iso(datetime.now(UTC))
        if result["ok"] and update_anchor and result["checked"]:
            AuditChainService._anchor_path().write_text(
                json.dumps(
                    {
                        "count": result["checked"],
                        "head_hash": result["head_hash"],
                        "verified_at": result["verified_at"],
                    }
                ),
                encoding="utf-8",
            )
        return result

    @staticmethod
    def verify_tail(limit: int = 200) -> dict:
        """Cheap check of the newest `limit` rows (used by the readiness probe)."""
        db.session.rollback()
        rows = db.session.execute(
            text(
                f"SELECT {_COLUMNS} FROM (SELECT {_COLUMNS} FROM audit_log_entry "  # noqa: S608  # nosec B608
                "ORDER BY id DESC LIMIT :n) ORDER BY id"
            ),
            {"n": limit},
        ).fetchall()
        if not rows:
            return {"ok": True, "checked": 0}
        key = _key()
        prev = rows[0][10]  # the window starts at a trusted link; everything after must follow it
        checked = 0
        for row in rows:
            if row[11] is None or prev is None:
                prev = row[11]
                continue
            if row[10] != prev:
                return {"ok": False, "checked": checked, "first_bad_id": row[0]}
            expected = canonical_bytes(
                row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], prev
            )
            if compute_hash(expected, key) != row[11]:
                return {"ok": False, "checked": checked, "first_bad_id": row[0]}
            prev = row[11]
            checked += 1
        return {"ok": True, "checked": checked}

    @staticmethod
    def archive(
        dest_dir: str | Path, older_than_years: float = 7, actor=None, now: datetime | None = None
    ) -> dict:
        """Export audit rows older than the retention period to `dest_dir` (JSON lines,
        gzip, plus a .sha256 file). Rows stay in the table; an AUDIT_ARCHIVE entry records
        what was written, and the next run continues after the last archived row."""
        from app.services.audit_service import AuditService

        now = now or datetime.now(UTC)
        cutoff = format_iso(now - timedelta(days=round(365.25 * older_than_years)))
        last = (
            db.session.query(AuditLogEntry)
            .filter(AuditLogEntry.entity_type == "AuditArchive")
            .order_by(AuditLogEntry.id.desc())
            .first()
        )
        after_id = 0
        if last is not None and last.after_value:
            after_id = int(json.loads(last.after_value).get("last_id", 0))

        rows = (
            db.session.query(AuditLogEntry)
            .filter(AuditLogEntry.id > after_id, AuditLogEntry.occurred_at < cutoff)
            .order_by(AuditLogEntry.id)
            .all()
        )
        if not rows:
            return {"archived": 0, "cutoff": cutoff}

        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        name = f"audit_archive_{rows[0].id:09d}-{rows[-1].id:09d}.jsonl.gz"
        path = dest / name
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            for row in rows:
                handle.write(
                    json.dumps(
                        {
                            "id": row.id,
                            "entity_type": row.entity_type,
                            "entity_id": row.entity_id,
                            "action": row.action,
                            "actor_id": row.actor_id,
                            "occurred_at": row.occurred_at,
                            "before_value": row.before_value,
                            "after_value": row.after_value,
                            "ip_address": row.ip_address,
                            "request_id": row.request_id,
                            "prev_hash": row.prev_hash,
                            "entry_hash": row.entry_hash,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        digest = manifest_service.sha256_hex(path.read_bytes())
        (dest / (name + ".sha256")).write_text(f"{digest}  {name}\n", encoding="utf-8")
        AuditService.log(
            "AuditArchive",
            rows[-1].id,
            "AUDIT_ARCHIVE",
            actor=actor,
            after={
                "file": name,
                "count": len(rows),
                "first_id": rows[0].id,
                "last_id": rows[-1].id,
                "sha256": digest,
                "cutoff": cutoff,
            },
        )
        db.session.commit()
        return {
            "archived": len(rows),
            "file": str(path),
            "sha256": digest,
            "cutoff": cutoff,
            "last_id": rows[-1].id,
        }


def verify_sqlite_file(path: str | Path, key: bytes | None = None) -> dict:
    """Chain check on a database file (a backup) without the application."""
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        statement = (
            f"SELECT {_COLUMNS} FROM audit_log_entry ORDER BY id"  # noqa: S608  # nosec B608
        )
        return verify_rows(connection.execute(statement), key)
    finally:
        connection.close()

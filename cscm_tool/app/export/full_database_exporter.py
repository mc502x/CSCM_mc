"""Full raw database export/backup via SQLite's Online Backup API — never a
raw file copy (docs/14-deployment-architecture.md §5), so this is safe to
run against a live database with concurrent readers/writers; SEC-015
restricts the calling route to the Administrator role."""

import os
import sqlite3
import tempfile
from pathlib import Path

from app.extensions import db


def export_full_database_bytes() -> bytes:
    """Reuses the ORM session's own connection as the backup source (same
    pattern as migrations/versions/9dc07a07a48b_*.py) rather than calling
    db.engine.raw_connection(), which would compete for a second checkout
    of the same pooled connection.

    Commits first: every transaction in this app runs as BEGIN IMMEDIATE
    (app/__init__.py's `begin` listener), and Python's sqlite3.Connection.backup()
    retries on SQLITE_BUSY forever with no total timeout — if the source
    connection still holds that write lock open, backup() hangs
    indefinitely rather than erroring (verified directly against the
    sqlite3 module, independent of SQLAlchemy). Committing releases the
    lock; the caller's subsequent writes (e.g. the audit log entry) simply
    open a fresh transaction afterward."""
    # Capture the underlying DBAPI connection BEFORE committing: calling
    # db.session.connection() again afterward would trigger SQLAlchemy 2.0's
    # "autobegin" and immediately re-open a fresh BEGIN IMMEDIATE transaction
    # (verified directly — Session.connection() always ensures a transaction
    # is active), putting us right back in the hang this commit is meant to
    # avoid. The captured DBAPI connection object itself is unaffected by
    # the commit that follows.
    connection = db.session.connection()
    dbapi_connection = connection.connection.dbapi_connection
    if not isinstance(dbapi_connection, sqlite3.Connection):
        raise RuntimeError("Full-database export requires a SQLite connection.")
    source: sqlite3.Connection = dbapi_connection
    db.session.commit()

    # mkstemp returns an open file descriptor as well as the path; leaving
    # it open blocks deleting the file on Windows, so close it immediately —
    # we only want the path, sqlite3.connect() opens its own handle.
    fd, tmp_name = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        destination = sqlite3.connect(str(tmp_path))
        try:
            source.backup(destination)
        finally:
            destination.close()
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)

"""Application factory. See docs/18-claude-code-implementation-guide.md §1-2."""

import os
import sqlite3
import time
import uuid

from flask import Flask, g
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.config import CONFIG_BY_NAME, DEFAULT_SECRET_KEY, MIN_PRODUCTION_SECRET_LENGTH
from app.extensions import csrf, db, migrate


@event.listens_for(Engine, "connect")
def _configure_sqlite_connection(dbapi_connection, connection_record):
    """Every connection must enforce FKs; SQLite defaults this off per-connection.
    Also disables pysqlite's own implicit BEGIN so the `begin` listener below
    can issue BEGIN IMMEDIATE instead — see docs/07-database-design.md §7a
    and docs/08-system-architecture.md §8 (WAL-mode read concurrency)."""
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return  # a different database (docs/07 section 12, I-34): nothing SQLite-specific to set
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA busy_timeout = 15000")  # writers queue instead of failing fast
    cursor.close()
    dbapi_connection.isolation_level = None


@event.listens_for(Engine, "begin")
def _begin_transaction(conn):
    """Write transactions acquire SQLite's write lock upfront (BEGIN
    IMMEDIATE) rather than deferring it, which is what makes concurrent
    identifier allocation (docs/07-database-design.md §7a) race-safe instead
    of prone to the classic SQLite "two readers both upgrading to writers"
    failure (https://www.sqlite.org/lang_transaction.html).

    Read-only requests — GET/HEAD/OPTIONS that are not flagged as writing
    (app/db_modes.py) — use a plain deferred BEGIN instead. In WAL mode
    those readers neither block nor are blocked by the writer, which is what
    lets 50 concurrent users search while someone submits (NFR-004,
    docs/08-system-architecture.md §8); taking the write lock for every read
    serialised the whole application and timed out under load."""
    from app.db_modes import is_read_only_request
    from app.observability import observe_lock_wait

    if conn.dialect.name != "sqlite":
        return  # the driver's own BEGIN; row locks replace the SQLite write lock (docs/07 §12)
    if is_read_only_request():
        conn.exec_driver_sql("BEGIN")
        return
    started = time.perf_counter()
    conn.exec_driver_sql("BEGIN IMMEDIATE")
    observe_lock_wait(time.perf_counter() - started)  # I-21: lock-wait histogram


def create_app(config_name: str | None = None, overrides: dict | None = None) -> Flask:
    resolved_name: str = (
        config_name if config_name is not None else os.environ.get("FLASK_ENV", "development")
    )

    # CSCM_INSTANCE_PATH keeps attachments, import files and the audit anchor outside the code
    # directory, so an upgrade (a fresh checkout) never touches them.
    app = Flask(
        __name__,
        instance_path=os.environ.get("CSCM_INSTANCE_PATH") or None,
        instance_relative_config=True,
    )
    app.config.from_object(CONFIG_BY_NAME[resolved_name])
    app.config.update(overrides or {})  # tests and tools: a file database, switched-off features

    if resolved_name == "production":
        # A forgeable session cookie would defeat every access control, so a live
        # instance refuses to start with the development key or a short one (SEC-002).
        key = str(app.config.get("SECRET_KEY") or "")
        if (
            key == DEFAULT_SECRET_KEY
            or "change-me" in key  # also catches the placeholder in .env.example
            or len(key) < MIN_PRODUCTION_SECRET_LENGTH
        ):
            raise RuntimeError(
                "Refusing to start in production: set SECRET_KEY to a random value of at "
                f"least {MIN_PRODUCTION_SECRET_LENGTH} characters."
            )

    if resolved_name == "production" and app.config.get("WINDOWS_AUTH_SIMULATE"):
        raise RuntimeError(
            "Refusing to start in production: WINDOWS_AUTH_SIMULATE lets anybody sign in as any "
            "user and is for development only (SEC-033)."
        )
    if app.config.get("AUTH_MODE", "password") not in ("password", "windows", "both"):
        raise RuntimeError("AUTH_MODE must be password, windows or both.")

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from app.auth.rate_limit import remember_app

    remember_app(app)

    @app.before_request
    def _assign_request_id():
        g.request_id = str(uuid.uuid4())

    from app import (
        audit_chain,  # noqa: F401  (registers the audit hash-chain flush hook)
        models,  # noqa: F401  (registers ORM tables on db.metadata)
    )
    from app.api.v1 import api_v1_bp
    from app.ui import ui_bp

    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")
    app.register_blueprint(ui_bp)

    from app.cli import register_cli_commands, register_operations_commands

    register_cli_commands(app)
    register_operations_commands(app)

    from app.errors import register_error_handlers

    register_error_handlers(app)

    from app.domain.lifecycle import register_lifecycle_guard
    from app.logging_config import configure_logging
    from app.security_headers import register_security_headers

    register_lifecycle_guard()

    from app.observability import register_metrics

    register_security_headers(app)
    configure_logging(app)
    register_metrics(app)

    return app

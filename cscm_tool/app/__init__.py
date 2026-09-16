"""Application factory. See docs/18-claude-code-implementation-guide.md §1-2."""

import os
import uuid

from flask import Flask, g
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.config import CONFIG_BY_NAME
from app.extensions import csrf, db, migrate


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """Every connection must enforce FKs; SQLite defaults this off per-connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def create_app(config_name: str | None = None) -> Flask:
    resolved_name: str = (
        config_name if config_name is not None else os.environ.get("FLASK_ENV", "development")
    )

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(CONFIG_BY_NAME[resolved_name])

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    @app.before_request
    def _assign_request_id():
        g.request_id = str(uuid.uuid4())

    from app import models  # noqa: F401  (registers ORM tables on db.metadata)
    from app.api.v1 import api_v1_bp

    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")

    from app.cli import register_cli_commands

    register_cli_commands(app)

    from app.errors import register_error_handlers

    register_error_handlers(app)

    return app

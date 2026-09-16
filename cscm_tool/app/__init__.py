"""Application factory. See docs/18-claude-code-implementation-guide.md §1-2."""

import os

from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.config import CONFIG_BY_NAME
from app.extensions import db, migrate


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

    from app import models  # noqa: F401  (registers ORM tables on db.metadata)
    from app.api.v1 import api_v1_bp

    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")

    from app.errors import register_error_handlers

    register_error_handlers(app)

    return app

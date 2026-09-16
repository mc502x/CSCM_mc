"""Shared pytest fixtures. Every test gets a fresh in-memory SQLite database
(docs/15-development-standards.md §7), migrated via the same Alembic
migration used in every other environment."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig

from app import create_app

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        # migrations/env.py resolves its engine from current_app, so this reuses
        # the same in-memory SQLite connection (SingletonThreadPool) that
        # db.session uses afterwards within this app context.
        alembic_cfg = AlembicConfig(str(MIGRATIONS_DIR / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
        command.upgrade(alembic_cfg, "head")
        yield application


@pytest.fixture()
def client(app):
    return app.test_client()

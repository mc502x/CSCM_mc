"""Shared pytest fixtures. Every test gets a fresh in-memory SQLite database
(docs/15-development-standards.md §7), migrated via the same Alembic
migration used in every other environment."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig

from app import create_app
from app.auth.rate_limit import reset_for_testing
from app.services.user_service import UserService

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The rate limiter is in-process global state (app/auth/rate_limit.py);
    without this every test would share one sliding window with every other."""
    reset_for_testing()
    yield
    reset_for_testing()


@pytest.fixture()
def app():
    """The migration runs inside its own app-context push/pop, deliberately
    NOT held open for the whole test: Flask reuses an already-active app
    context (and its `g`) for requests dispatched while one is on the
    stack, instead of pushing a fresh one per request. Keeping the context
    open here would leak `g.current_user` (app/auth/decorators.py) across
    what are supposed to be independent test-client requests. The
    in-memory SQLite connection itself survives the pop regardless — it is
    held by the SQLAlchemy engine on the Flask app object, not by any
    particular app context (docs/15-development-standards.md §7)."""
    application = create_app("testing")
    with application.app_context():
        alembic_cfg = AlembicConfig(str(MIGRATIONS_DIR / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
        command.upgrade(alembic_cfg, "head")
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(app):
    """Factory fixture: make_user(role_code="ENGINEER", password="...") ->
    User. Pushes its own short-lived app context per call (see the `app`
    fixture's docstring for why one isn't held open across the test)."""

    counter = {"n": 0}

    def _make(role_code: str = "ENGINEER", password: str = "a genuinely long passphrase"):
        counter["n"] += 1
        with app.app_context():
            from app.extensions import db

            user = UserService.create_user(
                username=f"{role_code.lower()}{counter['n']}",
                email=f"{role_code.lower()}{counter['n']}@example.com",
                full_name=f"Test {role_code.title()} {counter['n']}",
                role_code=role_code,
                password=password,
                actor=None,
            )
            # Force-load what tests read off this object, then detach it —
            # otherwise expire_on_commit leaves a DetachedInstanceError trap
            # the moment this app context (and its session) is torn down.
            _ = (user.id, user.username, user.email, user.full_name, user.role.code)
            db.session.expunge(user)
            return user

    return _make


@pytest.fixture()
def login(client):
    """Factory fixture: login(username, password) -> test response."""

    def _login(username: str, password: str):
        return client.post("/api/v1/auth/login", json={"username": username, "password": password})

    return _login

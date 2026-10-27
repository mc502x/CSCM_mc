"""Shared pytest fixtures. Every test gets a fresh in-memory SQLite database
(docs/15-development-standards.md §7), migrated via the same Alembic
migration used in every other environment."""

import os
import re
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from flask.testing import FlaskClient

from app import create_app
from app.auth.rate_limit import reset_for_testing
from app.services.user_service import UserService

# Every test user is created with this password (tests/helpers.py repeats it).
TEST_PASSWORD = "a genuinely long passphrase"
_STEP_UP_PATH = re.compile(
    r"/(reviewer-signoff|admin-signoff|chief-engineer-decide|publish|decisions)$"
    r"|/exports/full-database$"
)


class StepUpClient(FlaskClient):
    """Test client that answers the I-17 re-authentication prompt for the actor, so the
    many tests about *other* behaviour do not each have to repeat the password. A test
    that is about the prompt itself passes `no_step_up=True` or uses the `raw_client`
    fixture. Without this the requests below would be refused with 403 step_up_required."""

    def open(self, *args, no_step_up: bool = False, **kwargs):
        path = args[0] if args and isinstance(args[0], str) else ""
        method = (kwargs.get("method") or "GET").upper()
        if not no_step_up and method == "POST" and _STEP_UP_PATH.search(path.split("?")[0]):
            if isinstance(kwargs.get("json"), dict):
                kwargs["json"] = {"current_password": TEST_PASSWORD, **kwargs["json"]}
            elif kwargs.get("json") is None and "data" not in kwargs:
                kwargs["json"] = {"current_password": TEST_PASSWORD}
            elif isinstance(kwargs.get("data"), dict):
                kwargs["data"] = {"current_password": TEST_PASSWORD, **kwargs["data"]}
        return super().open(*args, **kwargs)


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


def pytest_collection_modifyitems(config, items):
    """CSCM_TEST_ORDER=reverse|shuffle[:SEED] re-orders the run to prove the
    tests are independent of one another (scripts/generate_test_report.py
    uses it for repeat runs). Default: file order."""
    import os
    import random

    mode = os.environ.get("CSCM_TEST_ORDER", "")
    if mode == "reverse":
        items.reverse()
    elif mode.startswith("shuffle"):
        seed = int(mode.partition(":")[2] or 1)
        random.Random(seed).shuffle(items)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The rate limiter is in-process global state (app/auth/rate_limit.py);
    without this every test would share one sliding window with every other."""
    reset_for_testing()
    yield
    reset_for_testing()


@pytest.fixture()
def app(tmp_path):
    """The migration runs inside its own app-context push/pop, deliberately
    NOT held open for the whole test: Flask reuses an already-active app
    context (and its `g`) for requests dispatched while one is on the
    stack, instead of pushing a fresh one per request. Keeping the context
    open here would leak `g.current_user` (app/auth/decorators.py) across
    what are supposed to be independent test-client requests. The
    in-memory SQLite connection itself survives the pop regardless — it is
    held by the SQLAlchemy engine on the Flask app object, not by any
    particular app context (docs/15-development-standards.md §7)."""
    # CSCM_TEST_DB=file runs the whole suite on a real SQLite *file* (WAL, several connections)
    # instead of an in-memory database: the third verification methodology of
    # docs/13-test-strategy.md section 11. scripts/generate_test_report.py --db file sets it.
    overrides = None
    if os.environ.get("CSCM_TEST_DB") == "file":
        overrides = {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'suite.db').as_posix()}"}
    application = create_app("testing", overrides)
    application.test_client_class = StepUpClient
    # Files the application keeps next to the database (attachments, import files, the audit
    # anchor) go to a per-test directory: a shared one would let a previous test's anchor make
    # this test's shorter audit log look truncated.
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(exist_ok=True)
    with application.app_context():
        alembic_cfg = AlembicConfig(str(MIGRATIONS_DIR / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
        command.upgrade(alembic_cfg, "head")
    yield application
    if overrides:  # a file database: release the file so the temp directory can be removed
        with application.app_context():
            from app.extensions import db

            db.session.remove()
            db.engine.dispose()


@pytest.fixture()
def file_app(tmp_path):
    """An app on a real SQLite *file* (several connections, threads or processes can share it):
    for the backup, background-import, multi-process and migration tests."""
    database = tmp_path / "cscm.db"
    application = create_app(
        "testing",
        {
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.as_posix()}",
            "IMPORT_ASYNC_INLINE": False,
            "BACKUP_DIR": str(tmp_path / "backups"),
        },
    )
    application.test_client_class = StepUpClient
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(exist_ok=True)
    with application.app_context():
        alembic_cfg = AlembicConfig(str(MIGRATIONS_DIR / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
        command.upgrade(alembic_cfg, "head")
    yield application
    with application.app_context():
        from app.extensions import db

        db.session.remove()
        db.engine.dispose()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def raw_client(app):
    """A client that never answers the step-up prompt for the test (see StepUpClient)."""
    return FlaskClient(app, app.response_class, use_cookies=True)


@pytest.fixture()
def make_user(app):
    """Factory fixture: make_user(role_code="ENGINEER", password="...") ->
    User. Pushes its own short-lived app context per call (see the `app`
    fixture's docstring for why one isn't held open across the test)."""

    counter = {"n": 0}

    def _make(
        role_code: str = "ENGINEER",
        password: str = "a genuinely long passphrase",
        engineering_domains: list[str] | None = None,
    ):
        counter["n"] += 1
        with app.app_context():
            from app.extensions import db

            user = UserService.create_user(
                username=f"{role_code.lower()}{counter['n']}",
                email=f"{role_code.lower()}{counter['n']}@example.com",
                full_name=f"Test {role_code.title()} {counter['n']}",
                role_code=role_code,
                password=password,
                engineering_domain_codes=engineering_domains,
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
def wcnv_ids(app):
    """(functional_system_group_id, functional_subgroup_id) for WCNV's
    "Converter" subgroup (010xx, sub-band 1000-1199) — resolved dynamically by
    code rather than hardcoded, since v3 assigns ids by seed insertion order
    (docs/artifacts/schema.sql) and functional_system_group.code is no
    longer globally unique (see app/services/lookup_service.py)."""
    with app.app_context():
        from app.extensions import db
        from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup

        group = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(LookupFunctionalSystemGroup.code == "WCNV")
            .one()
        )
        subgroup = (
            db.session.query(LookupFunctionalSubgroup)
            .filter(
                LookupFunctionalSubgroup.functional_system_group_id == group.id,
                LookupFunctionalSubgroup.code == "010xx",
            )
            .one()
        )
        return group.id, subgroup.id


@pytest.fixture()
def login(client):
    """Factory fixture: login(username, password) -> test response."""

    def _login(username: str, password: str):
        return client.post("/api/v1/auth/login", json={"username": username, "password": password})

    return _login


@pytest.fixture()
def languages_open(app):
    """The beta mark and the hiding of unreviewed languages from Viewers (FR-170, FR-172) switched
    off: for the tests that exercise every language without a review of it."""
    with app.app_context():
        from app.extensions import db
        from app.models.operations import AppSetting
        from app.utils import utcnow_iso

        db.session.add(AppSetting(key="languages.beta_marker", value="0", updated_at=utcnow_iso()))
        db.session.commit()


@pytest.fixture()
def st_mapping(app):
    """The mapping rows of the six programs in tests/fixtures/st (the .st import needs the mapping)."""
    from tests.helpers import seed_st_mapping

    with app.app_context():
        seed_st_mapping()

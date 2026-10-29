"""Property-based fuzz of the whole REST API against docs/artifacts/openapi.yaml (schemathesis): for
every operation, generated paths, queries and bodies - valid and invalid - are sent as an
Administrator to a throw-away database, and none may be answered with a server error. The contract
tests prove that the right inputs work; this proves that wrong ones are refused politely.

TC-082. Requirements: FR-200, NFR-006, SEC-020.
"""

import os
import tempfile
from pathlib import Path

import pytest
import schemathesis
from alembic import command
from alembic.config import Config
from hypothesis import HealthCheck, settings

from app import create_app
from app.services.mapping_service import MappingService
from app.services.user_service import UserService

APP_DIR = Path(__file__).resolve().parents[2]
SPEC = APP_DIR.parent / "docs" / "artifacts" / "openapi.yaml"
PASSWORD = "a genuinely long passphrase"
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")
NOT_FUZZED = (
    "/auth/login",
    "/auth/logout",
    "/exports/full-database",
)  # they end the session / are heavy


class SignedIn:
    """WSGI wrapper: every request carries the session cookie of the Administrator."""

    def __init__(self, wsgi, cookie: str):
        self.wsgi, self.cookie = wsgi, cookie

    def __call__(self, environ, start_response):
        environ["HTTP_COOKIE"] = self.cookie
        return self.wsgi(environ, start_response)


@pytest.fixture(scope="module")
def api_schema():
    work = Path(tempfile.mkdtemp(prefix="cscm_fuzz_"))
    os.environ["CSCM_INSTANCE_PATH"] = str(work / "instance")
    app = create_app(
        "testing",
        {
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(work / 'fuzz.db').as_posix()}",
            "STEP_UP_REQUIRED": False,
        },
    )
    app.instance_path = str(work / "instance")
    Path(app.instance_path).mkdir(exist_ok=True)
    with app.app_context():
        config = Config(str(APP_DIR / "migrations" / "alembic.ini"))
        config.set_main_option("script_location", str(APP_DIR / "migrations"))
        command.upgrade(config, "head")
        UserService.create_user(
            username="fuzz_admin",
            email="fuzz@example.test",
            full_name="Fuzz Admin",
            role_code="ADMINISTRATOR",
            password=PASSWORD,
            actor=None,
        )
        MappingService.seed()
    login = app.test_client()
    assert (
        login.post(
            "/api/v1/auth/login", json={"username": "fuzz_admin", "password": PASSWORD}
        ).status_code
        == 200
    )
    cookie = "; ".join(f"{c.key}={c.value}" for c in login._cookies.values())
    yield schemathesis.from_path(
        str(SPEC), app=SignedIn(app.wsgi_app, cookie), base_url="/api/v1"
    ), app, cookie


schema = schemathesis.from_pytest_fixture("api_schema_only")


@pytest.fixture(scope="module")
def api_schema_only(api_schema):
    return api_schema[0]


def test_the_fuzz_is_really_signed_in(api_schema):
    _schema, app, cookie = api_schema
    seen = []
    for path in ("/api/v1/users", "/api/v1/status-codes", "/api/v1/mapping", "/api/v1/auth/me"):
        client = app.test_client()
        client.set_cookie("session", cookie.split("=", 1)[1])
        seen.append(client.get(path).status_code)
    assert seen == [200, 200, 200, 200], seen  # otherwise every answer would be a 401


@schema.parametrize()
@settings(
    max_examples=5,
    deadline=None,
    derandomize=True,
    database=None,
    suppress_health_check=list(HealthCheck),
)
def test_no_operation_answers_with_a_server_error(case):
    if any(skipped in case.path for skipped in NOT_FUZZED):
        pytest.skip("not fuzzed")
    response = case.call_wsgi()  # call() trips over two bodiless operations inside the library
    assert (
        response.status_code < 500
    ), f"{case.method} {case.path}: {response.status_code} {response.data[:300]!r}"

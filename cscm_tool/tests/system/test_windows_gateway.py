"""The Windows sign-in against a real Windows identity (docs/03-srs.md FR-163, docs/11 SEC-033).

`scripts/windows_gateway.py` stands in for IIS: it authenticates the connection with the operating
system's SSPI (Negotiate / NTLM) and passes the user to the application in a header. These tests run
the real handshake - a client with the credentials of the Windows user who runs the tests against the
gateway's SSPI server side - and then the whole chain: client -> gateway -> application. They run on
Windows only; on other systems the unit tests of the header handling (test_email_and_windows_signin)
are the evidence.

TC-062. Requirements: FR-163, SEC-033.
"""

import base64
import http.client
import os
import re
import sys
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="SSPI exists on Windows only")

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
if sys.platform == "win32":
    import windows_gateway as gateway  # noqa: E402

from werkzeug.serving import make_server  # noqa: E402

from app.services.user_service import UserService  # noqa: E402

WINDOWS_USER = os.environ.get("USERNAME", "").lower()
WINDOWS_IDENTITY = f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}".lower()


def _handshake(package: str) -> "gateway.ServerContext":
    server, client = gateway.ServerContext(package), gateway.ClientContext(package)
    token = client.step(None)
    for _ in range(6):
        out = server.step(token)
        if server.done:
            return server
        token = client.step(out)
    raise AssertionError("the handshake did not finish")


@pytest.mark.parametrize("package", ["NTLM", "Negotiate"])
def test_sspi_names_the_windows_user_who_runs_the_process(package):
    server = _handshake(package)
    assert server.user().lower() == WINDOWS_IDENTITY


@pytest.fixture()
def chain(app):
    """The application (behind the gateway) and the gateway, both on loopback ports."""
    app.config.update(
        AUTH_MODE="windows",
        WINDOWS_AUTH_TRUSTED_PROXIES=("127.0.0.2",),  # the address the gateway connects from
        WINDOWS_AUTH_SIMULATE=False,
        SESSION_COOKIE_SECURE=False,
    )
    with app.app_context():
        UserService.create_user(
            username=WINDOWS_USER,
            email=f"{WINDOWS_USER}@example.com",
            full_name="The Windows User",
            role_code="ENGINEER",
            password="a genuinely long passphrase",
            actor=None,
        )
    upstream = make_server("127.0.0.1", 0, app, threaded=True)
    gateway.Gateway.upstream = ("127.0.0.1", upstream.server_port)
    gateway.Gateway.source = "127.0.0.2"
    front = gateway.ThreadingHTTPServer(("127.0.0.1", 0), gateway.Gateway)
    threads = [
        threading.Thread(target=upstream.serve_forever, daemon=True),
        threading.Thread(target=front.serve_forever, daemon=True),
    ]
    for t in threads:
        t.start()
    yield front.server_port, upstream.server_port
    front.shutdown()
    upstream.shutdown()
    front.server_close()
    upstream.server_close()


def _get(connection, path, headers=None):
    connection.request("GET", path, headers=headers or {})
    response = connection.getresponse()
    return response.status, response.getheader("WWW-Authenticate"), response.read(), response


def _sign_in(port, path="/login/windows", extra=None):
    """Negotiates on one connection (NTLM authenticates the connection) and follows the result."""
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    status, challenge, _, _ = _get(connection, path, extra)
    assert status == 401 and challenge and challenge.startswith("Negotiate")
    client = gateway.ClientContext("Negotiate")
    token = client.step(None)
    cookie = None
    for _ in range(6):
        headers = {
            "Authorization": "Negotiate " + base64.b64encode(token).decode(),
            **(extra or {}),
        }
        status, challenge, body, response = _get(connection, path, headers)
        if status != 401:
            break
        blob = (challenge or "").partition(" ")[2]
        token = client.step(base64.b64decode(blob)) if blob else client.step(None)
    cookie = response.getheader("Set-Cookie")
    return connection, status, body, response, cookie


def test_the_whole_chain_signs_the_windows_user_in(chain, app):
    front, _ = chain
    connection, status, body, response, cookie = _sign_in(front)
    assert status == 302 and response.getheader("Location", "").endswith("/") and cookie
    session = cookie.split(";")[0]
    status, _, body, _ = _get(connection, "/", {"Cookie": session})
    page = body.decode("utf-8")
    assert status == 200 and "The Windows User" in page and "<title>Dashboard" in page
    from app.extensions import db
    from app.models.audit import AuditLogEntry

    with app.app_context():
        entry = db.session.query(AuditLogEntry).filter_by(action="LOGIN_SUCCESS").one()
        assert (
            '"method": "windows"' in entry.after_value
            and '"source": "gateway"' in entry.after_value
        )
        assert WINDOWS_USER in entry.after_value.lower().replace("\\\\", "\\")


def test_a_request_without_credentials_gets_a_challenge_and_never_reaches_the_application(chain):
    front, _ = chain
    connection = http.client.HTTPConnection("127.0.0.1", front, timeout=30)
    status, challenge, body, _ = _get(connection, "/login/windows")
    assert status == 401 and challenge == "Negotiate" and body == b""


def test_a_header_the_client_sends_is_dropped_by_the_gateway(chain):
    front, _ = chain
    connection, status, _, response, cookie = _sign_in(
        front, extra={"X-Remote-User": "someone-else"}
    )
    assert status == 302 and cookie
    _, _, body, _ = _get(connection, "/", {"Cookie": cookie.split(";")[0]})
    assert "The Windows User" in body.decode("utf-8")  # the identity is the real one


def test_the_header_is_ignored_when_it_does_not_come_from_the_trusted_gateway(chain):
    _, upstream = chain
    connection = http.client.HTTPConnection("127.0.0.1", upstream, timeout=30)
    status, _, body, _ = _get(connection, "/login/windows", {"X-Remote-User": WINDOWS_IDENTITY})
    assert status == 401 and "No Windows identity reached the application" in body.decode("utf-8")


def test_an_unknown_windows_user_and_a_deactivated_account_are_refused(chain, app):
    front, _ = chain
    from app.extensions import db
    from app.models.user import User

    with app.app_context():
        db.session.query(User).filter_by(username=WINDOWS_USER).update({"is_active": 0})
        db.session.commit()
    _, status, body, _, cookie = _sign_in(front)
    assert status == 403 and (not cookie or "Max-Age=0" in cookie)  # no session is started
    assert re.search("No active account matches", body.decode("utf-8"))
    with app.app_context():
        db.session.query(User).filter_by(username=WINDOWS_USER).update(
            {"is_active": 1, "username": "someone-else"}
        )  # no account is called like the Windows user now
        db.session.commit()
    _, status, body, _, _ = _sign_in(front)
    assert status == 403

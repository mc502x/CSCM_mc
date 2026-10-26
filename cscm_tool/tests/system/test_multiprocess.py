"""Two real server processes on one database file (docs/14-deployment-architecture.md §3):
the login rate limit (I-20) is shared between them, and concurrent writers serialise on SQLite's
write lock instead of failing. Needs a free local port pair; skipped when sockets are blocked.

TC-050. Requirements: NFR-009.
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from tests.helpers import PASSWORD

APP_DIR = Path(__file__).resolve().parents[2]
SERVE = (
    "import sys; from waitress import serve; from app import create_app; "
    "serve(create_app('development'), host='127.0.0.1', port=int(sys.argv[1]), threads=4)"
)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _post(port: int, path: str, payload: dict, cookie: str | None = None):
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **({"Cookie": cookie} if cookie else {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310  # nosec B310
            return (
                response.status,
                response.headers.get("Set-Cookie"),
                json.loads(response.read() or b"{}"),
            )
    except urllib.error.HTTPError as exc:
        return exc.code, None, json.loads(exc.read() or b"{}")


def _wait_ready(port: int) -> None:
    deadline = time.time() + 40
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/v1/health", timeout=2
            ):  # noqa: S310  # nosec B310
                return
        except OSError:
            time.sleep(0.3)
    raise AssertionError(f"server on port {port} did not start")


@pytest.fixture()
def two_servers(file_app, tmp_path):
    with file_app.app_context():
        from app.services.user_service import UserService

        for name in ("alice", "bob", "carol"):
            UserService.create_user(
                username=name,
                email=f"{name}@example.com",
                full_name=name.title(),
                role_code="ENGINEER",
                password=PASSWORD,
                actor=None,
            )
        database = file_app.config["SQLALCHEMY_DATABASE_URI"]
    env = {
        **os.environ,
        "DATABASE_URL": database,
        "FLASK_ENV": "development",
        "SECRET_KEY": "x" * 40,
        "PYTHONPATH": str(APP_DIR),
    }
    ports = [_free_port(), _free_port()]
    processes = [
        subprocess.Popen(  # noqa: S603  # nosec B603
            [sys.executable, "-c", SERVE, str(p)],
            cwd=APP_DIR,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for p in ports
    ]
    try:
        for p in ports:
            _wait_ready(p)
        yield ports
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


def test_the_username_limit_is_shared_by_both_processes(two_servers):
    first, second = two_servers
    statuses = []
    for attempt in range(5):  # alternate: 3 on one process, 2 on the other
        port = first if attempt % 2 == 0 else second
        statuses.append(
            _post(port, "/api/v1/auth/login", {"username": "alice", "password": "wrong one"})[0]
        )
    assert statuses[:4] == [401] * 4
    assert statuses[4] in (401, 423)  # the 5th failure also locks the account (SEC-004)
    # The sixth attempt is refused by *either* process, even with the right password.
    assert _post(first, "/api/v1/auth/login", {"username": "alice", "password": PASSWORD})[0] == 429
    assert (
        _post(second, "/api/v1/auth/login", {"username": "alice", "password": PASSWORD})[0] == 429
    )


def test_the_ip_limit_is_shared_and_other_users_are_unaffected_until_it_is_reached(two_servers):
    first, second = two_servers
    # 10 attempts from this one address, spread over both processes and several usernames
    for i in range(10):
        port = first if i % 2 == 0 else second
        _post(port, "/api/v1/auth/login", {"username": f"nobody{i}", "password": "wrong one"})
    assert _post(second, "/api/v1/auth/login", {"username": "bob", "password": PASSWORD})[0] == 429
    assert _post(first, "/api/v1/auth/login", {"username": "carol", "password": PASSWORD})[0] == 429


def test_the_limit_survives_a_restart(file_app, two_servers):
    first, _ = two_servers
    for _ in range(5):
        _post(first, "/api/v1/auth/login", {"username": "carol", "password": "wrong one"})
    with file_app.app_context():
        from app.extensions import db
        from app.models.operations import LoginAttempt

        assert db.session.query(LoginAttempt).filter_by(scope="USER", key="carol").count() == 5
        db.session.rollback()


def test_concurrent_writers_in_two_processes_all_succeed(two_servers):
    first, second = two_servers
    status, cookie, _ = _post(
        first, "/api/v1/auth/login", {"username": "bob", "password": PASSWORD}
    )
    assert status == 200
    session = cookie.split(";")[0]
    token = None
    with urllib.request.urlopen(  # noqa: S310  # nosec B310
        urllib.request.Request(
            f"http://127.0.0.1:{first}/api/v1/auth/csrf-token", headers={"Cookie": session}
        )
    ) as response:
        token = json.loads(response.read())["csrf_token"]
        session = response.headers.get("Set-Cookie", session).split(";")[0] or session

    def create(i):
        port = first if i % 2 == 0 else second
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/v1/status-codes",
            data=json.dumps(
                {
                    "functional_system_group": 1,
                    "functional_subgroup": 1,
                    "turbine_platforms": ["3XM"],
                    "title": f"Concurrent write number {i}",
                    "description": "Written by a parallel request in the multi-process test.",
                    "status_category": "ERROR",
                    "available_group": 27,
                    "set_delay": "10ms",
                    "reset_delay": "2min",
                }
            ).encode(),
            headers={"Content-Type": "application/json", "Cookie": session, "X-CSRFToken": token},
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=30
            ) as response:  # noqa: S310  # nosec B310
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(create, range(16)))
    # 16 simultaneous creates through two processes: none may fail with a lock error
    assert statuses.count(201) == 16, statuses

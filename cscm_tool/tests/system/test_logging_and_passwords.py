"""Security policy details from 11-security-architecture.md: §4 password policy
(12 characters, breach block-list, no reuse of the last 5 passwords) and §11
structured JSON logging that never contains credentials."""

import json
import logging

import pytest

from app.auth.password import MIN_PASSWORD_LENGTH, validate_password_policy
from app.domain.errors import PasswordPolicyError
from app.extensions import db
from app.logging_config import JsonFormatter
from app.models.user import User, UserPasswordHistory
from app.services.user_service import PASSWORD_HISTORY_DEPTH, UserService
from tests.helpers import PASSWORD, login_as

NEW = "brand-new passphrase {n} for tests"


# ---- §4 password policy ------------------------------------------------------------------------


def test_policy_length_and_blocklist():
    assert MIN_PASSWORD_LENGTH == 12
    assert validate_password_policy("short")
    for blocked in ("Password123456", "WINDTURBINE123", "1qaz2wsx3edc", "Summer2024!!"):
        assert any("common" in v for v in validate_password_policy(blocked)), blocked
    assert validate_password_policy("a perfectly unusual phrase") == []


def test_blocklist_ignores_comments_and_short_entries():
    from app.auth import password

    assert "# common passwords" not in " ".join(password._COMMON_PASSWORD_BLOCKLIST).lower()
    assert all(len(entry) >= MIN_PASSWORD_LENGTH for entry in password._COMMON_PASSWORD_BLOCKLIST)


def test_last_five_passwords_cannot_be_reused(app, make_user):
    user = make_user("ENGINEER")
    passwords = [PASSWORD] + [NEW.format(n=n) for n in range(1, 7)]
    with app.app_context():
        model = db.session.get(User, user.id)
        # Change through six successive passwords.
        for old, new in zip(passwords, passwords[1:], strict=False):
            UserService.change_own_password(model, old, new)

        # Current + the four most recently retired are blocked...
        for blocked in passwords[-PASSWORD_HISTORY_DEPTH:]:
            with pytest.raises(PasswordPolicyError, match="last 5"):
                UserService.change_own_password(model, passwords[-1], blocked)
        # ...but a password older than that may be used again.
        UserService.change_own_password(model, passwords[-1], passwords[0])
        assert db.session.query(UserPasswordHistory).filter_by(user_id=user.id).count() == 7


def test_administrator_reset_also_honours_history(app, client, make_user):
    admin = make_user("ADMINISTRATOR")
    target = make_user("ENGINEER")
    login_as(client, admin)
    url = f"/api/v1/users/{target.id}/force-reset-password"
    assert client.post(url, json={"new_password": NEW.format(n=1)}).status_code in (200, 204)
    reused = client.post(url, json={"new_password": NEW.format(n=1)})
    assert reused.status_code == 422
    assert client.post(url, json={"new_password": NEW.format(n=2)}).status_code in (200, 204)


def test_only_hashes_are_stored_in_the_history(app, make_user):
    user = make_user("ENGINEER")
    with app.app_context():
        UserService.change_own_password(db.session.get(User, user.id), PASSWORD, NEW.format(n=1))
        row = db.session.query(UserPasswordHistory).one()
        assert row.password_hash.startswith("$argon2")
        assert PASSWORD not in row.password_hash


# ---- §11 structured logging --------------------------------------------------------------------


def test_requests_are_logged_as_json_without_credentials(app, client, make_user, caplog):
    user = make_user("ENGINEER")
    with caplog.at_level(logging.INFO, logger="cscm"):
        client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": PASSWORD},
            query_string={"q": "secret-search-term"},
        )
        client.get("/api/v1/health")

    records = [r for r in caplog.records if r.name == "cscm"]
    assert len(records) >= 2
    lines = [json.loads(JsonFormatter().format(r)) for r in records]
    login = next(line for line in lines if line["path"] == "/api/v1/auth/login")
    assert login["method"] == "POST" and login["status"] == 200
    assert login["request_id"] and isinstance(login["duration_ms"], float)
    blob = " ".join(json.dumps(line) for line in lines)
    assert PASSWORD not in blob
    assert "secret-search-term" not in blob  # query strings are never logged
    assert "session" not in blob.lower() or "session=" not in blob


def test_authenticated_requests_record_the_user_id(app, client, make_user, caplog):
    user = make_user("ENGINEER")
    login_as(client, user)
    with caplog.at_level(logging.INFO, logger="cscm"):
        client.get("/api/v1/auth/me")
    entry = json.loads(JsonFormatter().format(caplog.records[-1]))
    assert entry["user_id"] == user.id


def test_unhandled_errors_are_logged_with_the_request_id(app, client, make_user, caplog):
    from app.api.v1 import api_v1_bp  # noqa: F401  (blueprints already registered)

    admin = make_user("ADMINISTRATOR")
    login_as(client, admin)
    app.config["PROPAGATE_EXCEPTIONS"] = False

    from app.services.audit_service import AuditService

    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    original = AuditService.search
    AuditService.search = staticmethod(boom)  # type: ignore[method-assign]
    try:
        with caplog.at_level(logging.ERROR, logger="cscm"):
            response = client.get("/api/v1/audit-log")
    finally:
        AuditService.search = original  # type: ignore[method-assign]
    assert response.status_code == 500
    error = next(r for r in caplog.records if r.getMessage() == "unhandled exception")
    assert error.path == "/api/v1/audit-log" and error.request_id
    assert "kaboom" in json.loads(JsonFormatter().format(error))["exception"]

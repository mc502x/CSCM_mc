"""The e-mail address of a user is fixed, and the Windows sign-in that will replace the password in a
deployment - simulated on a developer machine (docs/03-srs.md FR-162, FR-163; docs/11 SEC-033).

TC-058. Requirements: FR-162, FR-163, SEC-033, FR-001, FR-010.
"""

import json
import re

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from app import create_app
from app.config import CONFIG_BY_NAME, ProductionConfig
from app.extensions import db
from app.models.audit import AuditLogEntry
from app.models.user import User
from tests.helpers import PASSWORD, login_as, make_cast


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


def _mode(app, mode, **extra):
    app.config["AUTH_MODE"] = mode
    app.config["WINDOWS_AUTH_TRUSTED_PROXIES"] = ("127.0.0.1",)
    app.config.update(extra)


def _as_windows(client, identity, headers=None, **kw):
    return client.post(
        "/api/v1/auth/windows", headers={"X-Remote-User": identity, **(headers or {})}, **kw
    )


# ------------------------------------------------------------------------------ e-mail address
def test_an_address_is_stored_trimmed_and_lower_case_and_must_be_valid_and_new(client, cast):
    login_as(client, cast["admin"])
    body = {
        "username": "mixed",
        "email": "  Mixed.Case@Example.COM ",
        "full_name": "Mixed Case",
        "password": "a genuinely long passphrase",
    }
    created = client.post("/api/v1/users", json=body)
    assert created.status_code == 201 and created.get_json()["email"] == "mixed.case@example.com"
    for bad in ("no-at-sign", "a@b", "a b@c.de", ""):
        refused = client.post(
            "/api/v1/users", json={**body, "username": "x" + str(len(bad)), "email": bad}
        )
        assert refused.status_code == 422, bad
    clash = client.post(
        "/api/v1/users", json={**body, "username": "other", "email": "MIXED.CASE@example.com"}
    )
    assert clash.status_code == 422 and "already in use" in clash.get_json()["message"]


def test_the_address_of_a_user_cannot_be_changed(app, client, cast):
    login_as(client, cast["admin"])
    target = cast["engineer"].id
    for new in ("new@example.com", cast["engineer"].email):  # not even to the same value
        refused = client.patch(f"/api/v1/users/{target}", json={"email": new})
        assert refused.status_code == 422 and "cannot be changed" in refused.get_json()["message"]
    with app.app_context():
        assert db.session.get(User, target).email == cast["engineer"].email


def test_the_database_refuses_a_changed_address_too(app, cast):
    with app.app_context():
        with pytest.raises(DatabaseError, match="cannot be changed"):
            db.session.execute(
                text("UPDATE user SET email = 'x@y.de' WHERE id = :i"), {"i": cast["viewer"].id}
            )
        db.session.rollback()
        db.session.execute(
            text("UPDATE user SET email = email WHERE id = :i"), {"i": cast["viewer"].id}
        )
        db.session.commit()  # writing the same value is not a change


def test_the_screens_show_the_address_as_fixed(client, cast):
    login_as(client, cast["admin"])
    detail = client.get(f"/admin/users/{cast['viewer'].id}").get_data(as_text=True)
    assert cast["viewer"].email in detail and 'name="email"' not in detail
    account = client.get("/account").get_data(as_text=True)
    assert cast["admin"].email in account and "fixed" in account and 'name="email"' not in account


# ------------------------------------------------------------------------------ the mode
def test_with_passwords_only_the_windows_sign_in_is_not_there(app, client, cast):
    assert app.config["AUTH_MODE"] == "password"
    assert client.get("/login/windows").status_code == 404
    refused = _as_windows(client, cast["engineer"].email)
    assert refused.status_code == 403 and refused.get_json()["error"] == "forbidden"
    page = client.get("/login").get_data(as_text=True)
    assert "Sign in with Windows" not in page and 'name="password"' in page


def test_the_gateways_identity_signs_the_matching_account_in_and_is_audited(app, client, cast):
    _mode(app, "windows")
    signed_in = _as_windows(client, cast["engineer"].email.upper())  # case does not matter
    body = signed_in.get_json()
    assert signed_in.status_code == 200 and body["username"] == cast["engineer"].username
    assert client.get("/api/v1/status-codes").status_code == 200  # the session works
    with app.app_context():
        entry = (
            db.session.query(AuditLogEntry)
            .filter_by(action="LOGIN_SUCCESS", entity_id=cast["engineer"].id)
            .order_by(AuditLogEntry.id.desc())
            .first()
        )
        after = json.loads(entry.after_value)
        assert after["method"] == "windows" and after["source"] == "gateway"
        assert db.session.get(User, cast["engineer"].id).last_login_at


def test_a_header_from_an_address_that_is_not_a_trusted_proxy_is_not_believed(app, client, cast):
    _mode(app, "windows")
    app.config["WINDOWS_AUTH_TRUSTED_PROXIES"] = ("10.1.2.3",)  # the test client is 127.0.0.1
    refused = _as_windows(client, cast["admin"].email)
    assert refused.status_code == 401 and refused.get_json()["error"] == "windows_identity_missing"
    assert client.get("/api/v1/users").status_code == 401  # nothing was signed in
    app.config["WINDOWS_AUTH_TRUSTED_PROXIES"] = ()
    assert (
        _as_windows(client, cast["admin"].email).status_code == 401
    )  # and none is trusted by default


def test_no_identity_an_unknown_one_and_a_deactivated_account_are_all_refused(app, client, cast):
    _mode(app, "windows")
    assert client.post("/api/v1/auth/windows").get_json()["error"] == "windows_identity_missing"
    unknown = _as_windows(client, "nobody@example.com")
    assert unknown.status_code == 401 and "No active account" in unknown.get_json()["message"]
    login_as_admin = cast["admin"]
    _mode(app, "both")
    login_as(client, login_as_admin)
    client.patch(f"/api/v1/users/{cast['viewer'].id}", json={"is_active": False})
    client.post("/api/v1/auth/logout")
    _mode(app, "windows")
    assert _as_windows(client, cast["viewer"].email).status_code == 401
    with app.app_context():
        failures = db.session.query(AuditLogEntry).filter_by(action="LOGIN_FAILURE").all()
        assert any(json.loads(f.after_value or "{}").get("method") == "windows" for f in failures)


def test_a_domain_name_is_matched_through_the_mail_domain_or_the_user_name(app, client, cast):
    _mode(app, "windows")
    engineer = cast["engineer"]
    name = engineer.email.split("@")[0]
    # without WINDOWS_AUTH_EMAIL_DOMAIN the user name has to match
    assert _as_windows(client, f"CORP\\{engineer.username}").status_code == 200
    client.post("/api/v1/auth/logout")
    assert _as_windows(client, f"CORP\\{name}").status_code in (200, 401)
    client.post("/api/v1/auth/logout")
    app.config["WINDOWS_AUTH_EMAIL_DOMAIN"] = "example.com"  # CORP\name -> name@example.com
    signed = _as_windows(client, f"CORP\\{name}")
    assert signed.status_code == 200 and signed.get_json()["email"] == engineer.email


def test_with_windows_only_passwords_are_refused_and_the_login_page_says_so(app, client, cast):
    _mode(app, "windows")
    api = client.post(
        "/api/v1/auth/login", json={"username": cast["admin"].username, "password": PASSWORD}
    )
    assert api.status_code == 403 and api.get_json()["error"] == "password_login_disabled"
    redirect = client.get("/login")
    assert redirect.status_code == 302 and "/login/windows" in redirect.headers["Location"]
    posted = client.post("/login", data={"username": cast["admin"].username, "password": PASSWORD})
    assert posted.status_code == 302 and "/login/windows" in posted.headers["Location"]
    assert client.get("/api/v1/status-codes").status_code == 401  # nobody got in
    # and an account with a password session cannot change it: it is managed in Windows
    _as_windows(client, cast["admin"].email)
    assert (
        client.post(
            "/api/v1/users/me/change-password", json={"current_password": "x", "new_password": "y"}
        ).status_code
        == 403
    )
    page = client.get("/account").get_data(as_text=True)
    assert "managed there" in page and 'name="current_password"' not in page


def test_with_both_modes_the_login_page_offers_the_button_and_the_form(app, client):
    _mode(app, "both", WINDOWS_AUTH_SIMULATE=True)
    page = client.get("/login").get_data(as_text=True)
    assert "Sign in with Windows" in page and "simulated" in page and 'name="password"' in page


# ------------------------------------------------------------------------------ the simulation
def test_the_simulation_page_stands_in_for_the_gateway_and_signs_in_by_address(app, client, cast):
    _mode(app, "both", WINDOWS_AUTH_SIMULATE=True)
    page = client.get("/login/windows").get_data(as_text=True)
    assert "Simulation." in page and 'name="identity"' in page
    assert f'<option value="{cast["reviewer"].email}">' in page  # the known accounts are offered
    done = client.post(
        "/login/windows/simulate", data={"identity": cast["reviewer"].email}, follow_redirects=True
    )
    assert done.status_code == 200 and cast["reviewer"].full_name in done.get_data(as_text=True)
    with app.app_context():
        entry = (
            db.session.query(AuditLogEntry)
            .filter_by(action="LOGIN_SUCCESS", entity_id=cast["reviewer"].id)
            .one()
        )
        assert json.loads(entry.after_value)["source"] == "simulation"  # the real code path, marked


def test_the_simulation_refuses_an_unknown_identity_and_is_off_by_default(app, client, cast):
    _mode(app, "both", WINDOWS_AUTH_SIMULATE=True)
    bad = client.post(
        "/login/windows/simulate", data={"identity": "ghost@example.com"}, follow_redirects=True
    )
    assert "No active account matches" in bad.get_data(as_text=True)
    assert client.get("/status-codes").status_code == 302  # still signed out
    assert "Enter the Windows identity" in client.post(
        "/login/windows/simulate", data={"identity": " "}, follow_redirects=True
    ).get_data(as_text=True)
    app.config["WINDOWS_AUTH_SIMULATE"] = False
    assert (
        client.post("/login/windows/simulate", data={"identity": cast["admin"].email}).status_code
        == 404
    )
    page = client.get("/login/windows")
    assert page.status_code == 401 and "No Windows identity reached" in page.get_data(as_text=True)


def test_production_never_starts_with_the_simulation_or_an_unknown_mode(monkeypatch):
    class Prod(ProductionConfig):
        SECRET_KEY = "k" * 40
        SQLALCHEMY_DATABASE_URI = "sqlite://"
        WINDOWS_AUTH_SIMULATE = True

    monkeypatch.setitem(CONFIG_BY_NAME, "production", Prod)
    with pytest.raises(RuntimeError, match="WINDOWS_AUTH_SIMULATE"):
        create_app("production")

    class Bad(ProductionConfig):
        SECRET_KEY = "k" * 40
        SQLALCHEMY_DATABASE_URI = "sqlite://"
        AUTH_MODE = "kerberos"

    monkeypatch.setitem(CONFIG_BY_NAME, "production", Bad)
    with pytest.raises(RuntimeError, match="AUTH_MODE"):
        create_app("production")

    class Good(ProductionConfig):
        SECRET_KEY = "k" * 40
        SQLALCHEMY_DATABASE_URI = "sqlite://"
        AUTH_MODE = "windows"

    monkeypatch.setitem(CONFIG_BY_NAME, "production", Good)
    assert create_app("production").config["WINDOWS_AUTH_SIMULATE"] is False


def test_the_development_defaults_are_the_simulation_next_to_the_password():
    development = create_app("development")
    assert development.config["AUTH_MODE"] == "both" and development.config["WINDOWS_AUTH_SIMULATE"]
    assert not create_app("testing").config["WINDOWS_AUTH_SIMULATE"]


def test_the_shipped_example_configuration_documents_the_settings():
    from pathlib import Path

    example = (Path(__file__).resolve().parents[2] / ".env.example").read_text(encoding="utf-8")
    for name in (
        "AUTH_MODE",
        "WINDOWS_AUTH_HEADER",
        "WINDOWS_AUTH_TRUSTED_PROXIES",
        "WINDOWS_AUTH_EMAIL_DOMAIN",
    ):
        assert re.search(rf"^# {name}=", example, re.M), name

"""TC-017, TC-026, TC-027, SEC-002, SEC-003, SEC-020-SEC-022: injection
resistance and session lifetime/cookie behaviour."""

from datetime import UTC, datetime, timedelta

from app.auth.rate_limit import reset_for_testing
from app.config import ProductionConfig
from app.extensions import db
from app.models.audit import AuditLogEntry
from app.utils import format_iso
from tests.helpers import PASSWORD, create_draft, login_as, make_cast, valid_payload

XSS = "<script>alert(1)</script>"
XSS_ESCAPED = "&lt;script&gt;alert(1)&lt;/script&gt;"


def _ui_login(client, user):
    reset_for_testing()
    client.post("/logout")
    response = client.post("/login", data={"username": user.username, "password": PASSWORD})
    assert response.status_code == 302


def test_user_supplied_text_is_escaped_everywhere_it_renders(app, client, make_user, wcnv_ids):
    """TC-026 / SEC-022."""
    cast = make_cast(make_user)
    revision, cr_id = create_draft(
        app,
        client,
        cast,
        wcnv_ids,
        title=f"Title {XSS}",
        description=f"Description {XSS} that is long enough",
        software_version=XSS,
    )
    login_as(client, cast["admin"])
    client.post(f"/api/v1/change-requests/{cr_id}/comments", json={"comment": f"note {XSS}"})

    _ui_login(client, cast["admin"])
    for path in (
        f"/status-codes/{revision['status_code_id']}",
        f"/status-codes/{revision['status_code_id']}?tab=history",
        "/status-codes",
        f"/change-requests/{cr_id}",
        "/admin/audit-log",
    ):
        html = client.get(path).get_data(as_text=True)
        assert "<script>alert" not in html, path
    detail = client.get(f"/status-codes/{revision['status_code_id']}").get_data(as_text=True)
    assert XSS_ESCAPED in detail
    # ...and the edit form keeps the payload as inert attribute/text content.
    edit = client.get(f"/status-codes/{revision['status_code_id']}/edit").get_data(as_text=True)
    assert "<script>alert" not in edit


def test_sql_injection_probes_have_no_effect(app, client, make_user, wcnv_ids):
    """TC-027 / SEC-021."""
    cast = make_cast(make_user)
    create_draft(app, client, cast, wcnv_ids, title="Findable Converter Code")
    create_draft(app, client, cast, wcnv_ids, title="Another Converter Code")
    login_as(client, cast["engineer"])

    total = client.get("/api/v1/status-codes").get_json()["total"]
    assert total == 2
    probes = ["' OR '1'='1", "'; DROP TABLE status_code; --", "%' OR 1=1 --", '" OR ""="']
    for probe in probes:
        response = client.get("/api/v1/status-codes", query_string={"q": probe})
        assert response.status_code == 200
        assert response.get_json()["total"] == 0, probe
    for param, value in (
        ("sort", "id; DROP TABLE status_code"),
        ("lifecycle_status", "DRAFT' OR '1'='1"),
        ("turbine_platform", "3XM' OR '1'='1"),
    ):
        response = client.get("/api/v1/status-codes", query_string={param: value})
        assert response.status_code == 200
        assert response.get_json()["total"] in (0, total)  # never more than the honest set

    with app.app_context():
        assert db.session.execute(db.text("SELECT COUNT(*) FROM status_code")).scalar() == 2
    found = client.get("/api/v1/status-codes", query_string={"q": "Findable"}).get_json()
    assert found["total"] == 1


def test_audit_log_filters_resist_injection(app, client, make_user):
    admin = make_user("ADMINISTRATOR")
    login_as(client, admin)
    response = client.get(
        "/api/v1/audit-log", query_string={"entity_type": "User' OR '1'='1", "date_from": "x'; --"}
    )
    assert response.status_code in (200, 422)
    if response.status_code == 200:
        assert response.get_json() == []
    with app.app_context():
        assert db.session.query(AuditLogEntry).count() > 0


def test_idle_session_expires_after_thirty_minutes(app, client, make_user):
    """TC-017 / FR-002 / SEC-003."""
    user = make_user("ENGINEER")
    login_as(client, user)
    assert client.get("/api/v1/auth/me").status_code == 200

    with client.session_transaction() as session:
        session["last_activity_at"] = format_iso(datetime.now(UTC) - timedelta(minutes=31))
    assert client.get("/api/v1/auth/me").status_code == 401


def test_recent_activity_keeps_the_session_alive(app, client, make_user):
    user = make_user("ENGINEER")
    login_as(client, user)
    with client.session_transaction() as session:
        session["last_activity_at"] = format_iso(datetime.now(UTC) - timedelta(minutes=29))
    assert client.get("/api/v1/auth/me").status_code == 200


def test_session_expires_at_the_absolute_lifetime(app, client, make_user):
    """SEC-003: 12 hours regardless of activity."""
    user = make_user("ENGINEER")
    login_as(client, user)
    with client.session_transaction() as session:
        session["login_at"] = format_iso(datetime.now(UTC) - timedelta(hours=12, minutes=1))
        session["last_activity_at"] = format_iso(datetime.now(UTC))
    assert client.get("/api/v1/auth/me").status_code == 401


def test_session_cookie_attributes(app, client, make_user):
    """SEC-002 (the Secure flag is off only in the dev/test configs)."""
    assert ProductionConfig.SESSION_COOKIE_SECURE is True
    assert ProductionConfig.SESSION_COOKIE_HTTPONLY is True
    assert ProductionConfig.SESSION_COOKIE_SAMESITE == "Strict"

    user = make_user("ENGINEER")
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie


def test_server_side_validation_ignores_client_side_constraints(app, client, make_user, wcnv_ids):
    """SEC-020: every rule is enforced server-side, whatever the browser did."""
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    bad = client.post(
        "/api/v1/status-codes",
        json=valid_payload(*wcnv_ids, title="", status_category="NOPE", set_delay="10 parsecs"),
    )
    assert bad.status_code == 422
    fields = {e["field"] for e in bad.get_json()["field_errors"]}
    assert {"title", "status_category", "set_delay"} <= fields

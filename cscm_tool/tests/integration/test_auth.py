"""FR-001-FR-004, SEC-001-SEC-004."""

from app.auth.password import hash_password
from app.extensions import db
from app.models.user import User


def test_login_success_returns_user_and_sets_session(client, make_user):
    make_user("ENGINEER", password="a genuinely long passphrase")

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "engineer1", "password": "a genuinely long passphrase"},
    )

    assert response.status_code == 200
    assert response.get_json()["role"] == "ENGINEER"

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.get_json()["username"] == "engineer1"


def test_me_requires_login(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_wrong_password_is_rejected(client, make_user):
    make_user("ENGINEER", password="a genuinely long passphrase")

    response = client.post(
        "/api/v1/auth/login", json={"username": "engineer1", "password": "totally wrong"}
    )

    assert response.status_code == 401


def test_five_failed_attempts_locks_the_account(app, client, make_user):
    """The 5th consecutive failure both locks the account (SEC-004) and
    happens to be the 5th attempt against the username rate limit
    (docs/11-security-architecture.md §5) — both thresholds are 5, so this
    test makes exactly 5 calls to observe SEC-004 before the rate limiter's
    independent 429 would also become reachable on a 6th attempt."""
    user = make_user("ENGINEER", password="a genuinely long passphrase")

    for _ in range(4):
        resp = client.post(
            "/api/v1/auth/login", json={"username": "engineer1", "password": "wrong"}
        )
        assert resp.status_code == 401

    locked_resp = client.post(
        "/api/v1/auth/login", json={"username": "engineer1", "password": "wrong"}
    )
    assert locked_resp.status_code == 423

    with app.app_context():
        from app.extensions import db
        from app.models.user import User

        assert db.session.get(User, user.id).locked_until is not None


def test_logout_invalidates_session(client, make_user):
    make_user("ENGINEER", password="a genuinely long passphrase")
    client.post(
        "/api/v1/auth/login",
        json={"username": "engineer1", "password": "a genuinely long passphrase"},
    )
    assert client.get("/api/v1/auth/me").status_code == 200

    logout_resp = client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 204

    assert client.get("/api/v1/auth/me").status_code == 401


def test_deactivated_user_is_immediately_rejected(app, client, make_user):
    user = make_user("ENGINEER", password="a genuinely long passphrase")
    client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": "a genuinely long passphrase"},
    )
    assert client.get("/api/v1/auth/me").status_code == 200

    with app.app_context():
        db_user = db.session.get(User, user.id)
        db_user.is_active = 0
        db.session.commit()

    assert client.get("/api/v1/auth/me").status_code == 401


def test_password_reset_invalidates_existing_session(app, client, make_user):
    user = make_user("ENGINEER", password="a genuinely long passphrase")
    client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": "a genuinely long passphrase"},
    )
    assert client.get("/api/v1/auth/me").status_code == 200

    with app.app_context():
        db_user = db.session.get(User, user.id)
        db_user.password_hash = hash_password("a completely different passphrase")
        db.session.commit()

    assert client.get("/api/v1/auth/me").status_code == 401

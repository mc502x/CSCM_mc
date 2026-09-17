"""FR-010-FR-014, SEC-003 §3 permission matrix, US-009."""


def _login_as(client, user, password="a genuinely long passphrase"):
    resp = client.post("/api/v1/auth/login", json={"username": user.username, "password": password})
    assert resp.status_code == 200
    return resp


def test_non_admin_cannot_list_users(client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    response = client.get("/api/v1/users")
    assert response.status_code == 403


def test_admin_can_list_and_create_users(client, make_user):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)

    listing = client.get("/api/v1/users")
    assert listing.status_code == 200
    assert listing.get_json()["total"] == 1

    create = client.post(
        "/api/v1/users",
        json={
            "username": "newengineer",
            "email": "newengineer@example.com",
            "full_name": "New Engineer",
            "role": "ENGINEER",
            "password": "a genuinely long passphrase",
            "engineering_domains": ["CONTROLS"],
        },
    )
    assert create.status_code == 201
    body = create.get_json()
    assert body["role"] == "ENGINEER"
    assert body["engineering_domains"] == ["CONTROLS"]


def test_create_user_rejects_weak_password(client, make_user):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)

    response = client.post(
        "/api/v1/users",
        json={
            "username": "weak",
            "email": "weak@example.com",
            "full_name": "Weak Password",
            "role": "VIEWER",
            "password": "short",
        },
    )
    assert response.status_code == 422


def test_cannot_deactivate_last_active_administrator(client, make_user):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)

    response = client.patch(f"/api/v1/users/{admin.id}", json={"is_active": False})
    assert response.status_code == 422
    assert response.get_json()["error"] == "last_administrator"


def test_can_deactivate_administrator_when_another_remains_active(client, make_user):
    admin = make_user("ADMINISTRATOR")
    other_admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)

    response = client.patch(f"/api/v1/users/{other_admin.id}", json={"is_active": False})
    assert response.status_code == 200
    assert response.get_json()["is_active"] is False


def test_self_password_change(client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    response = client.post(
        "/api/v1/users/me/change-password",
        json={
            "current_password": "a genuinely long passphrase",
            "new_password": "a different long passphrase",
        },
    )
    assert response.status_code == 204

    # old password no longer works, new one does
    client.post("/api/v1/auth/logout")
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": engineer.username, "password": "a genuinely long passphrase"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": engineer.username, "password": "a different long passphrase"},
        ).status_code
        == 200
    )


def test_admin_can_force_reset_another_users_password(client, make_user):
    admin = make_user("ADMINISTRATOR")
    engineer = make_user("ENGINEER")
    _login_as(client, admin)

    response = client.post(
        f"/api/v1/users/{engineer.id}/force-reset-password",
        json={"new_password": "an administrator chosen passphrase"},
    )
    assert response.status_code == 204

    login = client.post(
        "/api/v1/auth/login",
        json={"username": engineer.username, "password": "an administrator chosen passphrase"},
    )
    assert login.status_code == 200

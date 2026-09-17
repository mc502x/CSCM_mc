"""FR-070-FR-071: audit log search, Administrator full access,
Reviewer/Chief Engineer scoped to their own actions."""


def _login_as(client, user, password="a genuinely long passphrase"):
    resp = client.post("/api/v1/auth/login", json={"username": user.username, "password": password})
    assert resp.status_code == 200
    return resp


def test_engineer_cannot_view_audit_log(client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)
    assert client.get("/api/v1/audit-log").status_code == 403


def test_admin_sees_all_entries(client, make_user):
    admin = make_user("ADMINISTRATOR")
    make_user("ENGINEER")  # ensures a second USER_CREATE audit entry exists too
    _login_as(client, admin)

    response = client.get("/api/v1/audit-log")
    assert response.status_code == 200
    actions = {e["action"] for e in response.get_json()}
    assert "LOGIN_SUCCESS" in actions


def test_reviewer_only_sees_own_actions(client, make_user):
    reviewer = make_user("REVIEWER")
    admin = make_user("ADMINISTRATOR")

    # Generate an action attributable to admin (creating a user), then one
    # attributable to reviewer (their own login).
    _login_as(client, admin)
    client.post(
        "/api/v1/users",
        json={
            "username": "extra",
            "email": "extra@example.com",
            "full_name": "Extra",
            "role": "VIEWER",
            "password": "a genuinely long passphrase",
        },
    )
    client.post("/api/v1/auth/logout")

    _login_as(client, reviewer)
    response = client.get("/api/v1/audit-log")
    assert response.status_code == 200
    entries = response.get_json()
    assert entries  # at least the reviewer's own LOGIN_SUCCESS
    assert all(e["actor_id"] == reviewer.id for e in entries)


def test_filter_by_entity_type(client, make_user):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)
    client.post(
        "/api/v1/users",
        json={
            "username": "extra2",
            "email": "extra2@example.com",
            "full_name": "Extra Two",
            "role": "VIEWER",
            "password": "a genuinely long passphrase",
        },
    )

    response = client.get("/api/v1/audit-log?entity_type=User")
    entries = response.get_json()
    assert entries
    assert all(e["entity_type"] == "User" for e in entries)
    assert any(e["action"] == "USER_CREATE" for e in entries)

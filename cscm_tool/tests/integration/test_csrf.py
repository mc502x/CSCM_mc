"""docs/11-security-architecture.md §5: CSRF synchronizer-token protection
on all state-changing requests. TestingConfig disables CSRF by default
(docs/15-development-standards.md §7 wants deterministic, low-friction
tests) so this file explicitly re-enables it to verify the real behavior."""


def test_state_changing_request_without_csrf_token_is_rejected(app, client, make_user):
    admin = make_user("ADMINISTRATOR")
    app.config["WTF_CSRF_ENABLED"] = True
    client.post(
        "/api/v1/auth/login",
        json={"username": admin.username, "password": "a genuinely long passphrase"},
    )

    response = client.patch(f"/api/v1/users/{admin.id}", json={"full_name": "Renamed"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "csrf_error"


def test_state_changing_request_with_csrf_token_succeeds(app, client, make_user):
    admin = make_user("ADMINISTRATOR")
    app.config["WTF_CSRF_ENABLED"] = True
    client.post(
        "/api/v1/auth/login",
        json={"username": admin.username, "password": "a genuinely long passphrase"},
    )

    token = client.get("/api/v1/auth/csrf-token").get_json()["csrf_token"]
    response = client.patch(
        f"/api/v1/users/{admin.id}",
        json={"full_name": "Renamed"},
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 200
    assert response.get_json()["full_name"] == "Renamed"

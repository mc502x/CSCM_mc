"""FR-020-FR-029, FR-053-FR-056, FR-060-FR-064."""


def _login_as(client, user, password="a genuinely long passphrase"):
    resp = client.post("/api/v1/auth/login", json={"username": user.username, "password": password})
    assert resp.status_code == 200
    return resp


def _valid_payload(**overrides):
    payload = {
        "functional_system_group": "WCNV",
        "turbine_platforms": ["3XM"],
        "title": "Converter Grid Undervoltage Trip",
        "description": "Triggered when converter DC-link voltage falls below threshold.",
        "status_category": "FAULT",
        "availability_group": "A",
        "reset_program": "MANUAL",
        "software_version": "4.12.0",
        "operational_state": "STOPPED",
        "alarm_behaviour": "SELF_CLEARING",
    }
    payload.update(overrides)
    return payload


def test_engineer_can_create_draft_with_no_identifier(client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    response = client.post("/api/v1/status-codes", json=_valid_payload())

    assert response.status_code == 201
    body = response.get_json()
    assert body["status_code_identifier"] is None
    assert body["lifecycle_status"] == "DRAFT"
    assert body["turbine_platforms"] == ["3XM"]


def test_viewer_cannot_create_status_code(client, make_user):
    viewer = make_user("VIEWER")
    _login_as(client, viewer)

    response = client.post("/api/v1/status-codes", json=_valid_payload())
    assert response.status_code == 403


def test_create_rejects_invalid_fields(client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    response = client.post("/api/v1/status-codes", json=_valid_payload(software_version="bad"))
    assert response.status_code == 422
    assert any(fe["field"] == "software_version" for fe in response.get_json()["field_errors"])


def test_non_admin_cannot_create_sandbox(client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    response = client.post("/api/v1/status-codes", json=_valid_payload(is_sandbox=True))
    assert response.status_code == 403


def test_admin_sandbox_gets_identifier_immediately(client, make_user):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)

    response = client.post("/api/v1/status-codes", json=_valid_payload(is_sandbox=True))
    assert response.status_code == 201
    body = response.get_json()
    assert body["status_code_identifier"].startswith("StCd-T")
    assert body["is_sandbox"] is True


def test_sandbox_delete_requires_admin_and_sandbox_flag(client, make_user):
    admin = make_user("ADMINISTRATOR")
    engineer = make_user("ENGINEER")
    _login_as(client, admin)
    sandbox = client.post("/api/v1/status-codes", json=_valid_payload(is_sandbox=True)).get_json()
    real_draft = client.post("/api/v1/status-codes", json=_valid_payload()).get_json()

    # Engineer cannot delete at all.
    _login_as(client, engineer)
    assert client.delete(f"/api/v1/status-codes/{sandbox['status_code_id']}").status_code == 403

    # Administrator cannot delete a non-sandbox record.
    _login_as(client, admin)
    assert client.delete(f"/api/v1/status-codes/{real_draft['status_code_id']}").status_code == 403

    # Administrator can delete the sandbox record.
    delete_resp = client.delete(f"/api/v1/status-codes/{sandbox['status_code_id']}")
    assert delete_resp.status_code == 204
    assert client.get(f"/api/v1/status-codes/{sandbox['status_code_id']}").status_code == 404


def test_search_defaults_exclude_sandbox(client, make_user):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)
    client.post("/api/v1/status-codes", json=_valid_payload(is_sandbox=True))
    client.post("/api/v1/status-codes", json=_valid_payload())

    response = client.get("/api/v1/status-codes")
    body = response.get_json()
    assert body["total"] == 1
    assert body["items"][0]["is_sandbox"] is False


def test_viewer_cannot_see_draft_status_codes(client, make_user):
    engineer = make_user("ENGINEER")
    viewer = make_user("VIEWER")
    _login_as(client, engineer)
    created = client.post("/api/v1/status-codes", json=_valid_payload()).get_json()

    _login_as(client, viewer)
    assert client.get(f"/api/v1/status-codes/{created['status_code_id']}").status_code == 404
    assert client.get("/api/v1/status-codes").get_json()["total"] == 0

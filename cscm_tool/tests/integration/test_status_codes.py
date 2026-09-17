"""FR-020-FR-029, FR-053-FR-056, FR-060-FR-064."""


def _login_as(client, user, password="a genuinely long passphrase"):
    resp = client.post("/api/v1/auth/login", json={"username": user.username, "password": password})
    assert resp.status_code == 200
    return resp


def _valid_payload(group_id, subgroup_id, **overrides):
    payload = {
        "functional_system_group": group_id,
        "functional_subgroup": subgroup_id,
        "turbine_platforms": ["3XM"],
        "title": "Converter Grid Undervoltage Trip",
        "description": "Triggered when converter DC-link voltage falls below threshold.",
        "status_category": "ERROR",
        "available_group": 27,
        "set_delay": "10ms",
        "reset_delay": "2min",
    }
    payload.update(overrides)
    return payload


def test_engineer_can_create_draft_with_no_identifier(client, make_user, wcnv_ids):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    response = client.post("/api/v1/status-codes", json=_valid_payload(*wcnv_ids))

    assert response.status_code == 201
    body = response.get_json()
    assert body["status_code_identifier"] is None
    assert body["lifecycle_status"] == "DRAFT"
    assert body["turbine_platforms"] == ["3XM"]
    assert body["functional_subgroup_id"] == wcnv_ids[1]


def test_viewer_cannot_create_status_code(client, make_user, wcnv_ids):
    viewer = make_user("VIEWER")
    _login_as(client, viewer)

    response = client.post("/api/v1/status-codes", json=_valid_payload(*wcnv_ids))
    assert response.status_code == 403


def test_create_rejects_invalid_fields(client, make_user, wcnv_ids):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    response = client.post("/api/v1/status-codes", json=_valid_payload(*wcnv_ids, set_delay="bad"))
    assert response.status_code == 422
    assert any(fe["field"] == "set_delay" for fe in response.get_json()["field_errors"])


def test_create_rejects_missing_functional_subgroup(client, make_user, wcnv_ids):
    """BR-013: mandatory, never optional (corrected 2026-09-17)."""
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    payload = _valid_payload(*wcnv_ids)
    del payload["functional_subgroup"]
    response = client.post("/api/v1/status-codes", json=payload)
    assert response.status_code == 422


def test_non_admin_cannot_create_sandbox(client, make_user, wcnv_ids):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    response = client.post("/api/v1/status-codes", json=_valid_payload(*wcnv_ids, is_sandbox=True))
    assert response.status_code == 403


def test_admin_sandbox_gets_identifier_immediately(client, make_user, wcnv_ids):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)

    response = client.post("/api/v1/status-codes", json=_valid_payload(*wcnv_ids, is_sandbox=True))
    assert response.status_code == 201
    body = response.get_json()
    assert body["status_code_identifier"].startswith("StCd-T")
    assert body["is_sandbox"] is True


def test_sandbox_delete_requires_admin_and_sandbox_flag(client, make_user, wcnv_ids):
    admin = make_user("ADMINISTRATOR")
    engineer = make_user("ENGINEER")
    _login_as(client, admin)
    sandbox = client.post(
        "/api/v1/status-codes", json=_valid_payload(*wcnv_ids, is_sandbox=True)
    ).get_json()
    real_draft = client.post("/api/v1/status-codes", json=_valid_payload(*wcnv_ids)).get_json()

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


def test_search_defaults_exclude_sandbox(client, make_user, wcnv_ids):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)
    client.post("/api/v1/status-codes", json=_valid_payload(*wcnv_ids, is_sandbox=True))
    client.post("/api/v1/status-codes", json=_valid_payload(*wcnv_ids))

    response = client.get("/api/v1/status-codes")
    body = response.get_json()
    assert body["total"] == 1
    assert body["items"][0]["is_sandbox"] is False


def test_viewer_cannot_see_draft_status_codes(client, make_user, wcnv_ids):
    engineer = make_user("ENGINEER")
    viewer = make_user("VIEWER")
    _login_as(client, engineer)
    created = client.post("/api/v1/status-codes", json=_valid_payload(*wcnv_ids)).get_json()

    _login_as(client, viewer)
    assert client.get(f"/api/v1/status-codes/{created['status_code_id']}").status_code == 404
    assert client.get("/api/v1/status-codes").get_json()["total"] == 0

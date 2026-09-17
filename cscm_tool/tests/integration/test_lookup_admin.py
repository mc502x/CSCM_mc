"""US-091: Administrator manages controlled vocabularies. docs/05-governance-
handbook.md §3."""


def _login_as(client, user, password="a genuinely long passphrase"):
    resp = client.post("/api/v1/auth/login", json={"username": user.username, "password": password})
    assert resp.status_code == 200
    return resp


def test_non_admin_cannot_create_lookup_value(client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)
    response = client.post(
        "/api/v1/lookups/turbine-platforms", json={"code": "5XM", "label": "5XM Platform"}
    )
    assert response.status_code == 403


def test_admin_can_add_turbine_platform(client, make_user):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)

    response = client.post(
        "/api/v1/lookups/turbine-platforms", json={"code": "5XM", "label": "5XM Platform"}
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["code"] == "5XM"
    assert body["is_active"] is True

    listing = client.get("/api/v1/lookups/turbine-platforms").get_json()
    assert any(p["code"] == "5XM" for p in listing)


def test_cannot_create_functional_system_group(client, make_user):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)
    response = client.post(
        "/api/v1/lookups/functional-system-groups",
        json={"code": "WNEW", "label": "New Group"},
    )
    assert response.status_code == 422


def test_duplicate_code_rejected(client, make_user):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)
    response = client.post(
        "/api/v1/lookups/turbine-platforms", json={"code": "3XM", "label": "Duplicate"}
    )
    assert response.status_code == 422


def test_admin_can_deactivate_and_relabel_a_value(client, make_user):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)
    created = client.post(
        "/api/v1/lookups/turbine-platforms", json={"code": "5XM", "label": "5XM Platform"}
    ).get_json()

    response = client.patch(
        f"/api/v1/lookups/turbine-platforms/{created['id']}",
        json={"label": "5XM Platform (renamed)", "is_active": False},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["label"] == "5XM Platform (renamed)"
    assert body["is_active"] is False

    active_only = client.get("/api/v1/lookups/turbine-platforms").get_json()
    assert not any(p["code"] == "5XM" for p in active_only)


def test_create_functional_subgroup_with_range(client, make_user):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)
    response = client.post(
        "/api/v1/lookups/functional-subgroups",
        json={
            "code": "WCNV-4",
            "label": "Subgroup 4 (real taxonomy)",
            "functional_system_group": "WCNV",
            "sub_range_start": 1900,
            "sub_range_end": 1999,
        },
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["functional_system_group"] == "WCNV"
    assert body["range_start"] == 1900
    assert body["range_end"] == 1999

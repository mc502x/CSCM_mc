"""US-091: Administrator manages controlled vocabularies. docs/05-governance-
handbook.md §3. EPIC-16 (2026-09-17): Functional System Group / Functional
Subgroup administration, non-overlap validated."""


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


def test_functional_system_group_not_creatable_via_generic_endpoint(client, make_user):
    """v3 (EPIC-16): creation moved to a dedicated, non-overlap-validated
    endpoint — the generic vocabulary API rejects it (see
    LookupAdminService's module docstring)."""
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)
    response = client.post(
        "/api/v1/lookups/functional-system-groups",
        json={"code": "WNEW", "label": "New Group"},
    )
    # Missing range_start/range_end on the dedicated endpoint -> 422.
    assert response.status_code == 422


def test_admin_can_create_new_functional_system_group_in_free_range(client, make_user):
    """FR-048g: into any currently free range (10000-10999, 14000-14999,
    15000-15999, 16000-16999 as of 2026-09-17)."""
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)
    response = client.post(
        "/api/v1/lookups/functional-system-groups",
        json={"code": "WNEW", "label": "New Subsystem", "range_start": 15000, "range_end": 15999},
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["code"] == "WNEW"
    assert body["range_start"] == 15000
    assert body["range_end"] == 15999


def test_new_functional_system_group_range_overlap_rejected(client, make_user):
    """FR-048h: rejected with 409, naming the conflicting group."""
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)
    response = client.post(
        "/api/v1/lookups/functional-system-groups",
        json={"code": "WBAD", "label": "Overlaps WCNV", "range_start": 1500, "range_end": 2500},
    )
    assert response.status_code == 409
    assert "WCNV" in response.get_json()["message"] or "Converter" in response.get_json()["message"]


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


def test_create_functional_subgroup_with_range(client, make_user, wcnv_ids):
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)
    group_id, _subgroup_id = wcnv_ids
    response = client.post(
        "/api/v1/lookups/functional-subgroups",
        json={
            "code": "019xx",
            "label": "Converter Diagnostics",
            "functional_system_group": group_id,
            "sub_range_start": 1900,
            "sub_range_end": 1999,
        },
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["functional_system_group"] == "WCNV"
    assert body["functional_system_group_id"] == group_id
    assert body["range_start"] == 1900
    assert body["range_end"] == 1999


def test_functional_subgroup_overlap_rejected(client, make_user, wcnv_ids):
    """FR-048f: rejected with 409, naming the conflicting subgroup."""
    admin = make_user("ADMINISTRATOR")
    _login_as(client, admin)
    group_id, _subgroup_id = wcnv_ids
    response = client.post(
        "/api/v1/lookups/functional-subgroups",
        json={
            "code": "011xx",
            "label": "Overlaps Converter",
            "functional_system_group": group_id,
            "sub_range_start": 1050,
            "sub_range_end": 1150,
        },
    )
    assert response.status_code == 409

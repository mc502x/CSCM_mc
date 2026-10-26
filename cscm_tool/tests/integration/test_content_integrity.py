"""I-01 optimistic concurrency, I-04 reference warnings and where-used, I-12 duplicate
warnings, I-14 troubleshooting content, I-25 platform variants, I-27 planned dates and the
I-19 capacity hint (docs/21-improvement-ideas.md).

TC-039. Requirements: FR-090, FR-091, FR-092, FR-093, FR-094, FR-109, FR-131, FR-141, BR-019.
"""

from datetime import UTC, datetime, timedelta

from tests.helpers import (
    cr_id_for_revision,
    create_draft,
    decide,
    domain_sign,
    drive_to_approved,
    login_as,
    make_cast,
    release_revisions,
    submit,
    valid_payload,
)


def _released(app, client, cast, wcnv_ids, **overrides):
    revision, cr_id = drive_to_approved(app, client, cast, wcnv_ids, **overrides)
    release_revisions(client, cast, [revision["id"]], label=f"v-{revision['id']}")
    return client.get(f"/api/v1/status-codes/{revision['status_code_id']}").get_json()


# ---------------------------------------------------------------- I-01
def test_stale_save_is_refused_with_the_current_values(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, _ = create_draft(app, client, cast, wcnv_ids)
    assert revision["row_version"] == 1
    body = {**valid_payload(*wcnv_ids), "expected_row_version": 1}

    login_as(client, cast["admin"])  # the Administrator may edit the author's Draft too
    first = client.patch(
        f"/api/v1/revisions/{revision['id']}", json={**body, "title": "Admin edit"}
    )
    assert first.status_code == 200
    assert first.get_json()["row_version"] == 2

    login_as(client, cast["engineer"])
    stale = client.patch(f"/api/v1/revisions/{revision['id']}", json={**body, "title": "My edit"})
    assert stale.status_code == 409
    payload = stale.get_json()
    assert payload["error"] == "conflict"
    assert payload["current_row_version"] == 2
    assert payload["current"]["title"] == "Admin edit"  # nothing was overwritten

    retry = client.patch(
        f"/api/v1/revisions/{revision['id']}",
        json={**body, "title": "My edit", "expected_row_version": 2},
    )
    assert retry.status_code == 200 and retry.get_json()["title"] == "My edit"


def test_expected_updated_at_is_enforced_too(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, _ = create_draft(app, client, cast, wcnv_ids)
    body = valid_payload(*wcnv_ids)
    ok = client.patch(
        f"/api/v1/revisions/{revision['id']}",
        json={**body, "expected_updated_at": revision["updated_at"], "title": "A"},
    )
    assert ok.status_code == 200
    stale = client.patch(
        f"/api/v1/revisions/{revision['id']}",
        json={**body, "expected_updated_at": revision["updated_at"], "title": "B"},
    )
    assert stale.status_code == 409


def test_save_without_a_version_still_works_for_old_clients(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, _ = create_draft(app, client, cast, wcnv_ids)
    response = client.patch(
        f"/api/v1/revisions/{revision['id']}", json={**valid_payload(*wcnv_ids), "title": "Legacy"}
    )
    assert response.status_code == 200


def test_ui_stale_edit_keeps_the_users_entries_and_shows_the_conflict(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    revision, _ = create_draft(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    page = client.get(f"/status-codes/{revision['status_code_id']}/edit").get_data(as_text=True)
    assert 'name="row_version"' in page

    client.patch(
        f"/api/v1/revisions/{revision['id']}",
        json={**valid_payload(*wcnv_ids), "title": "Changed elsewhere"},
    )
    form = {
        "functional_system_group": wcnv_ids[0],
        "functional_subgroup": wcnv_ids[1],
        "turbine_platforms": "3XM",
        "title": "My unsaved title",
        "description": "Triggered when converter DC-link voltage falls below threshold.",
        "status_category": "ERROR",
        "available_group": "27",
        "set_delay": "10ms",
        "reset_delay": "2min",
        "row_version": "1",
    }
    response = client.post(f"/status-codes/{revision['status_code_id']}/edit", data=form)
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "My unsaved title" in html  # NFR-007a: entries are kept
    assert "changed by someone else" in html
    assert "Changed elsewhere" in html  # the current stored value is shown next to it


# ---------------------------------------------------------------- I-04
def test_unknown_escalation_number_warns_but_does_not_block(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    response = client.post(
        "/api/v1/status-codes",
        json=valid_payload(*wcnv_ids, status_code_for_repeated_error=424242),
    )
    assert response.status_code == 201
    warnings = response.get_json()["warnings"]
    assert [w["type"] for w in warnings] == ["UNKNOWN_REFERENCE"]
    assert "external escalation" in warnings[0]["message"]


def test_reference_to_a_deprecated_code_warns(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    target = _released(app, client, cast, wcnv_ids)
    number = int(target["status_code_identifier"][5:])

    login_as(client, cast["engineer"])
    deprecation = client.post(
        f"/api/v1/status-codes/{target['status_code_id']}/deprecation-requests",
        json={"reason": "Replaced by a better code for the same fault."},
    )
    assert deprecation.status_code == 201
    cr_id = cr_id_for_revision(app, deprecation.get_json()["id"])
    domain_sign(client, cast, cr_id)
    assert submit(client, cast, cr_id).status_code == 200
    decide(client, cast["reviewer"], cr_id, "reviewer-signoff")
    decide(client, cast["admin"], cr_id, "admin-signoff")
    final = decide(client, cast["chief_engineer"], cr_id, "chief-engineer-decide")
    assert final.get_json()["state"] == "APPROVED"

    login_as(client, cast["engineer"])
    response = client.post(
        "/api/v1/status-codes",
        json=valid_payload(*wcnv_ids, title="Another code", status_code_for_repeated_error=number),
    )
    assert any(w["type"] == "DEPRECATED_REFERENCE" for w in response.get_json()["warnings"])


def test_where_used_lists_dependants_and_deprecation_needs_acknowledgement(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    target = _released(app, client, cast, wcnv_ids)
    number = int(target["status_code_identifier"][5:])
    login_as(client, cast["engineer"])
    client.post(
        "/api/v1/status-codes",
        json=valid_payload(
            *wcnv_ids,
            title="Depends on the first",
            description="A second code whose repeat escalation points at the first.",
            status_code_for_repeated_error=number,
            number_of_times_repeated=3,
        ),
    )
    used = client.get(f"/api/v1/status-codes/{target['status_code_id']}/where-used").get_json()
    assert [(u["relation"], u["title"]) for u in used["items"]] == [
        ("REPEATED_ERROR", "Depends on the first")
    ]

    refused = client.post(
        f"/api/v1/status-codes/{target['status_code_id']}/deprecation-requests",
        json={"reason": "No longer needed by anyone at all."},
    )
    assert refused.status_code == 422
    assert refused.get_json()["field_errors"][0]["field"] == "acknowledge_dependants"

    accepted = client.post(
        f"/api/v1/status-codes/{target['status_code_id']}/deprecation-requests",
        json={"reason": "No longer needed by anyone at all.", "acknowledge_dependants": True},
    )
    assert accepted.status_code == 201


def test_related_codes_are_validated_and_checked(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    bad = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, related_status_codes="not-a-code")
    )
    assert bad.status_code == 422
    good = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, related_status_codes="StCd-99999")
    )
    assert good.status_code == 201
    assert good.get_json()["related_status_codes"] == "StCd-99999"
    assert any(w["field"] == "related_status_codes" for w in good.get_json()["warnings"])


# ---------------------------------------------------------------- I-12
def test_similar_title_in_the_subgroup_is_flagged_not_blocked(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, title="Grid undervoltage trip")
    )
    second = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, title="Grid under-voltage trip!")
    )
    assert second.status_code == 201
    assert [w["type"] for w in second.get_json()["warnings"]] == ["POSSIBLE_DUPLICATE"]

    unrelated = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, title="Fan motor overtemperature")
    )
    assert unrelated.get_json()["warnings"] == []


def test_similar_endpoint_supports_the_did_you_mean_hint(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, title="Converter overcurrent")
    )
    hits = client.get(
        f"/api/v1/status-codes/similar?title=Converter%20overcurrent&functional_subgroup={wcnv_ids[1]}"
    ).get_json()["items"]
    assert len(hits) == 1 and hits[0]["score"] == 1.0
    assert client.get("/api/v1/status-codes/similar?title=x").status_code == 422


# ---------------------------------------------------------------- I-14
def test_troubleshooting_fields_round_trip_and_reach_the_export(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision = _released(
        app,
        client,
        cast,
        wcnv_ids,
        remedy_text="Check the DC-link fuses, then reset the converter.",
        affected_component="DC link",
        standard_references="IEC 61400-25",
    )
    assert revision["remedy_text"].startswith("Check the DC-link")
    assert revision["affected_component"] == "DC link"
    login_as(client, cast["viewer"])
    body = client.get("/api/v1/exports/released?format=json").get_json()
    assert body[0]["remedy_text"].startswith("Check the DC-link")
    assert body[0]["standard_references"] == "IEC 61400-25"


def test_remedy_text_length_is_validated(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    response = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, remedy_text="x" * 4001)
    )
    assert response.status_code == 422


# ---------------------------------------------------------------- I-25
def test_platform_variant_copies_the_code_and_links_the_family(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    source = _released(app, client, cast, wcnv_ids, remedy_text="Reset the converter.")
    login_as(client, cast["engineer"])
    created = client.post(
        f"/api/v1/status-codes/{source['status_code_id']}/platform-variants",
        json={"turbine_platform": "4XM"},
    )
    assert created.status_code == 201
    variant = created.get_json()
    assert variant["turbine_platforms"] == ["4XM"]
    assert variant["lifecycle_status"] == "DRAFT"
    assert variant["platform_variant_of_status_code_id"] == source["status_code_id"]
    assert variant["remedy_text"] == "Reset the converter."
    assert variant["status_code_identifier"] is None  # allocated at submit like any new code

    family = client.get(f"/api/v1/status-codes/{variant['status_code_id']}/family").get_json()[
        "items"
    ]
    assert [m["status_code_id"] for m in family] == [
        source["status_code_id"],
        variant["status_code_id"],
    ]

    again = client.post(
        f"/api/v1/status-codes/{source['status_code_id']}/platform-variants",
        json={"turbine_platform": "4XM"},
    )
    assert again.status_code == 422  # 4XM is already covered by the family
    same = client.post(
        f"/api/v1/status-codes/{source['status_code_id']}/platform-variants",
        json={"turbine_platform": "3XM"},
    )
    assert same.status_code == 422  # the source already applies to 3XM


def test_variant_needs_a_decided_source_and_an_engineer(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    draft, _ = create_draft(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    assert (
        client.post(
            f"/api/v1/status-codes/{draft['status_code_id']}/platform-variants",
            json={"turbine_platform": "4XM"},
        ).status_code
        == 409
    )
    login_as(client, cast["viewer"])
    assert (
        client.post(
            f"/api/v1/status-codes/{draft['status_code_id']}/platform-variants",
            json={"turbine_platform": "4XM"},
        ).status_code
        == 403
    )


# ---------------------------------------------------------------- I-27
def test_planned_dates_are_administrator_set_audited_and_warn_at_publish(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids)
    future = (datetime.now(UTC) + timedelta(days=30)).date().isoformat()
    later = (datetime.now(UTC) + timedelta(days=400)).date().isoformat()

    login_as(client, cast["engineer"])
    assert (
        client.put(
            f"/api/v1/status-codes/{revision['status_code_id']}/planned-dates",
            json={"planned_effective_date": future},
        ).status_code
        == 403
    )
    login_as(client, cast["admin"])
    ok = client.put(
        f"/api/v1/status-codes/{revision['status_code_id']}/planned-dates",
        json={"planned_effective_date": future, "planned_deprecation_date": later},
    )
    assert ok.status_code == 200
    assert ok.get_json()["planned_effective_date"] == future
    bad = client.put(
        f"/api/v1/status-codes/{revision['status_code_id']}/planned-dates",
        json={"planned_effective_date": later, "planned_deprecation_date": future},
    )
    assert bad.status_code == 422
    junk = client.put(
        f"/api/v1/status-codes/{revision['status_code_id']}/planned-dates",
        json={"planned_effective_date": "next week"},
    )
    assert junk.status_code == 422

    release = client.post("/api/v1/releases", json={"name": "R", "version_label": "v1"}).get_json()
    client.put(
        f"/api/v1/releases/{release['id']}/items",
        json={"status_code_revision_ids": [revision["id"]]},
    )
    published = client.post(f"/api/v1/releases/{release['id']}/publish")
    assert published.status_code == 200  # a warning, never a block
    assert published.get_json()["warnings"][0]["type"] == "FUTURE_EFFECTIVE_DATE"

    audit = client.get("/api/v1/audit-log?action=PLANNED_DATES_SET").get_json()
    assert len(audit) == 1


# ---------------------------------------------------------------- I-19 capacity hint
def test_next_available_reports_how_many_numbers_are_left(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    hint = client.get(
        f"/api/v1/status-codes/next-available?functional_system_group={wcnv_ids[0]}"
        f"&functional_subgroup={wcnv_ids[1]}"
    ).get_json()
    capacity = hint["capacity"]
    assert hint["preview_identifier"] == "StCd-01000"
    assert (capacity["range_start"], capacity["range_end"]) == (1000, 1199)
    assert capacity["remaining"] == 200 and capacity["allocated"] == 0

    drive_to_approved(app, client, cast, wcnv_ids)  # allocates StCd-01000
    login_as(client, cast["engineer"])
    hint = client.get(
        f"/api/v1/status-codes/next-available?functional_system_group={wcnv_ids[0]}"
        f"&functional_subgroup={wcnv_ids[1]}"
    ).get_json()
    assert hint["preview_identifier"] == "StCd-01001"
    assert hint["capacity"]["remaining"] == 199 and hint["capacity"]["allocated"] == 1

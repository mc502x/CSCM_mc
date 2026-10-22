"""EPIC-11 / FR-080: the code and docs/artifacts/openapi.yaml describe the
same API — every documented operation exists, every implemented operation is
documented, and live payloads only use properties the contract declares."""

import re
from pathlib import Path

import pytest
import yaml

from tests.helpers import create_draft, drive_to_review, login_as, make_cast

SPEC = yaml.safe_load(
    (Path(__file__).resolve().parents[3] / "docs" / "artifacts" / "openapi.yaml").read_text(
        encoding="utf-8"
    )
)
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _spec_operations() -> set[tuple[str, str]]:
    return {
        (method.upper(), re.sub(r"\{[^}]+\}", "{}", path))
        for path, item in SPEC["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }


def _flask_operations(app) -> set[tuple[str, str]]:
    operations = set()
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api/v1/"):
            continue
        path = re.sub(r"<[^>]+>", "{}", rule.rule[len("/api/v1") :])
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            operations.add((method, path))
    return operations


def test_every_documented_operation_is_implemented_and_vice_versa(app):
    documented = _spec_operations()
    implemented = _flask_operations(app)
    assert documented - implemented == set(), "documented but not implemented"
    assert implemented - documented == set(), "implemented but not documented"


def _declared(schema_name: str) -> set[str]:
    schema = SPEC["components"]["schemas"][schema_name]
    props = set(schema.get("properties", {}))
    for part in schema.get("allOf", []):
        if "$ref" in part:
            props |= _declared(part["$ref"].rsplit("/", 1)[-1])
        props |= set(part.get("properties", {}))
    return props


@pytest.fixture()
def populated(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    return cast, revision, cr_id


def test_live_payloads_only_use_declared_properties(app, client, populated):
    cast, revision, cr_id = populated
    login_as(client, cast["admin"])
    release = client.post("/api/v1/releases", json={"name": "R", "version_label": "v1"}).get_json()

    checks = {
        "StatusCodeRevision": client.get(
            f"/api/v1/status-codes/{revision['status_code_id']}"
        ).get_json(),
        "ChangeRequest": client.get(f"/api/v1/change-requests/{cr_id}").get_json(),
        "Release": release,
        "User": client.get("/api/v1/auth/me").get_json(),
    }
    problems = []
    for schema_name, payload in checks.items():
        extra = set(payload) - _declared(schema_name)
        if extra:
            problems.append(f"{schema_name}: undeclared {sorted(extra)}")
    assert problems == []


def test_revision_diff_payload_matches_contract(app, client, populated):
    cast, revision, _ = populated
    login_as(client, cast["engineer"])
    diff = client.get(
        f"/api/v1/status-codes/{revision['status_code_id']}/revisions/1/diff/1"
    ).get_json()
    assert set(diff) == _declared("RevisionDiff")


def test_lookup_and_domain_request_payloads_match_contract(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = create_draft(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])

    lookup = client.get("/api/v1/lookups/development-access").get_json()[0]
    assert set(lookup) <= _declared("LookupValue")

    created = client.post(
        f"/api/v1/change-requests/{cr_id}/domain-signoff-requests",
        json={"engineering_domain": "CONTROLS"},
    ).get_json()
    assert set(created) == _declared("DomainSignoffRequest")


def test_unauthenticated_requests_are_rejected_for_every_documented_operation(app, client):
    skip = {"/auth/login", "/auth/csrf-token", "/health"}
    failures = []
    for method, path in sorted(_spec_operations()):
        if path in skip:
            continue
        url = "/api/v1" + path.replace("{}", "1")
        response = client.open(url, method=method)
        if response.status_code != 401:
            failures.append(f"{method} {path} -> {response.status_code}")
    assert failures == []

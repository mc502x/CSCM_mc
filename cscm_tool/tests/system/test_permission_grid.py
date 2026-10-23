"""TC-018 / TC-018a / TC-018b / TC-019 / FR-081 / SEC-010: the full
5-role x endpoint permission grid, for the API and for the UI routes.

A role outside an endpoint's allow-list must get the role-gate 403
("Insufficient role"); a role inside it must get past the gate (it may still
see a domain error such as 404/409/422, or a row-level SoD 403 with a
different message — that is the service layer, tested elsewhere)."""

import pytest

from app.auth.rate_limit import reset_for_testing
from tests.helpers import PASSWORD, create_draft, login_as, make_cast

ALL = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER", "VIEWER", "STCD_OWNER")
ADMIN = ("ADMINISTRATOR",)
ADMIN_ENG = ("ADMINISTRATOR", "ENGINEER")
NOT_VIEWER = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")  # BR-009
OVERSIGHT = (*NOT_VIEWER, "STCD_OWNER")  # read-only view of the workflow (BR-024)
USERS = ("ADMINISTRATOR", "STCD_OWNER")  # the user list; the owner may only change roles (BR-024)
LOGGED_IN = ALL

ROLE_USER = {
    "ADMINISTRATOR": "admin",
    "ENGINEER": "engineer",
    "REVIEWER": "reviewer",
    "CHIEF_ENGINEER": "chief_engineer",
    "VIEWER": "viewer",
    "STCD_OWNER": "stcd_owner",
}

# (method, path, json body, roles allowed past the role gate)
API_GRID = [
    ("GET", "/users", None, USERS),
    ("POST", "/users", {}, ADMIN),
    ("PATCH", "/users/{user}", {}, USERS),
    ("POST", "/users/{user}/force-reset-password", {}, ADMIN),
    ("GET", "/status-codes", None, LOGGED_IN),
    (
        "GET",
        "/status-codes/next-available?functional_system_group=1&functional_subgroup=1",
        None,
        ADMIN_ENG,
    ),
    ("GET", "/releases/9999/candidates", None, ADMIN),
    ("POST", "/status-codes", {}, ADMIN_ENG),
    ("DELETE", "/status-codes/{sc}", None, ADMIN),
    ("POST", "/status-codes/{sc}/deprecation-requests", {}, ADMIN_ENG),
    ("POST", "/status-codes/{sc}/archive", None, ADMIN),
    ("POST", "/status-codes/{sc}/reinstate", {}, ADMIN),
    ("POST", "/status-codes/{sc}/revisions", {}, ADMIN_ENG),
    ("GET", "/status-codes/{sc}/revisions", None, LOGGED_IN),
    ("GET", "/status-codes/{sc}/revisions/1/diff/1", None, LOGGED_IN),
    ("PATCH", "/revisions/{rev}", {}, ADMIN_ENG),
    ("GET", "/change-requests", None, OVERSIGHT),
    ("GET", "/change-requests/{cr}", None, OVERSIGHT),
    ("GET", "/change-requests/{cr}/domain-signoffs", None, OVERSIGHT),
    ("POST", "/change-requests/{cr}/submit", {}, ADMIN_ENG),
    ("POST", "/change-requests/{cr}/reviewer-signoff", {}, ("REVIEWER",)),
    ("POST", "/change-requests/{cr}/admin-signoff", {}, ADMIN),
    ("POST", "/change-requests/{cr}/chief-engineer-decide", {}, ("CHIEF_ENGINEER",)),
    ("POST", "/change-requests/{cr}/comments", {}, ("REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER")),
    ("PUT", "/change-requests/{cr}/reviewer-assignment", {}, ADMIN),
    ("POST", "/change-requests/{cr}/withdraw", None, ADMIN_ENG),
    ("POST", "/change-requests/{cr}/domain-signoffs", {}, ("ENGINEER",)),
    ("POST", "/change-requests/{cr}/domain-signoff-requests", {}, ADMIN_ENG),
    ("GET", "/domain-signoff-requests", None, ("ENGINEER",)),
    ("GET", "/releases", None, LOGGED_IN),
    ("POST", "/releases", {}, ADMIN),
    ("PUT", "/releases/9999/items", {}, ADMIN),
    ("POST", "/releases/9999/publish", None, ADMIN),
    ("DELETE", "/releases/9999", None, ADMIN),
    ("GET", "/releases/9999/export?format=csv", None, LOGGED_IN),
    ("GET", "/imports/9999", None, ADMIN_ENG),
    ("POST", "/imports", None, ADMIN_ENG),
    ("GET", "/exports/released?format=csv", None, LOGGED_IN),
    (
        "GET",
        "/exports/working-set?format=csv",
        None,
        ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER"),
    ),
    ("POST", "/exports/full-database", {}, ADMIN),
    ("GET", "/lookups/turbine-platforms", None, LOGGED_IN),
    ("POST", "/lookups/turbine-platforms", {}, ADMIN),
    ("PATCH", "/lookups/turbine-platforms/1", {}, ADMIN),
    ("POST", "/lookups/functional-system-groups", {}, ADMIN),
    ("POST", "/lookups/functional-subgroups", {}, ADMIN),
    ("GET", "/audit-log", None, ("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER")),
    # v4 (improvement pack): the full list is derived by test_route_inventory.py; these are the
    # reviewable statements of who may do what.
    ("GET", "/reports/catalogue-health", None, ("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER")),
    ("GET", "/reports/kpis", None, ("ADMINISTRATOR", "CHIEF_ENGINEER")),
    ("GET", "/reports/occurrences", None, ("ADMINISTRATOR", "CHIEF_ENGINEER")),
    ("POST", "/occurrence-imports", None, ("ADMINISTRATOR", "CHIEF_ENGINEER")),
    ("GET", "/api-tokens", None, ADMIN),
    ("POST", "/api-tokens", {}, ADMIN),
    ("GET", "/webhooks", None, ADMIN),
    ("POST", "/webhooks", {}, ADMIN),
    ("GET", "/operations/backup-status", None, ADMIN),
    ("POST", "/operations/audit-verify", None, ADMIN),
    ("GET", "/hub-consolidation/mapping", None, OVERSIGHT),
    ("POST", "/status-codes/{sc}/mc-drafts", {}, ADMIN_ENG),
    ("POST", "/hub-consolidation/deprecation-requests", {}, ADMIN),
    ("GET", "/change-sets", None, OVERSIGHT),
    ("POST", "/change-sets", {}, ("ADMINISTRATOR", "ENGINEER", "CHIEF_ENGINEER")),
    ("POST", "/change-sets/9999/close", None, ADMIN),
    ("POST", "/delegations", {}, ("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER")),
    ("GET", "/saved-searches", None, LOGGED_IN),
    ("GET", "/notifications", None, LOGGED_IN),
]

UI_GRID = [
    ("GET", "/admin/users", USERS),
    ("GET", "/change-requests/mine", NOT_VIEWER),
    ("GET", "/change-requests/{cr}", NOT_VIEWER),
    ("GET", "/admin/lookups", ADMIN),
    ("GET", "/admin/audit-log", ("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER")),
    ("GET", "/status-codes/new", ADMIN_ENG),
    ("GET", "/status-codes/new-sandbox", ADMIN),
    ("POST", "/status-codes/{sc}/delete", ADMIN),
    ("POST", "/status-codes/{sc}/archive", ADMIN),
    ("GET", "/change-requests/review-queue", ("REVIEWER", "ADMINISTRATOR")),
    ("GET", "/change-requests/approval-queue", ("CHIEF_ENGINEER",)),
    ("POST", "/change-requests/{cr}/reviewer-signoff", ("REVIEWER",)),
    ("POST", "/change-requests/{cr}/admin-signoff", ADMIN),
    ("POST", "/change-requests/{cr}/chief-engineer-decide", ("CHIEF_ENGINEER",)),
    ("POST", "/change-requests/{cr}/comments", ("REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER")),
    ("POST", "/change-requests/{cr}/reviewer-assignment", ADMIN),
    ("GET", "/releases/new", ADMIN),
    ("POST", "/releases/9999/delete", ADMIN),
    ("POST", "/releases/9999/publish", ADMIN),
    ("GET", "/imports/new", ADMIN_ENG),
    ("GET", "/admin/settings", ADMIN),
    ("GET", "/admin/operations", ADMIN),
    ("GET", "/admin/integrations", ADMIN),
    ("GET", "/admin/stalled", ADMIN),
    ("GET", "/admin/review-checklist", ADMIN),
    ("GET", "/admin/export-profiles", ADMIN),
    ("GET", "/reports/catalogue-health", ("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER")),
    ("GET", "/reports/success-metrics", ("ADMINISTRATOR", "CHIEF_ENGINEER")),
    ("GET", "/reports/fleet-feedback", ("ADMINISTRATOR", "CHIEF_ENGINEER")),
    ("GET", "/hub-consolidation", OVERSIGHT),
    ("GET", "/change-sets", OVERSIGHT),
    ("GET", "/delegation", ("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER")),
]


@pytest.fixture()
def fixture_ids(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, cr_id = create_draft(app, client, cast, wcnv_ids)
    client.post("/api/v1/auth/logout")
    return {
        "cast": cast,
        "ids": {
            "user": cast["viewer"].id,
            "sc": revision["status_code_id"],
            "rev": revision["id"],
            "cr": cr_id,
        },
    }


def _is_role_gate(response) -> bool:
    if response.status_code != 403:
        return False
    body = response.get_json(silent=True)
    return body is None or body.get("message") == "Insufficient role"


@pytest.mark.parametrize("role", ALL)
def test_api_permission_grid(client, fixture_ids, role):
    reset_for_testing()
    login_as(client, fixture_ids["cast"][ROLE_USER[role]])
    failures = []
    for method, path, body, allowed in API_GRID:
        url = "/api/v1" + path.format(**fixture_ids["ids"])
        kwargs = {} if body is None else {"json": body}
        response = client.open(url, method=method, **kwargs)
        gated = _is_role_gate(response)
        if role in allowed and (gated or response.status_code == 401):
            failures.append(
                f"{role} should pass the gate on {method} {path}: {response.status_code}"
            )
        if role not in allowed and not gated:
            failures.append(f"{role} should be gated on {method} {path}: {response.status_code}")
    assert failures == []


def test_api_endpoints_require_authentication(client, fixture_ids):
    failures = []
    for method, path, body, _allowed in API_GRID:
        url = "/api/v1" + path.format(**fixture_ids["ids"])
        kwargs = {} if body is None else {"json": body}
        response = client.open(url, method=method, **kwargs)
        if response.status_code != 401:
            failures.append(f"{method} {path} -> {response.status_code}")
    assert failures == []


@pytest.mark.parametrize("role", ALL)
def test_ui_permission_grid(client, fixture_ids, role):
    reset_for_testing()
    user = fixture_ids["cast"][ROLE_USER[role]]
    client.post("/api/v1/auth/logout")
    client.post("/logout")
    assert (
        client.post("/login", data={"username": user.username, "password": PASSWORD}).status_code
        == 302
    )
    failures = []
    for method, path, allowed in UI_GRID:
        response = client.open(path.format(**fixture_ids["ids"]), method=method)
        if role in allowed and response.status_code in (401, 403):
            failures.append(f"{role} should reach {method} {path}: {response.status_code}")
        if role not in allowed and response.status_code != 403:
            failures.append(f"{role} should get 403 on {method} {path}: {response.status_code}")
    assert failures == []


def test_ui_redirects_anonymous_users_to_login(client, fixture_ids):
    for method, path, _allowed in UI_GRID:
        response = client.open(path.format(**fixture_ids["ids"]), method=method)
        assert response.status_code == 302, (method, path)
        assert "/login" in response.headers["Location"]

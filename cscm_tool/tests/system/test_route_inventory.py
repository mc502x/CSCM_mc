"""Every route is access-controlled, and the declared role lists are what is enforced.

`test_permission_grid.py` is the hand-written grid (the reviewable statement of who may do what).
This module is its safety net: it walks the Flask URL map, so a route added later cannot slip
through un-gated or with a gate that is not the one declared on it. The decorators in
app/auth/decorators.py record what they enforce in `view.access` = ("login", ()) or
("roles", (role codes...)).

TC-048. Requirements: SEC-010, FR-081, TC-018.
"""

import pytest

from app.auth.rate_limit import reset_for_testing
from tests.helpers import PASSWORD, login_as, make_cast

PUBLIC_ENDPOINTS = {
    "static",
    "metrics",  # network allow-list + optional token instead of a session (docs/11 §10)
    "api_v1.csrf_token",
    "api_v1.login",
    "api_v1.windows_login",  # the gateway supplies the identity (FR-163)
    "api_v1.health",
    "api_v1.ready",
    "ui.login",
    "ui.login_windows",
    "ui.login_windows_simulate",  # 404 unless the developer simulation is on
    "ui.logout",
    "ui.set_language",
}
ROLE_USER = {
    "ADMINISTRATOR": "admin",
    "ENGINEER": "engineer",
    "REVIEWER": "reviewer",
    "CHIEF_ENGINEER": "chief_engineer",
    "VIEWER": "viewer",
    "STCD_OWNER": "stcd_owner",
}
# Login-only endpoints that end the session or change credentials: skip them in the role loops.
SESSION_ENDING = {"api_v1.logout", "ui.account_password", "api_v1.change_password"}
VERBS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def _routes(app):
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if rule.endpoint in PUBLIC_ENDPOINTS:
            continue
        values = {
            name: (999999 if type(rule._converters[name]).__name__ == "IntegerConverter" else "x")
            for name in rule.arguments
        }
        path = rule.build(values)[1]
        for method in sorted(rule.methods & VERBS):
            yield rule, method, path


def _is_api(path: str) -> bool:
    return path.startswith("/api/v1/")


def test_every_route_declares_its_access_control(app):
    undeclared = [
        f"{rule.endpoint} {rule.rule}"
        for rule in app.url_map.iter_rules()
        if rule.endpoint not in PUBLIC_ENDPOINTS
        and getattr(app.view_functions[rule.endpoint], "access", None) is None
    ]
    assert undeclared == []


def test_the_public_list_is_exactly_the_routes_that_need_no_session(app):
    existing = {r.endpoint for r in app.url_map.iter_rules()}
    assert PUBLIC_ENDPOINTS <= existing  # no stale entries hiding a renamed route


def test_every_gated_route_refuses_anonymous_callers(client, app):
    failures = []
    for rule, method, path in _routes(app):
        if method != "GET" and rule.endpoint in SESSION_ENDING:
            continue
        response = client.open(path, method=method)
        if _is_api(path):
            ok = response.status_code == 401
        else:
            ok = response.status_code == 302 and "/login" in response.headers["Location"]
        if not ok:
            failures.append(f"{method} {path} ({rule.endpoint}) -> {response.status_code}")
    assert failures == []


def test_role_lists_are_never_empty_and_only_name_real_roles(app):
    known = set(ROLE_USER)
    for rule in app.url_map.iter_rules():
        access = getattr(app.view_functions[rule.endpoint], "access", None)
        if access and access[0] == "roles":
            assert access[1] and set(access[1]) <= known, rule.endpoint


@pytest.mark.parametrize("role", list(ROLE_USER))
def test_the_declared_role_list_is_what_each_role_gets(client, app, make_user, role):
    cast = make_cast(make_user)
    reset_for_testing()
    login_as(client, cast[ROLE_USER[role]])
    failures = []
    checked = 0
    for rule, method, path in _routes(app):
        access = app.view_functions[rule.endpoint].access
        if access[0] != "roles" or rule.endpoint in SESSION_ENDING:
            continue
        checked += 1
        response = client.open(path, method=method)
        gated = response.status_code == 403 and (
            not _is_api(path)
            or (response.get_json(silent=True) or {}).get("message") == "Insufficient role"
        )
        if role in access[1] and gated:
            failures.append(f"{role} should pass the gate on {method} {path}")
        if role not in access[1] and not gated:
            failures.append(f"{role} should be refused on {method} {path}: {response.status_code}")
    assert checked > 100  # the walk really covers the application
    assert failures == []


def test_login_only_routes_are_reachable_by_every_role(client, app, make_user):
    cast = make_cast(make_user)
    failures = []
    for role, key in ROLE_USER.items():
        reset_for_testing()
        login_as(client, cast[key])
        for rule, method, path in _routes(app):
            access = app.view_functions[rule.endpoint].access
            if access[0] != "login" or method != "GET" or rule.endpoint in SESSION_ENDING:
                continue
            response = client.get(path)
            if response.status_code in (401, 403) or (
                response.status_code == 302 and "/login" in response.headers.get("Location", "")
            ):
                failures.append(f"{role} GET {path} -> {response.status_code}")
    assert failures == []


def test_a_tokenised_endpoint_is_always_a_get(app):
    """API tokens may only ever read (docs/11 §12): `allow_token` must never sit on a write."""
    for rule in app.url_map.iter_rules():
        if getattr(app.view_functions[rule.endpoint], "_token_scope", None):
            assert rule.methods & VERBS == {"GET"}, rule.endpoint


def test_login_page_credentials_still_work_for_the_ui_walk(client, make_user):
    user = make_user("ADMINISTRATOR")
    assert (
        client.post("/login", data={"username": user.username, "password": PASSWORD}).status_code
        == 302
    )

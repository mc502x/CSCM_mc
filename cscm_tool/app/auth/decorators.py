"""Session validation + RBAC decorators. Enforcement-point order per
docs/11-security-architecture.md §8: API route decorator -> service-layer
check -> DB constraint/trigger -> UI conditional rendering."""

import hashlib
from datetime import UTC, datetime
from functools import wraps

from flask import abort, current_app, g, jsonify, redirect, request, session, url_for
from werkzeug.local import LocalProxy

from app.auth.providers import AuthenticatedUser
from app.repositories.user_repository import UserRepository
from app.utils import format_iso, parse_iso

_repo = UserRepository()


def _load_current_user() -> AuthenticatedUser | None:
    """Validates idle timeout (SEC-003), absolute lifetime (SEC-003),
    account status, and password freshness on every request, so
    deactivation and forced password resets (SEC/§5) take effect on the
    very next request even though the session itself is a signed cookie
    rather than a server-side-revocable token."""
    if "current_user" in g:
        return g.current_user

    user_id = session.get("user_id")
    if user_id is None:
        g.current_user = _token_principal()
        return g.current_user

    login_at = session.get("login_at")
    last_activity_at = session.get("last_activity_at")
    if login_at is None or last_activity_at is None:
        session.clear()
        g.current_user = None
        return None

    now = datetime.now(UTC)
    idle_timeout = current_app.config["IDLE_SESSION_TIMEOUT"]
    absolute_lifetime = current_app.config["PERMANENT_SESSION_LIFETIME"]
    if (
        now - parse_iso(last_activity_at) > idle_timeout
        or now - parse_iso(login_at) > absolute_lifetime
    ):
        session.clear()
        g.current_user = None
        return None

    user = _repo.get(user_id)
    if user is None or not user.is_active:
        session.clear()
        g.current_user = None
        return None

    fingerprint = hashlib.sha256(user.password_hash.encode()).hexdigest()
    if fingerprint != session.get("pw_fingerprint"):
        session.clear()
        g.current_user = None
        return None

    session["last_activity_at"] = format_iso(now)
    g.current_user = AuthenticatedUser.from_model(user)
    return g.current_user


def allow_token(scope: str):
    """Marks a GET endpoint as callable with an API token holding `scope` (I-29). Apply it
    directly under the route decorator; it only records the scope on the view function."""

    def decorator(view):
        view._token_scope = scope
        return view

    return decorator


def _token_principal() -> AuthenticatedUser | None:
    """A Viewer-level principal for `Authorization: Bearer cscm_...` on a token-enabled GET
    endpoint; None for everything else (so tokens can never reach a write or any other route)."""
    header = request.headers.get("Authorization", "")
    if request.method != "GET" or not header.startswith("Bearer "):
        return None
    view = current_app.view_functions.get(request.endpoint or "")
    scope = getattr(view, "_token_scope", None)
    if scope is None:
        return None
    from app.services.integration_service import ApiTokenService

    return ApiTokenService.authenticate(header[7:].strip(), scope)


current_user: AuthenticatedUser = LocalProxy(_load_current_user)  # type: ignore[assignment]


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if _load_current_user() is None:
            return jsonify(error="unauthorized", message="Authentication required"), 401
        return view(*args, **kwargs)

    wrapper.access = ("login", ())  # type: ignore[attr-defined]  # read by tests/system/test_route_inventory.py
    return wrapper


def require_role(*roles: str):
    """Role-membership check only (static). Segregation-of-duties checks
    that depend on a specific row's data live in the service layer
    (SEC-010/SEC-011), not here."""

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(*args, **kwargs):
            user = _load_current_user()
            if user is not None and user.role_code not in roles:
                return jsonify(error="forbidden", message="Insufficient role"), 403
            return view(*args, **kwargs)

        wrapper.access = ("roles", roles)  # type: ignore[attr-defined]
        return wrapper

    return decorator


def require_role_or_delegate(*roles: str):
    """Like `require_role`, but a user covering for someone who holds one of `roles`
    (I-16) is admitted too. Used only on the decision actions."""

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(*args, **kwargs):
            user = _load_current_user()
            if user is not None and not any(user.can_act_as(r) for r in roles):
                return jsonify(error="forbidden", message="Insufficient role"), 403
            return view(*args, **kwargs)

        wrapper.access = ("roles", roles)  # type: ignore[attr-defined]
        return wrapper

    return decorator


def login_required_web(view):
    """UI-blueprint equivalent of login_required: redirects to the login
    page instead of returning a JSON 401, since a browser navigating to a
    protected page should see a login form, not an API error body."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if _load_current_user() is None:
            return redirect(url_for("ui.login", next=request.path))
        return view(*args, **kwargs)

    wrapper.access = ("login", ())  # type: ignore[attr-defined]
    return wrapper


def require_role_or_delegate_web(*roles: str):
    def decorator(view):
        @wraps(view)
        @login_required_web
        def wrapper(*args, **kwargs):
            user = _load_current_user()
            if user is not None and not any(user.can_act_as(r) for r in roles):
                abort(403)
            return view(*args, **kwargs)

        wrapper.access = ("roles", roles)  # type: ignore[attr-defined]
        return wrapper

    return decorator


def require_role_web(*roles: str):
    def decorator(view):
        @wraps(view)
        @login_required_web
        def wrapper(*args, **kwargs):
            user = _load_current_user()
            if user is not None and user.role_code not in roles:
                abort(403)
            return view(*args, **kwargs)

        wrapper.access = ("roles", roles)  # type: ignore[attr-defined]
        return wrapper

    return decorator

"""FR-001-FR-004. See docs/artifacts/openapi.yaml paths /auth/*."""

from flask import jsonify, request
from flask_wtf.csrf import generate_csrf

from app.api.v1 import api_v1_bp
from app.auth.decorators import current_user, login_required
from app.auth.providers import AuthenticatedUser
from app.domain.errors import AccountLockedError, InvalidCredentialsError, RateLimitedError
from app.extensions import csrf
from app.services.auth_service import AuthService


def _user_payload(auth_user: AuthenticatedUser) -> dict:
    return {
        "id": auth_user.id,
        "username": auth_user.username,
        "email": auth_user.email,
        "full_name": auth_user.full_name,
        "role": auth_user.role_code,
        "engineering_domains": sorted(auth_user.engineering_domain_codes),
    }


@api_v1_bp.get("/auth/csrf-token")
@csrf.exempt
def csrf_token():
    """Infrastructure endpoint (not in docs/artifacts/openapi.yaml, which
    documents business endpoints): issues the synchronizer token required
    per docs/11-security-architecture.md §5 on every other state-changing
    request, via the X-CSRFToken header."""
    return jsonify(csrf_token=generate_csrf()), 200


@api_v1_bp.post("/auth/login")
@csrf.exempt
def login():
    """Exempted from CSRF: there is no pre-existing authenticated session
    for an attacker to ride, and requiring a pre-fetched token here would
    only add friction without closing a real attack surface at MVP scope."""
    body = request.get_json(silent=True) or {}
    username = body.get("username")
    password = body.get("password")
    if not username or not password:
        return (
            jsonify(error="validation_error", message="username and password are required"),
            422,
        )

    try:
        auth_user = AuthService.login(username, password, request.remote_addr)
    except RateLimitedError as exc:
        return jsonify(error="rate_limited", message=str(exc)), 429
    except AccountLockedError as exc:
        return jsonify(error="account_locked", message=str(exc)), 423
    except InvalidCredentialsError as exc:
        return jsonify(error="unauthorized", message=str(exc)), 401

    return jsonify(_user_payload(auth_user)), 200


@api_v1_bp.post("/auth/logout")
@login_required
def logout():
    AuthService.logout(current_user.id)
    return "", 204


@api_v1_bp.get("/auth/me")
@login_required
def me():
    return jsonify(_user_payload(current_user)), 200

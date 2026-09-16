"""FR-010-FR-014. See docs/artifacts/openapi.yaml paths /users, /users/{userId}."""

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.decorators import current_user, login_required, require_role
from app.domain.errors import LastAdministratorError, PasswordPolicyError
from app.models.user import User
from app.services.user_service import UserService


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.code,
        "engineering_domains": sorted(
            ued.engineering_domain.code for ued in user.engineering_domains
        ),
        "is_active": bool(user.is_active),
        "last_login_at": user.last_login_at,
    }


@api_v1_bp.get("/users")
@require_role("ADMINISTRATOR")
def list_users():
    users = UserService.list_users()
    return jsonify(
        items=[_user_payload(u) for u in users], total=len(users), page=1, page_size=len(users) or 1
    )


@api_v1_bp.post("/users")
@require_role("ADMINISTRATOR")
def create_user():
    body = request.get_json(silent=True) or {}
    required = {"username", "email", "full_name", "role", "password"}
    missing = required - body.keys()
    if missing:
        return (
            jsonify(error="validation_error", message=f"missing fields: {sorted(missing)}"),
            422,
        )

    try:
        user = UserService.create_user(
            username=body["username"],
            email=body["email"],
            full_name=body["full_name"],
            role_code=body["role"],
            password=body["password"],
            engineering_domain_codes=body.get("engineering_domains"),
            actor=current_user,
        )
    except PasswordPolicyError as exc:
        return (
            jsonify(
                error="validation_error",
                message=str(exc),
                field_errors=[{"field": "password", "message": v} for v in exc.violations],
            ),
            422,
        )
    except ValueError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return jsonify(_user_payload(user)), 201


@api_v1_bp.get("/users/<int:user_id>")
@require_role("ADMINISTRATOR")
def get_user(user_id: int):
    return jsonify(_user_payload(UserService.get_user(user_id))), 200


@api_v1_bp.patch("/users/<int:user_id>")
@require_role("ADMINISTRATOR")
def update_user(user_id: int):
    body = request.get_json(silent=True) or {}
    try:
        user = UserService.update_user(
            user_id,
            full_name=body.get("full_name"),
            role_code=body.get("role"),
            engineering_domain_codes=body.get("engineering_domains"),
            is_active=body.get("is_active"),
            actor=current_user,
        )
    except LastAdministratorError as exc:
        return jsonify(error="last_administrator", message=str(exc)), 422
    except ValueError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return jsonify(_user_payload(user)), 200


@api_v1_bp.post("/users/me/change-password")
@login_required
def change_own_password():
    body = request.get_json(silent=True) or {}
    current_password = body.get("current_password")
    new_password = body.get("new_password")
    if not current_password or not new_password:
        return (
            jsonify(
                error="validation_error",
                message="current_password and new_password are required",
            ),
            422,
        )

    user = UserService.get_user(current_user.id)
    try:
        UserService.change_own_password(user, current_password, new_password)
    except PasswordPolicyError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422
    except ValueError as exc:
        return jsonify(error="unauthorized", message=str(exc)), 401

    return "", 204


@api_v1_bp.post("/users/<int:user_id>/force-reset-password")
@require_role("ADMINISTRATOR")
def force_reset_password(user_id: int):
    body = request.get_json(silent=True) or {}
    new_password = body.get("new_password")
    if not new_password:
        return jsonify(error="validation_error", message="new_password is required"), 422
    try:
        UserService.force_reset_password(user_id, new_password, actor=current_user)
    except PasswordPolicyError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return "", 204

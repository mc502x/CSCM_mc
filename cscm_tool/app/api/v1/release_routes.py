"""FR-040-FR-044, BR-006-BR-008. See docs/artifacts/openapi.yaml paths /releases*."""

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1.serializers import release_payload, revision_payload
from app.auth.decorators import current_user, login_required, require_role
from app.domain.errors import DomainError, InvalidTransitionError, NotFoundError
from app.services.release_service import ReleaseService


@api_v1_bp.get("/releases")
@login_required
def list_releases():
    return jsonify([release_payload(r) for r in ReleaseService.list_all()])


@api_v1_bp.post("/releases")
@require_role("ADMINISTRATOR")
def create_release():
    body = request.get_json(silent=True) or {}
    if not body.get("name") or not body.get("version_label"):
        return (
            jsonify(error="validation_error", message="name and version_label are required"),
            422,
        )
    release = ReleaseService.create(body, current_user)
    return jsonify(release_payload(release)), 201


@api_v1_bp.get("/releases/<int:release_id>")
@login_required
def get_release(release_id: int):
    try:
        release = ReleaseService.get(release_id)
    except NotFoundError:
        return jsonify(error="not_found", message="Release not found"), 404
    return jsonify(release_payload(release))


@api_v1_bp.get("/releases/<int:release_id>/candidates")
@require_role("ADMINISTRATOR")
def list_candidates(release_id: int):
    try:
        candidates = ReleaseService.list_candidates(release_id)
    except NotFoundError:
        return jsonify(error="not_found", message="Release not found"), 404
    return jsonify([revision_payload(r) for r in candidates])


@api_v1_bp.put("/releases/<int:release_id>/items")
@require_role("ADMINISTRATOR")
def set_release_items(release_id: int):
    body = request.get_json(silent=True) or {}
    revision_ids = body.get("status_code_revision_ids") or []
    try:
        release = ReleaseService.set_items(release_id, revision_ids, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Release not found"), 404
    except InvalidTransitionError as exc:
        return jsonify(error="conflict", message=str(exc)), 409
    except (DomainError, ValueError) as exc:
        return jsonify(error="validation_error", message=str(exc)), 422
    return jsonify(release_payload(release)), 200


@api_v1_bp.post("/releases/<int:release_id>/publish")
@require_role("ADMINISTRATOR")
def publish_release(release_id: int):
    try:
        release = ReleaseService.publish(release_id, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Release not found"), 404
    except InvalidTransitionError as exc:
        return jsonify(error="conflict", message=str(exc)), 409
    except DomainError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422
    return jsonify(release_payload(release)), 200

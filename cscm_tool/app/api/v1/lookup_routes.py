"""See docs/artifacts/openapi.yaml /lookups/{vocabulary}. Write endpoints are
Administrator-only (docs/05-governance-handbook.md §3, US-091).

v3 (2026-09-17, EPIC-16): Functional System Group and Functional Subgroup
creation moved to their own dedicated, non-overlap-validated endpoints
(docs/09-api-specification.md §6c) — see LookupAdminService's module
docstring for why the generic create/update endpoints no longer accept
either vocabulary."""

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.decorators import current_user, login_required, require_role
from app.domain.errors import DomainError, NotFoundError
from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup
from app.services.lookup_admin_service import LookupAdminService
from app.services.lookup_service import LookupService


def _lookup_payload(item) -> dict:
    payload = {
        "id": item.id,
        "code": item.code,
        "label": item.label,
        "description": getattr(item, "description", None),
        "is_active": bool(item.is_active),
    }
    if isinstance(item, LookupFunctionalSystemGroup):
        payload["range_start"] = item.range_start
        payload["range_end"] = item.range_end
    elif isinstance(item, LookupFunctionalSubgroup):
        payload["range_start"] = item.sub_range_start
        payload["range_end"] = item.sub_range_end
        payload["functional_system_group"] = item.functional_system_group.code
        payload["functional_system_group_id"] = item.functional_system_group_id
    return payload


@api_v1_bp.get("/lookups/<vocabulary>")
@login_required
def list_lookup(vocabulary: str):
    try:
        items = LookupService.list_vocabulary(
            vocabulary,
            functional_system_group_id=request.args.get("functional_system_group", type=int),
        )
    except ValueError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return jsonify([_lookup_payload(item) for item in items])


@api_v1_bp.post("/lookups/<vocabulary>")
@require_role("ADMINISTRATOR")
def create_lookup_value(vocabulary: str):
    body = request.get_json(silent=True) or {}
    try:
        value = LookupAdminService.create_value(vocabulary, body, current_user)
    except DomainError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422
    except ValueError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return jsonify(_lookup_payload(value)), 201


@api_v1_bp.patch("/lookups/<vocabulary>/<int:value_id>")
@require_role("ADMINISTRATOR")
def update_lookup_value(vocabulary: str, value_id: int):
    body = request.get_json(silent=True) or {}
    try:
        value = LookupAdminService.update_value(vocabulary, value_id, body, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Lookup value not found"), 404
    except ValueError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return jsonify(_lookup_payload(value)), 200


@api_v1_bp.post("/lookups/functional-system-groups")
@require_role("ADMINISTRATOR")
def create_functional_system_group():
    """FR-048g/h: Administrator-only, into any currently free range."""
    body = request.get_json(silent=True) or {}
    try:
        group = LookupAdminService.create_functional_system_group(body, current_user)
    except DomainError as exc:
        return jsonify(error="conflict", message=str(exc)), 409
    except ValueError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return jsonify(_lookup_payload(group)), 201


@api_v1_bp.post("/lookups/functional-subgroups")
@require_role("ADMINISTRATOR")
def create_functional_subgroup():
    """FR-048e/f: Administrator-only, within an existing Functional System
    Group, non-overlap validated."""
    body = request.get_json(silent=True) or {}
    try:
        subgroup = LookupAdminService.create_functional_subgroup(body, current_user)
    except DomainError as exc:
        return jsonify(error="conflict", message=str(exc)), 409
    except ValueError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return jsonify(_lookup_payload(subgroup)), 201

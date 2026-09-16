"""See docs/artifacts/openapi.yaml /lookups/{vocabulary}."""

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.auth.decorators import login_required
from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup
from app.services.lookup_service import LookupService


def _lookup_payload(item) -> dict:
    payload = {"id": item.id, "code": item.code, "label": item.label}
    if isinstance(item, LookupFunctionalSystemGroup):
        payload["range_start"] = item.range_start
        payload["range_end"] = item.range_end
    elif isinstance(item, LookupFunctionalSubgroup):
        payload["range_start"] = item.sub_range_start
        payload["range_end"] = item.sub_range_end
        payload["functional_system_group"] = item.functional_system_group.code
    return payload


@api_v1_bp.get("/lookups/<vocabulary>")
@login_required
def list_lookup(vocabulary: str):
    try:
        items = LookupService.list_vocabulary(
            vocabulary, functional_system_group_code=request.args.get("functional_system_group")
        )
    except ValueError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return jsonify([_lookup_payload(item) for item in items])

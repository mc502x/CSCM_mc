"""FR-027-FR-029. See docs/artifacts/openapi.yaml /change-requests/{crId}/domain-signoffs."""

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1.serializers import domain_signoff_payload, pending_domain_signoff_payload
from app.auth.decorators import current_user, require_role
from app.domain.errors import DomainError
from app.extensions import db
from app.models.change_request import ChangeRequest
from app.services.domain_signoff_service import DomainSignoffService, user_domain_codes


@api_v1_bp.get("/change-requests/<int:cr_id>/domain-signoffs")
@require_role("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")
def list_domain_signoffs(cr_id: int):
    cr = db.session.get(ChangeRequest, cr_id)
    if cr is None:
        return jsonify(error="not_found", message="Change request not found"), 404

    requester_domains = user_domain_codes(cr.requester)
    signed_off = {ds.engineering_domain.code: ds for ds in cr.domain_signoffs}
    required = DomainSignoffService.required_domains(requester_domains)

    payload = [domain_signoff_payload(ds) for ds in cr.domain_signoffs]
    payload += [
        pending_domain_signoff_payload(code) for code in sorted(required - signed_off.keys())
    ]
    return jsonify(payload)


@api_v1_bp.post("/change-requests/<int:cr_id>/domain-signoffs")
@require_role("ENGINEER")
def create_domain_signoff(cr_id: int):
    cr = db.session.get(ChangeRequest, cr_id)
    if cr is None:
        return jsonify(error="not_found", message="Change request not found"), 404

    body = request.get_json(silent=True) or {}
    domain_code = body.get("engineering_domain")
    if not domain_code:
        return jsonify(error="validation_error", message="engineering_domain is required"), 422

    try:
        signoff = DomainSignoffService.sign(cr, domain_code, current_user)
    except DomainError as exc:
        return jsonify(error="forbidden", message=str(exc)), 403
    except ValueError as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return jsonify(domain_signoff_payload(signoff)), 201

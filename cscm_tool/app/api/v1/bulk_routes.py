# ruff: noqa: E501  (docstring lines)
"""FR-180: bulk work on a change set - edit, submit, sign off, decide - with the sample inspection.
See docs/artifacts/openapi.yaml /change-sets/{id}/readiness, bulk-edit, bulk-submit, domain-signoffs,
samples and /bulk-samples."""

from flask import Response, jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1._errors import error_response
from app.auth.decorators import current_user, require_role
from app.domain.errors import DomainError
from app.services.bulk_service import BulkService

_WORKING = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")
_SEEING = (*_WORKING, "STCD_OWNER")


def _body() -> dict:
    return request.get_json(silent=True) or {}


def sample_payload(sample) -> dict:
    return {
        "id": sample.id,
        "change_set_id": sample.change_set_id,
        "step": sample.step,
        "domain": sample.domain_code,
        "status": sample.status,
        "population": sample.population,
        "sampled": len(sample.items),
        "rate_percent": sample.rate_percent,
        "drawn_by": sample.drawn_by,
        "drawn_at": sample.drawn_at,
        "used_at": sample.used_at,
        "items": [
            {
                "change_request_id": item.change_request_id,
                "identifier": item.change_request.revision.status_code.status_code_identifier
                or item.change_request.revision.status_code.reserved_identifier,
                "title": item.change_request.revision.title,
                "verdict": item.verdict,
                "note": item.note,
            }
            for item in sample.items
        ],
    }


@api_v1_bp.get("/change-sets/<int:change_set_id>/readiness")
@require_role(*_SEEING)
def change_set_readiness(change_set_id: int):
    try:
        data = BulkService.readiness(change_set_id)
    except DomainError as exc:
        return error_response(exc)
    return jsonify(
        tally=data["tally"],
        pending_by_domain=data["pending_by_domain"],
        rules=BulkService.rules(),
        items=[
            {
                "change_request_id": r["cr"].id,
                "identifier": r["identifier"],
                "title": r["title"],
                "blockers": r["blockers"],
            }
            for r in data["rows"]
        ],
    )


@api_v1_bp.post("/change-sets/<int:change_set_id>/bulk-edit")
@require_role("ADMINISTRATOR", "ENGINEER")
def change_set_bulk_edit(change_set_id: int):
    body = _body()
    try:
        results = BulkService.edit(
            change_set_id, body.get("change_request_ids"), body.get("changes") or {}, current_user
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(results=results)


@api_v1_bp.post("/change-sets/<int:change_set_id>/bulk-submit")
@require_role("ADMINISTRATOR", "ENGINEER")
def change_set_bulk_submit(change_set_id: int):
    try:
        results = BulkService.submit(change_set_id, current_user, _body().get("change_request_ids"))
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(results=results)


@api_v1_bp.post("/change-sets/<int:change_set_id>/domain-signoffs")
@require_role("ADMINISTRATOR", "ENGINEER")
def change_set_domain_signoffs(change_set_id: int):
    body = _body()
    try:
        results = BulkService.domain_signoff(
            change_set_id,
            body.get("domain", ""),
            current_user,
            sample_id=body.get("sample_id"),
            cr_ids=body.get("change_request_ids"),
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(results=results)


@api_v1_bp.post("/change-sets/<int:change_set_id>/samples")
@require_role(*_WORKING)
def draw_sample(change_set_id: int):
    """Draws the sample that a bulk decision at `step` needs (step: domain, reviewer, admin,
    chief-engineer; domain steps name the `domain`)."""
    body = _body()
    try:
        sample = BulkService.draw_sample(
            change_set_id,
            body.get("step", ""),
            current_user,
            domain_code=body.get("domain"),
            cr_ids=body.get("change_request_ids"),
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(sample_payload(sample)), 201


@api_v1_bp.get("/change-sets/<int:change_set_id>/samples")
@require_role(*_SEEING)
def list_samples(change_set_id: int):
    return jsonify(items=[sample_payload(s) for s in BulkService.samples(change_set_id)])


@api_v1_bp.get("/bulk-samples/<int:sample_id>")
@require_role(*_SEEING)
def get_bulk_sample(sample_id: int):
    try:
        return jsonify(sample_payload(BulkService.get_sample(sample_id)))
    except DomainError as exc:
        return error_response(exc)


@api_v1_bp.put("/bulk-samples/<int:sample_id>/items/<int:cr_id>")
@require_role(*_WORKING)
def set_sample_verdict(sample_id: int, cr_id: int):
    body = _body()
    try:
        sample = BulkService.record_verdict(
            sample_id, cr_id, body.get("verdict", ""), body.get("note"), current_user
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(sample_payload(sample))


@api_v1_bp.post("/bulk-samples/<int:sample_id>/reject-defects")
@require_role(*_WORKING)
def reject_sample_defects(sample_id: int):
    body = _body()
    try:
        results = BulkService.reject_defects(
            sample_id, current_user, body.get("current_password"), body.get("comment")
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(results=results)


@api_v1_bp.get("/change-sets/<int:change_set_id>/dossier.xlsx")
@require_role(*_SEEING)
def change_set_dossier(change_set_id: int):
    try:
        content = BulkService.dossier(change_set_id)
    except DomainError as exc:
        return error_response(exc)
    return Response(
        content,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=cscm_change-set-{change_set_id}_dossier.xlsx"
        },
    )

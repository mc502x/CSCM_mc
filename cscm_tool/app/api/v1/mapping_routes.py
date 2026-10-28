"""The legacy -> new status code mapping and its change requests (FR-191..FR-198). See
docs/artifacts/openapi.yaml /mapping, /mapping-changes. A row is changed only by a request that the
StCd Owner, the Chief Engineer and an Administrator all approve."""

import json

from flask import Response, jsonify, request
from sqlalchemy.exc import OperationalError

from app.api.v1 import api_v1_bp
from app.api.v1._errors import error_response
from app.auth.decorators import current_user, require_role
from app.domain.errors import DomainError
from app.extensions import db
from app.models.mapping import StatusCodeMapping
from app.services.mapping_service import (
    ACTIONS,
    APPROVER_ROLES,
    FAMILIES,
    REQUEST_ROLES,
    STATUSES,
    VIEW_ROLES,
    MappingError,
    MappingService,
    differences,
    row_dict,
)

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@api_v1_bp.errorhandler(OperationalError)
def _database_not_upgraded(exc: OperationalError):
    message = str(exc.orig) if exc.orig is not None else str(exc)
    if "no such table" not in message or "mapping" not in message:
        raise exc
    db.session.rollback()
    return (
        jsonify(
            error="database_not_upgraded",
            message=(
                "The database has not been upgraded: run `flask db upgrade` "
                "and `flask mapping-seed`."
            ),
        ),
        503,
    )


def row_payload(model: StatusCodeMapping) -> dict:
    row = row_dict(model)
    row.update(id=model.id, version=model.version, updated_at=model.updated_at)
    row["identifier"] = f"StCd-{model.new_number:05d}"
    return row


def change_payload(change, items: bool = False) -> dict:
    out = {
        "id": change.id,
        "title": change.title,
        "reason": change.reason,
        "origin": change.origin,
        "state": change.state,
        "requested_by": change.requester.full_name,
        "requested_at": change.requested_at,
        "closed_at": change.closed_at,
        "rows": len(change.items),
        "approvals": [
            {
                "role": role,
                "decision": a.decision if a else None,
                "by": a.user.full_name if a else None,
                "at": a.decided_at if a else None,
                "comment": a.comment if a else None,
            }
            for role, a in MappingService.who_decides(change).items()
        ],
    }
    if items:
        out["items"] = []
        for item in change.items:
            before = json.loads(item.before_json) if item.before_json else None
            after = json.loads(item.after_json)
            out["items"].append(
                {
                    "action": item.action,
                    "mapping_id": item.mapping_id,
                    "new_number": after.get("new_number"),
                    "changed_fields": differences(before, after),
                    "after": after,
                }
            )
    return out


@api_v1_bp.get("/mapping")
@require_role(*VIEW_ROLES)
def mapping_list():
    """Rows of the mapping. Filters: `family` (MC | HC), `status`, `q`; paged by `page`."""
    family = request.args.get("family")
    status = request.args.get("status")
    if family and family not in FAMILIES:
        return jsonify(error="validation_error", message="family must be MC or HC"), 422
    if status and status not in STATUSES:
        return jsonify(error="validation_error", message="unknown status"), 422
    page = max(1, request.args.get("page", 1, type=int) or 1)
    rows, total = MappingService.search(family, status, request.args.get("q"), page, 100)
    return jsonify(
        summary=MappingService.summary(),
        total=total,
        page=page,
        rows=[row_payload(r) for r in rows],
    )


@api_v1_bp.get("/mapping/export")
@require_role(*VIEW_ROLES)
def mapping_export():
    """The mapping as a workbook with the sheets MC and HC (the layout the upload reads)."""
    family = request.args.get("family")
    return Response(
        MappingService.export_xlsx(family if family in FAMILIES else None),
        mimetype=_XLSX,
        headers={"Content-Disposition": "attachment; filename=legacy_mapping.xlsx"},
    )


@api_v1_bp.get("/mapping/<int:mapping_id>")
@require_role(*VIEW_ROLES)
def mapping_get(mapping_id: int):
    try:
        return jsonify(row_payload(MappingService.get(mapping_id)))
    except DomainError as exc:
        return error_response(exc)


@api_v1_bp.post("/mapping-changes")
@require_role(*REQUEST_ROLES)
def mapping_change_create():
    """Opens a change request. Body: `title`, `reason`, `items` = [{action: ADD | CHANGE | CONFIRM |
    REJECT, mapping_id (not for ADD), fields: {...}}]. Nothing changes before the three approvals.
    """
    body = request.get_json(silent=True) or {}
    raw_items = body.get("items")
    if not isinstance(raw_items, list):
        return jsonify(error="validation_error", message="items must be a list"), 422
    try:
        items = []
        for entry in raw_items:
            if not isinstance(entry, dict) or entry.get("action") not in ACTIONS:
                raise MappingError("Every item needs an action: " + ", ".join(ACTIONS) + ".")
            mapping_id = entry.get("mapping_id")
            if mapping_id is not None and type(mapping_id) is not int:
                raise MappingError("mapping_id must be a number.")
            fields = entry.get("fields") or {}
            if not isinstance(fields, dict):
                raise MappingError("fields must be an object.")
            items.append(MappingService.build_item(entry["action"], mapping_id, fields))
        change = MappingService.propose(
            current_user, body.get("title", ""), body.get("reason", ""), items, "FORM"
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(change_payload(change, items=True)), 201


@api_v1_bp.get("/mapping-changes")
@require_role(*VIEW_ROLES)
def mapping_change_list():
    state = request.args.get("state")
    return jsonify(changes=[change_payload(c) for c in MappingService.changes(state)])


@api_v1_bp.get("/mapping-changes/<int:change_id>")
@require_role(*VIEW_ROLES)
def mapping_change_get(change_id: int):
    try:
        return jsonify(change_payload(MappingService.get_change(change_id), items=True))
    except DomainError as exc:
        return error_response(exc)


@api_v1_bp.post("/mapping-changes/<int:change_id>/decisions")
@require_role(*APPROVER_ROLES)
def mapping_change_decide(change_id: int):
    """The StCd Owner, the Chief Engineer and an Administrator each decide once: `decision`
    (APPROVE | REJECT), `comment` (required to reject), `current_password`. The third approval
    applies the change."""
    body = request.get_json(silent=True) or {}
    try:
        change = MappingService.decide(
            change_id,
            current_user,
            body.get("decision", ""),
            body.get("comment"),
            reauth_password=body.get("current_password"),
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(change_payload(change, items=True))


@api_v1_bp.post("/mapping-changes/<int:change_id>/withdraw")
@require_role(*REQUEST_ROLES)
def mapping_change_withdraw(change_id: int):
    try:
        change = MappingService.withdraw(change_id, current_user)
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return jsonify(change_payload(change))


@api_v1_bp.post("/mapping-changes/workbook")
@require_role(*REQUEST_ROLES)
def mapping_change_from_workbook():
    """Compares an uploaded workbook (sheets MC and HC) with the mapping and opens one request
    with every new and every differing row. Form fields: `file`, `title`, `reason`,
    `confirm_unchanged` (1 also asks to approve unchanged proposed rows)."""
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify(error="validation_error", message="file is required"), 422
    try:
        plan = MappingService.plan_from_workbook(
            upload.read(), confirm_unchanged=request.form.get("confirm_unchanged") == "1"
        )
        if plan["problems"]:
            return (
                jsonify(
                    error="validation_error",
                    message="The workbook has problems.",
                    problems=plan["problems"][:100],
                ),
                422,
            )
        items = [
            MappingService.build_item(i["action"], i["mapping_id"], i["after"])
            for i in plan["items"]
        ]
        change = MappingService.propose(
            current_user,
            request.form.get("title", ""),
            request.form.get("reason", ""),
            items,
            "WORKBOOK",
        )
    except (DomainError, ValueError) as exc:
        return error_response(exc)
    return (
        jsonify(change=change_payload(change), counts=plan["counts"], unchanged=plan["unchanged"]),
        201,
    )


@api_v1_bp.post("/mapping/seed")
@require_role("ADMINISTRATOR")
def mapping_seed():
    """Loads the initial mapping from the shipped workbook into an empty table."""
    try:
        return jsonify(loaded=MappingService.seed())
    except (DomainError, ValueError) as exc:
        return error_response(exc)

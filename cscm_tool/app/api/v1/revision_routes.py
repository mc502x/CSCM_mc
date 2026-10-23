"""FR-024/FR-025. See docs/artifacts/openapi.yaml /revisions/{revisionId}."""

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.api.v1.serializers import revision_payload
from app.auth.decorators import current_user, require_role
from app.domain.errors import (
    ConcurrentModificationError,
    InvalidTransitionError,
    NotFoundError,
    SegregationOfDutiesViolation,
)
from app.services.status_code_service import StatusCodeService, ValidationFailed


@api_v1_bp.patch("/revisions/<int:revision_id>")
@require_role("ADMINISTRATOR", "ENGINEER")
def update_revision(revision_id: int):
    body = request.get_json(silent=True) or {}
    try:
        revision = StatusCodeService.update_draft(revision_id, body, current_user)
    except NotFoundError:
        return jsonify(error="not_found", message="Revision not found"), 404
    except SegregationOfDutiesViolation as exc:
        return jsonify(error="forbidden", message=str(exc)), 403
    except ConcurrentModificationError as exc:
        # I-01: tell the client what is stored now so it can merge and retry.
        current = StatusCodeService.get_current_revision_by_id(revision_id)
        return (
            jsonify(
                error="conflict",
                message=str(exc),
                current_row_version=exc.current_row_version,
                current_updated_at=exc.current_updated_at,
                current=revision_payload(current) if current is not None else None,
            ),
            409,
        )
    except InvalidTransitionError as exc:
        return jsonify(error="conflict", message=str(exc)), 409
    except ValidationFailed as exc:
        return (
            jsonify(error="validation_error", message=str(exc), field_errors=exc.field_errors),
            422,
        )
    except (KeyError, ValueError) as exc:
        return jsonify(error="validation_error", message=str(exc)), 422

    return (
        jsonify(revision_payload(revision, warnings=StatusCodeService.warnings_for(revision))),
        200,
    )

"""One translation of service-layer exceptions into API error responses, for the route
modules that do not need their own wording."""

from flask import jsonify

from app.domain.errors import (
    AccountLockedError,
    ConcurrentModificationError,
    DomainError,
    ForbiddenError,
    InvalidTransitionError,
    NotFoundError,
    SegregationOfDutiesViolation,
    StepUpRequiredError,
)
from app.services.status_code_service import ValidationFailed


def error_response(exc: Exception):
    if isinstance(exc, StepUpRequiredError):
        code = "step_up_failed" if exc.wrong_password else "step_up_required"
        return jsonify(error=code, message=str(exc)), 403
    if isinstance(exc, AccountLockedError):
        return jsonify(error="account_locked", message=str(exc)), 403
    if isinstance(exc, ForbiddenError | SegregationOfDutiesViolation):
        return jsonify(error="forbidden", message=str(exc)), 403
    if isinstance(exc, NotFoundError):
        return jsonify(error="not_found", message=str(exc)), 404
    if isinstance(exc, InvalidTransitionError | ConcurrentModificationError):
        return jsonify(error="conflict", message=str(exc)), 409
    if isinstance(exc, ValidationFailed):
        return (
            jsonify(error="validation_error", message=str(exc), field_errors=exc.field_errors),
            422,
        )
    if isinstance(exc, DomainError | ValueError):
        return jsonify(error="validation_error", message=str(exc)), 422
    raise exc

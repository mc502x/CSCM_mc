"""Centralized JSON error handlers for the API surface."""

import logging
import re

from flask import Flask, g, jsonify, request
from flask_wtf.csrf import CSRFError

from app.domain.errors import ForbiddenError

# Control characters (everything below space except tab, line feed and carriage return, and DEL)
# are never part of a title, a name or a comment. They break spreadsheets and PDFs and hide in
# logs, so a write that carries one is refused before any service sees it (found by the API
# fuzz, v4.18.1).
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SECRET_FIELDS = ("password", "passphrase", "token", "secret")


def _strings(value, key: str = ""):
    if isinstance(value, str):
        if not any(s in key.lower() for s in _SECRET_FIELDS):
            yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _strings(v, str(k))
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v, key)


def register_error_handlers(app: Flask) -> None:
    @app.before_request
    def refuse_control_characters():
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return None
        found = []
        if request.is_json:
            found = list(_strings(request.get_json(silent=True)))
        elif request.form:
            for key, values in request.form.lists():
                found.extend(v for v in values if not any(s in key.lower() for s in _SECRET_FIELDS))
        if any(_CONTROL.search(s) for s in found):
            return (
                jsonify(
                    error="validation_error", message="Text must not contain control characters."
                ),
                422,
            )
        return None

    @app.errorhandler(OverflowError)
    def number_too_large(_err):
        """An identifier beyond the range of the database (an integer wider than 64 bits) names
        nothing: it is a missing resource, not a server error."""
        return jsonify(error="not_found", message="Resource not found"), 404

    @app.errorhandler(CSRFError)
    def csrf_error(err):
        return jsonify(error="csrf_error", message=err.description), 400

    @app.errorhandler(ForbiddenError)
    def forbidden(err):
        return jsonify(error="forbidden", message=str(err)), 403

    @app.errorhandler(400)
    def bad_request(err):
        return jsonify(error="bad_request", message=str(err)), 400

    @app.errorhandler(404)
    def not_found(_err):
        return jsonify(error="not_found", message="Resource not found"), 404

    @app.errorhandler(422)
    def unprocessable(err):
        return jsonify(error="validation_error", message=str(err)), 422

    @app.errorhandler(500)
    def internal_error(err):
        logging.getLogger("cscm").error(
            "unhandled exception",
            exc_info=getattr(err, "original_exception", None),
            extra={
                "request_id": g.get("request_id"),
                "method": request.method,
                "path": request.path,
            },
        )
        return jsonify(error="internal_error", message="An unexpected error occurred"), 500

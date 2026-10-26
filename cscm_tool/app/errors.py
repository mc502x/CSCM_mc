"""Centralized JSON error handlers for the API surface."""

import logging

from flask import Flask, g, jsonify, request
from flask_wtf.csrf import CSRFError

from app.domain.errors import ForbiddenError


def register_error_handlers(app: Flask) -> None:
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

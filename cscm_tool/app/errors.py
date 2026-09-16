"""Centralized JSON error handlers for the API surface."""

from flask import Flask, jsonify
from flask_wtf.csrf import CSRFError


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(CSRFError)
    def csrf_error(err):
        return jsonify(error="csrf_error", message=err.description), 400

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
    def internal_error(_err):
        return jsonify(error="internal_error", message="An unexpected error occurred"), 500

"""Centralized JSON error handlers for the API surface."""

from flask import Flask, jsonify


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_err):
        return jsonify(error="not_found", message="Resource not found"), 404

    @app.errorhandler(422)
    def unprocessable(err):
        return jsonify(error="validation_error", message=str(err)), 422

    @app.errorhandler(500)
    def internal_error(_err):
        return jsonify(error="internal_error", message="An unexpected error occurred"), 500

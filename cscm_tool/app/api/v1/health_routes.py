"""Unauthenticated liveness endpoint. See 14-deployment-architecture.md §8."""

from flask import jsonify

from app.api.v1 import api_v1_bp


@api_v1_bp.get("/health")
def health():
    return jsonify(status="ok"), 200

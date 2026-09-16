"""API v1 blueprint registry. Route modules register themselves in api_v1_bp."""

from flask import Blueprint

api_v1_bp = Blueprint("api_v1", __name__)

from app.api.v1 import auth_routes, health_routes, user_routes  # noqa: E402,F401

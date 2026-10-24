"""API v1 blueprint registry. Route modules register themselves in api_v1_bp."""

from flask import Blueprint

api_v1_bp = Blueprint("api_v1", __name__)

from app.api.v1 import (  # noqa: E402,F401
    audit_routes,
    auth_routes,
    change_request_routes,
    domain_signoff_routes,
    export_routes,
    governance_routes,
    health_routes,
    import_routes,
    lookup_routes,
    operations_routes,
    package_routes,
    publication_routes,
    release_routes,
    revision_routes,
    st_import_routes,
    status_code_routes,
    user_routes,
)

"""Server-rendered UI blueprint. Route handlers stay thin — they call the
same service layer the JSON API uses, then render a template or redirect
(POST/redirect/GET), never duplicating business logic
(docs/18-claude-code-implementation-guide.md §1)."""

from flask import Blueprint

from app.auth.decorators import current_user as _current_user

ui_bp = Blueprint("ui", __name__, template_folder="../templates")


@ui_bp.app_context_processor
def _inject_current_user():
    """Makes `current_user` available in every template without each view
    passing it explicitly — the LocalProxy itself forwards truthiness and
    attribute access to whatever _load_current_user() resolves to (None or
    an AuthenticatedUser), so no unwrapping is needed here."""
    return {"current_user": _current_user}


from app.ui import (  # noqa: E402,F401
    admin_views,
    auth_views,
    change_request_views,
    dashboard_views,
    export_views,
    release_views,
    status_code_views,
)

"""Server-rendered UI blueprint. Route handlers stay thin — they call the
same service layer the JSON API uses, then render a template or redirect
(POST/redirect/GET), never duplicating business logic
(docs/18-claude-code-implementation-guide.md §1)."""

from flask import Blueprint, g

from app.auth.decorators import current_user as _current_user

ui_bp = Blueprint("ui", __name__, template_folder="../templates")


@ui_bp.app_context_processor
def _inject_current_user():
    """Makes `current_user` available in every template without each view
    passing it explicitly — the LocalProxy itself forwards truthiness and
    attribute access to whatever _load_current_user() resolves to (None or
    an AuthenticatedUser), so no unwrapping is needed here."""
    return {"current_user": _current_user}


_DECISION_LABELS = {
    "REVIEWER_APPROVE": "Reviewer approved",
    "REVIEWER_REJECT": "Reviewer rejected",
    "ADMIN_APPROVE": "Administrator approved",
    "ADMIN_REJECT": "Administrator rejected",
    "CHIEF_ENGINEER_APPROVE": "Chief Engineer approved",
    "CHIEF_ENGINEER_REJECT": "Chief Engineer rejected",
}


@ui_bp.app_template_global()
def user_label(user_id):
    """ "Full Name (Role)" for a user id, so screens never show a bare "User #4"."""
    if user_id is None:
        return "—"
    cache = g.setdefault("_user_labels", {})
    if user_id not in cache:
        from app.extensions import db
        from app.models.user import User

        user = db.session.get(User, user_id)
        cache[user_id] = (
            f"{user.full_name} ({user.role.code.replace('_', ' ').title()})"
            if user
            else f"Unknown user #{user_id}"
        )
    return cache[user_id]


@ui_bp.app_template_filter()
def decision_label(decision):
    return _DECISION_LABELS.get(decision, "—") if decision else "—"


from app.ui import (  # noqa: E402,F401
    admin_views,
    auth_views,
    change_request_views,
    dashboard_views,
    export_views,
    import_views,
    release_views,
    status_code_views,
)

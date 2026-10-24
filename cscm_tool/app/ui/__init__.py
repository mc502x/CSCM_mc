"""Server-rendered UI blueprint. Route handlers stay thin — they call the
same service layer the JSON API uses, then render a template or redirect
(POST/redirect/GET), never duplicating business logic
(docs/18-claude-code-implementation-guide.md §1)."""

from flask import Blueprint, g

from app.auth.decorators import current_user as _current_user

ui_bp = Blueprint("ui", __name__, template_folder="../templates")


def _translation_access() -> bool:
    """The Translations link is shown to those who review a language or manage the reviewers."""
    if not _current_user:
        return False
    from app.services.translation_review_service import TranslationReviewService

    try:
        return TranslationReviewService.has_access(_current_user)
    except Exception:  # noqa: BLE001 - a database that has not been upgraded yet
        return False


@ui_bp.app_context_processor
def _inject_current_user():
    """Makes `current_user` available in every template without each view
    passing it explicitly — the LocalProxy itself forwards truthiness and
    attribute access to whatever _load_current_user() resolves to (None or
    an AuthenticatedUser), so no unwrapping is needed here.

    v4: also the UI language (I-22), the unread-notice count (I-08) and the
    help lookups (I-35) every page needs."""
    from app import status_code_fields
    from app.auth.roles import role_info
    from app.i18n import LANGUAGE_META, LANGUAGES, RTL_LANGUAGES, current_language

    unread = 0
    if _current_user:
        from app.services.notification_service import NotificationService

        unread = NotificationService.unread_count(_current_user.id)
    beta_languages: frozenset[str] = frozenset()
    if _current_user:
        try:
            from app.services.translation_review_service import TranslationReviewService

            beta_languages = TranslationReviewService.beta_languages()
        except Exception:  # noqa: BLE001 - a database that has not been upgraded yet
            beta_languages = frozenset()
    nav_groups: list[dict] = []
    if _current_user:
        from flask import request

        from app.ui import nav

        nav_groups = nav.visible_menu(
            _current_user,
            request.endpoint or "",
            {"translation_access": _translation_access()},
            nav.nav_counts(_current_user),
        )
    return {
        "nav_groups": nav_groups,
        "beta_languages": beta_languages,
        "current_user": _current_user,
        "ui_lang": current_language(),
        "languages": LANGUAGES,
        "language_meta": LANGUAGE_META,
        "ui_dir": "rtl" if current_language() in RTL_LANGUAGES else "ltr",
        "role_info": role_info,
        "scf": status_code_fields,  # the fields of the generated programs (FR-168)
        "translation_access": _translation_access(),
        "unread_notices": unread,
    }


def _register_translate() -> None:
    # A global (not a context variable) so macros imported without context can call _() too.
    from app.i18n import translate

    ui_bp.add_app_template_global(translate, name="_")


_register_translate()


@ui_bp.app_template_global()
def state_help(status):
    from app.help_content import STATE_GLOSSARY

    return STATE_GLOSSARY.get(status, "")


@ui_bp.app_template_global()
def term_help(key):
    from app.help_content import TERM_GLOSSARY

    return TERM_GLOSSARY.get(key, "")


@ui_bp.app_template_global()
def sort_url(key):
    """The current URL sorted by `key` (a second click on the same key reverses it)."""
    from flask import request, url_for

    descending = request.args.get("sort") == key
    params = {k: v for k, v in request.args.to_dict().items() if k not in ("page", "sort")}
    params["sort"] = f"-{key}" if descending else key
    return url_for(request.endpoint or "ui.dashboard", **{**(request.view_args or {}), **params})


@ui_bp.app_template_global()
def page_url(page):
    """The current URL with ?page= replaced, keeping every other filter (I-26)."""
    from flask import request, url_for

    params = {**request.args.to_dict(), "page": page}
    return url_for(request.endpoint or "ui.dashboard", **{**(request.view_args or {}), **params})


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
    governance_views,
    import_views,
    insight_views,
    publication_views,
    release_views,
    status_code_views,
    terminology_views,
    translation_views,
)

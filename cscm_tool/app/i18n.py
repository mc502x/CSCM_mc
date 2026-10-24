"""UI language (I-22): English and German for the interface chrome; v4.3 adds French, Hindi and
Georgian (app/i18n_extra.py), Arabic (app/i18n_ar.py, right to left), ten more (app/i18n_in.py,
Bengali ... Punjabi, Urdu right to left) and Spanish, Italian and Danish (app/i18n_eu.py): the most
visible strings only - the rest stays English.

A deliberately small mechanism instead of a translation framework: templates call `_('English
text')`, the German catalogue (`app/i18n_de.py`) maps that text to German, and anything
missing falls back to the English text, so an untranslated string is never blank or broken.
The language is a per-user preference (`user.ui_language`); before login it follows the
`?lang=` choice remembered in the session, else the browser's Accept-Language.

Scope: navigation, dashboard, login, list/detail/form labels and the change-request screens.
Flash messages produced by the service layer and the administration screens stay English;
that is listed as a further improvement. tests/system/test_i18n.py checks that every string
a template wraps in `_()` has a German entry."""

import re
from typing import Any

from flask import g, has_request_context, request, session

from app.i18n_de import DE
from app.i18n_extra import CATALOGUES

# code -> (country letters, the language's own name, flag emoji). The name of a language reads
# "GB English" with the letters on the left; the flag is on the right: as an emoji in plain text
# (selects, the translation lookup) and as a drawn SVG in the top-bar menu (templates/_flags.html),
# because Windows shows flag emoji as two letters.
LANGUAGE_META: dict[str, tuple[str, str, str]] = {
    "en": ("GB", "English", "\U0001f1ec\U0001f1e7"),
    "de": ("DE", "Deutsch", "\U0001f1e9\U0001f1ea"),
    "fr": ("FR", "Fran\u00e7ais", "\U0001f1eb\U0001f1f7"),
    "hi": ("IN", "\u0939\u093f\u0928\u094d\u0926\u0940", "\U0001f1ee\U0001f1f3"),
    "ar": ("SA", "\u0627\u0644\u0639\u0631\u0628\u064a\u0629", "\U0001f1f8\U0001f1e6"),
    "bn": ("IN", "বাংলা", "🇮🇳"),
    "mr": ("IN", "मराठी", "🇮🇳"),
    "te": ("IN", "తెలుగు", "🇮🇳"),
    "ta": ("IN", "தமிழ்", "🇮🇳"),
    "gu": ("IN", "ગુજરાતી", "🇮🇳"),
    "ur": ("PK", "اردو", "🇵🇰"),
    "kn": ("IN", "ಕನ್ನಡ", "🇮🇳"),
    "or": ("IN", "ଓଡ଼ିଆ", "🇮🇳"),
    "ml": ("IN", "മലയാളം", "🇮🇳"),
    "pa": ("IN", "ਪੰਜਾਬੀ", "🇮🇳"),
    "es": ("ES", "Español", "🇪🇸"),
    "it": ("IT", "Italiano", "🇮🇹"),
    "da": ("DK", "Dansk", "🇩🇰"),
    "ka": ("GE", "\u10e5\u10d0\u10e0\u10d7\u10e3\u10da\u10d8", "\U0001f1ec\U0001f1ea"),
}
LANGUAGES = {code: f"{cc} {name} {flag}" for code, (cc, name, flag) in LANGUAGE_META.items()}
RTL_LANGUAGES = frozenset(
    {"ar", "ur"}
)  # written right to left: <html dir="rtl">, app.css mirrors the layout
DEFAULT_LANGUAGE = "en"

# Matches _('text') and _("text") in templates (the catalogue-completeness test uses it too).
TEMPLATE_STRING_RE = re.compile(r"""\b_\(\s*(?:'((?:[^'\\]|\\.)*)'|"((?:[^"\\]|\\.)*)")""")


def hidden_languages() -> frozenset[str]:
    """The languages this request may not use (FR-172): no native speaker has completed a review of
    them, and the person is a Viewer or not signed in. Everybody else sees every language, marked
    beta (FR-170); a Viewer who was assigned a language to review sees that one."""
    if not has_request_context():
        return frozenset()
    cached = g.get("hidden_languages")
    if cached is not None:
        return cached
    from app.auth.decorators import current_user

    hidden: frozenset[str] = frozenset()
    if not current_user or current_user.role_code == "VIEWER":
        try:
            from app.services.translation_review_service import TranslationReviewService

            hidden = TranslationReviewService.unreviewed_languages()
            if current_user:
                hidden -= set(TranslationReviewService.assigned_languages(current_user.id))
        except Exception:  # noqa: BLE001 - a database that has not been upgraded yet
            hidden = frozenset()
    g.hidden_languages = hidden
    return hidden


def _withheld(language: str) -> frozenset[str]:
    """The English texts a Viewer or guest reads instead of the translation (FR-176): strings of a
    reviewed language that were added or changed after the review and are not approved yet. Nothing
    is withheld from the working roles or from a Viewer who reviews this language. Worked out once
    per request and language."""
    if not has_request_context():
        return frozenset()
    cache = g.setdefault("withheld_cache", {})
    if language not in cache:
        cache[language] = _compute_withheld(language)
    return cache[language]


def _compute_withheld(language: str) -> frozenset[str]:
    from app.auth.decorators import current_user

    if current_user and current_user.role_code != "VIEWER":
        return frozenset()
    try:
        from app.services.settings_service import SettingsService
        from app.services.translation_review_service import TranslationReviewService

        if SettingsService.get("languages.beta_marker") != "1":
            return frozenset()
        if current_user and language in TranslationReviewService.assigned_languages(
            current_user.id
        ):
            return frozenset()
        return TranslationReviewService.withheld_strings(language)
    except Exception:  # noqa: BLE001 - a database that has not been upgraded yet
        return frozenset()


def usable_languages() -> dict[str, str]:
    """{code: label} of the languages this request may choose."""
    hidden = hidden_languages()
    return {code: label for code, label in LANGUAGES.items() if code not in hidden}


def current_language() -> str:
    if not has_request_context():
        return DEFAULT_LANGUAGE
    cached = g.get("ui_language")
    if cached:
        return cached
    from app.auth.decorators import current_user

    language = None
    if current_user:
        language = getattr(current_user, "ui_language", None)
    if language not in LANGUAGES:
        language = session.get("ui_lang")
    if language not in LANGUAGES:
        best = request.accept_languages.best_match(list(LANGUAGES))
        language = best or DEFAULT_LANGUAGE
    if language in hidden_languages():  # a language a Viewer may not see reads as English
        language = DEFAULT_LANGUAGE
    g.ui_language = language
    return language


def _overrides(language: str) -> dict[str, str]:
    """The accepted proposals of the language, read once per request (translation review,
    docs/26-translations.md). Outside a request, or before the table exists, there are none."""
    if not has_request_context():
        return {}
    cache = g.setdefault("translation_overrides", {})
    if language not in cache:
        from app.translation_catalogue import overrides

        cache[language] = overrides(language)
    return cache[language]


def translate_for(language: str | None, text: str, **values: Any) -> str:
    """The text in a language chosen by the caller, not by the person who is signed in: the words
    around an export follow the language of the export (FR-171). English, or none, is the text."""
    translated = text
    if language and language != "en":
        accepted = _overrides(language).get(text)
        if accepted is not None:
            translated = accepted
        elif language == "de":
            translated = DE.get(text, text)
        else:
            translated = CATALOGUES.get(language, {}).get(text, text)
    return translated % values if values else translated


def translate(text: str, **values: Any) -> str:
    language = current_language()
    translated = text
    if language != "en" and text not in _withheld(language):
        accepted = _overrides(language).get(text)
        if accepted is not None:
            translated = accepted
        elif language == "de":
            translated = DE.get(text, text)
        else:
            translated = CATALOGUES.get(language, {}).get(text, text)
    return translated % values if values else translated

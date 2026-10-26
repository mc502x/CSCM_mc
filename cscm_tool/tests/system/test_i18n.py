"""I-22: the German interface. The catalogue must cover every string a template wraps in `_()`,
placeholders must survive translation, and the language choice must stick.

TC-049. Requirements: FR-155, FR-167.
"""

import re
from pathlib import Path

import pytest

from app.extensions import db
from app.i18n import LANGUAGES, TEMPLATE_STRING_RE, translate
from app.i18n_de import DE
from app.models.user import User
from tests.helpers import PASSWORD, login_as, make_cast

TEMPLATES = Path(__file__).resolve().parents[2] / "app" / "templates"
PLACEHOLDER = re.compile(r"%\((\w+)\)[sd]")

pytestmark = pytest.mark.usefixtures("languages_open")


def _template_strings() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in sorted(TEMPLATES.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        for match in TEMPLATE_STRING_RE.finditer(text):
            string = (match.group(1) or match.group(2)).replace("\\'", "'").replace('\\"', '"')
            found.setdefault(string, []).append(path.name)
    return found


def test_every_template_string_has_a_german_entry():
    missing = {s: files[:2] for s, files in _template_strings().items() if s not in DE}
    assert missing == {}, f"{len(missing)} strings without a German entry"


def test_the_catalogue_has_no_empty_or_identical_entries():
    empty = [k for k, v in DE.items() if not v.strip()]
    assert empty == []
    # an entry identical to its source is dead weight unless it is a proper noun / unit
    identical = [k for k, v in DE.items() if k == v and len(k) > 25]
    assert identical == []


def test_placeholders_survive_translation():
    problems = [
        key
        for key, value in DE.items()
        if sorted(PLACEHOLDER.findall(key)) != sorted(PLACEHOLDER.findall(value))
    ]
    assert problems == []


# FR-167: the strings that stay as they are in every language (a unit, a code, a platform name)
UNTRANSLATED = {"d", "WNEW", "TCC"}


def test_every_language_translates_the_whole_interface_inventory():
    from app.translation_catalogue import catalogue, languages, screens

    inventory = set(screens())
    catalogues = catalogue()
    problems = {}
    for code in languages():
        if code == "en":
            continue
        missing = sorted(inventory - set(catalogues[code]) - UNTRANSLATED)
        wrong = [
            key
            for key, value in catalogues[code].items()
            if sorted(PLACEHOLDER.findall(key)) != sorted(PLACEHOLDER.findall(value))
        ]
        if missing or wrong:
            problems[code] = {"missing": missing[:5], "placeholders": wrong[:5]}
    assert problems == {}
    assert len(languages()) == 19


def test_there_are_no_stale_german_entries_for_removed_template_strings():
    used = set(_template_strings())
    py_sources = " ".join(
        p.read_text(encoding="utf-8")
        for p in (TEMPLATES.parent).rglob("*.py")
        if p.name != "i18n_de.py"
    )
    stale = [k for k in DE if k not in used and k not in py_sources]
    assert len(stale) <= 15, f"{len(stale)} catalogue entries match nothing: {stale[:10]}"


def test_translate_falls_back_to_the_english_text(app):
    with app.test_request_context("/", headers={"Accept-Language": "de"}):
        assert translate("Log in") == DE["Log in"]
        assert translate("A sentence nobody translated") == "A sentence nobody translated"
    with app.test_request_context("/", headers={"Accept-Language": "en"}):
        assert translate("Log in") == "Log in"


def test_the_browser_language_picks_the_login_page_language(client):
    german = client.get("/login", headers={"Accept-Language": "de-DE,de;q=0.9"}).get_data(
        as_text=True
    )
    assert '<html lang="de"' in german and DE["Log in"] in german
    french = client.get("/login", headers={"Accept-Language": "fr,en;q=0.5"}).get_data(as_text=True)
    assert '<html lang="fr"' in french
    english = client.get("/login", headers={"Accept-Language": "ja,en;q=0.5"}).get_data(
        as_text=True
    )
    assert '<html lang="en"' in english
    unsupported = client.get("/login", headers={"Accept-Language": "ja"}).get_data(as_text=True)
    assert '<html lang="en"' in unsupported


def test_the_language_choice_is_remembered_for_the_user(app, client, make_user):
    user = make_user("ENGINEER")
    login_as(client, user)
    assert client.post("/language", data={"lang": "de"}).status_code == 302
    page = client.get("/").get_data(as_text=True)
    assert '<html lang="de"' in page
    with app.app_context():
        assert db.session.get(User, user.id).ui_language == "de"
    client.post("/api/v1/auth/logout")
    client.post("/logout")
    login_as(client, user)  # a new session starts in the saved language
    assert '<html lang="de"' in client.get("/").get_data(as_text=True)
    assert client.post("/language", data={"lang": "klingon"}).status_code == 302
    assert '<html lang="de"' in client.get("/").get_data(as_text=True)  # invalid choice ignored


def test_the_choice_before_login_applies_to_the_login_page(client):
    client.post("/language", data={"lang": "de"})
    assert '<html lang="de"' in client.get("/login").get_data(as_text=True)


def test_the_user_preference_is_exposed_on_the_account_page(client, make_user):
    login_as(client, make_user("VIEWER"))
    html = client.get("/account").get_data(as_text=True)
    assert "Deutsch" in html and "English" in html


@pytest.mark.parametrize("lang", sorted(LANGUAGES))
def test_main_pages_render_in_each_language_without_leaking_format_markers(client, make_user, lang):
    cast = make_cast(make_user)
    login_as(client, cast["admin"])
    client.post("/language", data={"lang": lang})
    for path in (
        "/",
        "/status-codes",
        "/change-requests/mine",
        "/releases",
        "/exports",
        "/help",
        "/notifications",
    ):
        response = client.get(path)
        assert response.status_code == 200, path
        html = response.get_data(as_text=True)
        assert f'<html lang="{lang}"' in html
        assert "%(" not in html and "{{" not in html, path


def test_the_german_login_page_keeps_english_credentials_hint_free_of_secrets(client):
    html = client.get("/login", headers={"Accept-Language": "de"}).get_data(as_text=True)
    assert PASSWORD not in html

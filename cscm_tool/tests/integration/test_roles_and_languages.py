"""The StCd Owner role, the role colours, who may create users and hand out roles, and the three
added interface languages with their flags (docs/03-srs.md FR-156, FR-157, BR-024; docs/11 section 3).

TC-054. Requirements: FR-156, FR-157, BR-024, SEC-032, FR-010, FR-012.
"""

import json
import re
from pathlib import Path

import pytest

from app.auth.roles import (
    OVERSIGHT_ROLES,
    ROLE_CODES,
    ROLES,
    assignable_roles,
    may_change_role,
    role_info,
)
from app.extensions import db
from app.i18n import LANGUAGES, TEMPLATE_STRING_RE
from app.i18n_extra import CATALOGUES
from app.models.audit import AuditLogEntry
from app.models.lookup import LookupLanguage
from app.models.user import User
from tests.helpers import login_as, make_cast

TEMPLATES = Path(__file__).resolve().parents[2] / "app" / "templates"


# ------------------------------------------------------------------------------ the catalogue
def test_the_levels_order_the_roles_and_red_is_the_highest():
    assert ROLE_CODES == (
        "ADMINISTRATOR",
        "STCD_OWNER",
        "CHIEF_ENGINEER",
        "REVIEWER",
        "ENGINEER",
        "VIEWER",
    )
    levels = [ROLES[c].level for c in ROLE_CODES]
    assert levels == sorted(levels, reverse=True) and len(set(levels)) == 6
    assert role_info("ADMINISTRATOR").css == "administrator"
    assert role_info("nobody").level == 0  # an unknown role is drawn, not a crash


def test_who_may_change_which_role_to_which():
    assert assignable_roles("ADMINISTRATOR") == ROLE_CODES
    assert assignable_roles("STCD_OWNER") == ("VIEWER", "ENGINEER", "REVIEWER")
    for role in ("ENGINEER", "REVIEWER", "CHIEF_ENGINEER", "VIEWER", None):
        assert assignable_roles(role) == ()
    low = ("VIEWER", "ENGINEER", "REVIEWER")
    for current in ROLE_CODES:
        for new in ROLE_CODES:
            assert may_change_role("ADMINISTRATOR", current, new)
            assert may_change_role("STCD_OWNER", current, new) == (current in low and new in low)
            assert not may_change_role("CHIEF_ENGINEER", current, new)
    assert "STCD_OWNER" in OVERSIGHT_ROLES and "VIEWER" not in OVERSIGHT_ROLES


# ------------------------------------------------------------------------------ users and roles
def _patch(client, user_id, **body):
    return client.patch(f"/api/v1/users/{user_id}", json=body)


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


def test_only_an_administrator_creates_users(client, cast):
    body = {
        "username": "newbie",
        "email": "newbie@example.com",
        "full_name": "New Person",
        "password": "a genuinely long passphrase",
    }
    for who in ("stcd_owner", "chief_engineer", "reviewer", "engineer", "viewer"):
        login_as(client, cast[who])
        assert client.post("/api/v1/users", json=body).status_code == 403, who
    login_as(client, cast["admin"])
    created = client.post("/api/v1/users", json={**body, "role": "STCD_OWNER"})
    assert created.status_code == 201 and created.get_json()["role"] == "STCD_OWNER"


def test_the_stcd_owner_moves_users_between_viewer_engineer_and_reviewer(app, client, cast):
    login_as(client, cast["stcd_owner"])
    listing = client.get("/api/v1/users")
    assert listing.status_code == 200 and listing.get_json()["total"] >= 7
    viewer_id, engineer_id = cast["viewer"].id, cast["engineer"].id
    assert _patch(client, viewer_id, role="REVIEWER").get_json()["role"] == "REVIEWER"
    assert _patch(client, engineer_id, role="VIEWER").get_json()["role"] == "VIEWER"
    assert _patch(client, viewer_id, role="ENGINEER").status_code == 200
    with app.app_context():
        entry = (
            db.session.query(AuditLogEntry)
            .filter_by(action="ROLE_CHANGE", entity_id=viewer_id)
            .order_by(AuditLogEntry.id.desc())
            .first()
        )
        assert json.loads(entry.before_value) == {"role": "REVIEWER"}
        assert json.loads(entry.after_value) == {"role": "ENGINEER"}
        assert entry.actor_id == cast["stcd_owner"].id


@pytest.mark.parametrize(
    "target,new_role",
    [
        ("viewer", "CHIEF_ENGINEER"),  # nobody is promoted past Reviewer by the owner
        ("engineer", "ADMINISTRATOR"),
        ("reviewer", "STCD_OWNER"),
        ("admin", "VIEWER"),  # and the higher roles cannot be touched at all
        ("chief_engineer", "REVIEWER"),
        ("stcd_owner", "VIEWER"),
    ],
)
def test_the_stcd_owner_cannot_reach_the_other_roles(client, cast, target, new_role):
    login_as(client, cast["stcd_owner"])
    refused = _patch(client, cast[target].id, role=new_role)
    assert refused.status_code == 403 and "BR-024" in refused.get_json()["message"]


def test_the_stcd_owner_changes_nothing_but_the_role(app, client, cast):
    login_as(client, cast["stcd_owner"])
    target = cast["engineer"].id
    for body in (
        {"full_name": "Renamed"},
        {"is_active": False},
        {"engineering_domains": ["CONTROLS"]},
        {"role": "REVIEWER", "full_name": "Renamed"},
    ):
        assert _patch(client, target, **body).status_code == 403, body
    assert client.post(f"/api/v1/users/{target}/force-reset-password", json={}).status_code == 403
    with app.app_context():
        user = db.session.get(User, target)
        assert user.role.code == "ENGINEER" and user.full_name != "Renamed" and user.is_active


def test_the_administrator_still_gives_every_role(client, cast):
    login_as(client, cast["admin"])
    for role in ("STCD_OWNER", "CHIEF_ENGINEER", "ADMINISTRATOR", "VIEWER"):
        assert _patch(client, cast["viewer"].id, role=role).get_json()["role"] == role


def test_the_last_administrator_is_still_protected(app, client, cast):
    login_as(client, cast["admin"])
    refused = _patch(client, cast["admin"].id, role="VIEWER")
    assert refused.status_code == 422 and refused.get_json()["error"] == "last_administrator"


def test_other_roles_cannot_open_the_user_list(client, cast):
    for who in ("chief_engineer", "reviewer", "engineer", "viewer"):
        login_as(client, cast[who])
        assert client.get("/api/v1/users").status_code == 403, who
        assert client.get("/admin/users").status_code == 403, who


def test_the_stcd_owner_reads_the_workflow_but_changes_nothing_in_it(client, cast):
    login_as(client, cast["stcd_owner"])
    for path in ("/api/v1/change-requests", "/api/v1/change-sets", "/status-codes"):
        assert client.get(path).status_code == 200, path
    # no part in the decisions, the data entry, the imports or the lookups
    assert client.post("/api/v1/status-codes", json={}).status_code == 403
    assert client.post("/api/v1/imports/templates", json={}).status_code in (403, 404, 405)
    assert client.get("/admin/lookups").status_code == 403
    assert client.get("/api/v1/audit-log").status_code == 403
    assert (
        client.post("/api/v1/releases", json={"name": "x", "version_label": "1"}).status_code == 403
    )


# ------------------------------------------------------------------------------ the screens
def test_the_user_page_colours_every_role_and_red_is_the_administrator(client, cast):
    login_as(client, cast["admin"])
    page = client.get("/admin/users").get_data(as_text=True)
    for css in ("administrator", "stcd-owner", "chief-engineer", "reviewer", "engineer", "viewer"):
        assert f"role-badge role-badge--{css}" in page, css
    assert "Create User" in page
    css_file = (TEMPLATES.parent / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert re.search(r"\.role-badge--administrator \{ background: #b71c1c;", css_file)


def test_the_stcd_owner_sees_the_list_without_the_administrator_forms(client, cast):
    login_as(client, cast["stcd_owner"])
    page = client.get("/admin/users").get_data(as_text=True)
    assert "Create User" not in page and "Reset Password" not in page
    assert "Set role" in page and "Administrator only" in page  # the higher roles are read-only
    assert "role-badge--stcd-owner" in client.get("/").get_data(as_text=True)  # top bar badge
    changed = client.post(
        f"/admin/users/{cast['viewer'].id}/update", data={"role": "REVIEWER"}, follow_redirects=True
    )
    assert "User updated." in changed.get_data(as_text=True)
    refused = client.post(
        f"/admin/users/{cast['admin'].id}/update", data={"role": "VIEWER"}, follow_redirects=True
    )
    assert "BR-024" in refused.get_data(as_text=True)
    assert client.post("/admin/users/new", data={"username": "x"}).status_code == 403


# ------------------------------------------------------------------------------ languages
def test_the_language_names_have_the_country_letters_left_and_the_flag_right(app):
    assert list(LANGUAGES) == [
        "en",
        "de",
        "fr",
        "hi",
        "ar",
        "bn",
        "mr",
        "te",
        "ta",
        "gu",
        "ur",
        "kn",
        "or",
        "ml",
        "pa",
        "es",
        "it",
        "da",
        "ka",
    ]
    india = "\U0001f1ee\U0001f1f3"
    expected = {
        "en": ("GB", "\U0001f1ec\U0001f1e7"),  # Britain
        "de": ("DE", "\U0001f1e9\U0001f1ea"),  # Germany
        "fr": ("FR", "\U0001f1eb\U0001f1f7"),  # France
        "hi": ("IN", india),
        "ka": ("GE", "\U0001f1ec\U0001f1ea"),  # Georgia
        "ar": ("SA", "\U0001f1f8\U0001f1e6"),  # Saudi Arabia
        "ur": ("PK", "\U0001f1f5\U0001f1f0"),  # Pakistan
        "es": ("ES", "\U0001f1ea\U0001f1f8"),  # Spain
        "it": ("IT", "\U0001f1ee\U0001f1f9"),  # Italy
        "da": ("DK", "\U0001f1e9\U0001f1f0"),  # Denmark
        **{code: ("IN", india) for code in ("bn", "mr", "te", "ta", "gu", "kn", "or", "ml", "pa")},
    }
    for code, (letters, flag) in expected.items():
        assert LANGUAGES[code].startswith(letters + " ") and LANGUAGES[code].endswith(" " + flag)
    with app.app_context():
        stored = {lang.code: lang.label for lang in db.session.query(LookupLanguage).all()}
    for code, (letters, flag) in expected.items():  # the lookup the translations use agrees
        assert stored[code].startswith(letters + " ") and stored[code].endswith(" " + flag)


@pytest.mark.parametrize(
    "lang,sample",
    [
        ("fr", "Se connecter"),
        ("hi", "लॉग इन करें"),
        ("ka", "შესვლა"),
        ("ar", "تسجيل الدخول"),
        ("bn", "লগ ইন"),
        ("mr", "लॉग इन"),
        ("te", "లాగిన్"),
        ("ta", "உள்நுழை"),
        ("gu", "લૉગ ઇન"),
        ("ur", "لاگ ان"),
        ("kn", "ಲಾಗ್ ಇನ್"),
        ("or", "ଲଗ୍ ଇନ୍"),
        ("ml", "ലോഗിൻ"),
        ("pa", "ਲਾਗ ਇਨ"),
        ("es", "Iniciar sesión"),
        ("it", "Accedi"),
        ("da", "Log ind"),
    ],
)
def test_each_added_language_translates_the_login_page_and_falls_back_to_english(
    client, lang, sample
):
    client.post("/language", data={"lang": lang})
    page = client.get("/login").get_data(as_text=True)
    direction = "rtl" if lang in ("ar", "ur") else "ltr"
    assert f'<html lang="{lang}" dir="{direction}">' in page and sample in page
    assert "%(" not in page


def test_the_menu_shows_letters_left_and_a_drawn_flag_right_for_every_language(client, cast):
    login_as(client, cast["engineer"])
    page = client.get("/").get_data(as_text=True)
    menu = page.split('<details class="lang-menu">', 1)[1].split("</details>", 1)[0]
    assert menu.count('class="flag"') == 20  # the open choice and one per language
    for letters in ("GB", "DE", "FR", "IN", "GE", "SA", "PK", "ES", "IT", "DK"):
        assert f'<span class="lang-code">{letters}</span>' in menu
    # letters, then the name, then the flag
    assert re.search(r'lang-code">GB</span> <span class="lang-name">English</span> <svg', menu)
    assert 'name="lang" value="ar"' in menu and 'name="lang" value="pa"' in menu
    # Arabic is followed by the ten Indian languages, then Spanish, Italian, Danish; Georgian is last
    order = re.findall(r'name="lang" value="(\w+)"', menu)
    assert order[order.index("ar") :] == [
        "ar",
        "bn",
        "mr",
        "te",
        "ta",
        "gu",
        "ur",
        "kn",
        "or",
        "ml",
        "pa",
        "es",
        "it",
        "da",
        "ka",
    ]


def test_the_choice_of_an_added_language_is_remembered_for_the_user(app, client, cast):
    user = cast["engineer"]
    login_as(client, user)
    for lang in ("ka", "hi", "fr", "ar", "ta", "ur", "pa"):
        assert client.post("/language", data={"lang": lang}).status_code == 302
        assert f'<html lang="{lang}"' in client.get("/").get_data(as_text=True)
        with app.app_context():
            assert db.session.get(User, user.id).ui_language == lang  # the CHECK accepts it


def test_arabic_is_right_to_left_but_identifiers_codes_and_numbers_stay_as_they_are(
    client, cast, wcnv_ids
):
    from tests.helpers import valid_payload

    login_as(client, cast["engineer"])
    created = client.post("/api/v1/status-codes", json=valid_payload(*wcnv_ids)).get_json()
    client.post("/language", data={"lang": "ar"})
    page = client.get(f"/status-codes/{created['status_code_id']}").get_data(as_text=True)
    assert 'dir="rtl"' in page
    # what is data, not interface, is never translated: the lifecycle state code, the category
    # value and the title the author wrote
    assert "DRAFT" in page and "ERROR" in page and "Converter Grid Undervoltage Trip" in page
    css = (TEMPLATES.parent / "static" / "css" / "app.css").read_text(encoding="utf-8")
    assert 'html[dir="rtl"] .sidebar' in css


def test_a_string_missing_from_a_catalogue_shows_in_english(client, cast, monkeypatch):
    """Every language is complete (FR-167), but a string that is ever missing must still show."""
    login_as(client, cast["admin"])
    client.post("/language", data={"lang": "ka"})
    monkeypatch.delitem(
        CATALOGUES["ka"], 'Typos are tolerated: "convertor" still finds "converter".'
    )
    page = client.get("/status-codes").get_data(as_text=True)
    assert "სტატუსის კოდები" in page  # translated
    assert "Typos are tolerated" in page  # not in the catalogue: the English text


def _template_strings() -> set[str]:
    found: set[str] = set()
    for path in TEMPLATES.rglob("*.html"):
        for match in TEMPLATE_STRING_RE.finditer(path.read_text(encoding="utf-8")):
            found.add((match.group(1) or match.group(2)).replace("\\'", "'"))
    return found


def test_the_catalogues_agree_and_only_translate_real_strings():
    from app.i18n_eu import CODES as EU
    from app.i18n_in import CODES

    assert set(CATALOGUES) == {"fr", "hi", "ka", "ar", *CODES, *EU}
    assert all(set(CATALOGUES[c]) == set(CATALOGUES["fr"]) for c in EU)
    assert set(CATALOGUES["fr"]) == set(CATALOGUES["hi"]) == set(CATALOGUES["ka"])
    assert set(CATALOGUES["ka"]) == set(CATALOGUES["ar"])
    ten = [CATALOGUES[c] for c in CODES]
    assert all(set(t) == set(ten[0]) for t in ten)  # the ten share one set of strings
    assert set(ten[0]) <= set(CATALOGUES["fr"])  # ... which is part of the main one
    from app.translation_catalogue import screens

    known = set(screens()) | _template_strings() | {r.label for r in ROLES.values()}
    assert [k for k in CATALOGUES["fr"] if k not in known] == []
    for language, catalogue in CATALOGUES.items():
        assert all(v.strip() for v in catalogue.values()), language
        assert len(catalogue) >= (55 if language in CODES else 90), language
        for key, value in catalogue.items():
            assert re.findall(r"%\(\w+\)[sd]", key) == re.findall(r"%\(\w+\)[sd]", value)
    # a catalogue never copies English over: at least the role names differ
    for language in CODES:
        assert CATALOGUES[language]["Viewer"] != "Viewer", language

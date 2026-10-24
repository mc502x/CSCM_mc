"""The menu on the left (docs/10-ui-ux-specification.md section 3, docs/03-srs.md FR-169): what each role
sees, the groups, the counts of what waits, the link of the current page and the Menu button of narrow
windows.

TC-064. Requirements: FR-169, FR-170, FR-172, SEC-010, NFR-010.
"""

import re

import pytest

from tests.helpers import create_draft, domain_sign, login_as, make_cast, submit


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


def _nav(client, path="/"):
    page = client.get(path).get_data(as_text=True)
    nav = page.split('<nav class="sidebar"', 1)[1].split("</nav>", 1)[0]
    links = re.findall(r'<a href="([^"]+)" class="([^"]*)"[^>]*>(.*?)</a>', nav, re.S)
    labels = [re.sub(r"<[^>]+>", "", text).strip() for _href, _cls, text in links]
    titles = [
        re.sub(r"<[^>]+>", "", t).strip()
        for t in re.findall(r'<summary class="sidebar__title">(.*?)</summary>', nav, re.S)
    ]
    return page, nav, links, labels, titles


def _names(labels):
    # a count badge is part of the text of the link: "Review Queue 3"
    return {re.sub(r"\s*\d+\s*$", "", label) for label in labels}


COMMON = {"Dashboard", "Status Codes", "Releases", "Export Center", "Terminology", "Help"}


def test_a_viewer_sees_the_catalogue_and_nothing_to_work_with(client, cast):
    login_as(client, cast["viewer"])
    _page, nav, _links, labels, titles = _nav(client)
    names = _names(labels)
    assert COMMON <= names
    assert not names & {
        "My Change Requests",
        "Review Queue",
        "Library Import",
        "Users",
        "Audit Log",
    }
    assert "+ New Status Code" not in nav
    assert titles == ["Catalogue", "Languages"] or set(titles) <= {"Catalogue", "Languages"}


EXPECTED = {
    "engineer": {
        "present": {
            "My Change Requests",
            "Change Sets",
            "Library Import",
            "Import from .st files",
            "Legacy mapping",
            "Hub Consolidation",
        },
        "absent": {"Review Queue", "Approval Queue", "Users", "Lookups", "Withdrawn Codes"},
        "new_button": True,
    },
    "reviewer": {
        "present": {
            "My Change Requests",
            "Review Queue",
            "Delegation",
            "Catalogue Health",
            "Audit Log",
        },
        "absent": {"Library Import", "Approval Queue", "Users", "Lookups"},
        "new_button": False,
    },
    "chief_engineer": {
        "present": {"Approval Queue", "Success Metrics", "Fleet Feedback", "Audit Log"},
        "absent": {"Review Queue", "Library Import", "Users", "Operations"},
        "new_button": False,
    },
    "admin": {
        "present": {
            "My Change Requests",
            "Review Queue",
            "Library Import",
            "Withdrawn Codes",
            "Stalled Requests",
            "Users",
            "Lookups",
            "Export Profiles",
            "Review Checklist",
            "Settings",
            "Integrations",
            "Operations",
            "Audit Log",
            "New Sandbox Code",
        },
        "absent": {"Approval Queue"},
        "new_button": True,
    },
    "stcd_owner": {
        "present": {"Users", "Change Sets"},
        "absent": {"Lookups", "Operations", "Review Queue", "Library Import", "Withdrawn Codes"},
        "new_button": False,
    },
}


@pytest.mark.parametrize("role", sorted(EXPECTED))
def test_each_role_sees_the_links_of_its_work_and_no_other(client, cast, role):
    login_as(client, cast[role])
    _page, nav, _links, labels, _titles = _nav(client)
    names = _names(labels)
    assert COMMON <= names, COMMON - names
    assert EXPECTED[role]["present"] <= names, EXPECTED[role]["present"] - names
    assert not names & EXPECTED[role]["absent"], names & EXPECTED[role]["absent"]
    assert ("+ New Status Code" in nav) is EXPECTED[role]["new_button"]


def test_no_link_appears_twice_and_the_groups_are_the_planned_ones(client, cast):
    login_as(client, cast["admin"])
    _page, _nav_html, links, labels, titles = _nav(client)
    names = [re.sub(r"\s*\d+\s*$", "", label) for label in labels]
    assert len(names) == len(set(names))  # "Releases" used to be both a group and a link
    assert titles == [
        "Catalogue",
        "Workflow",
        "Import and Migration",
        "Insight",
        "Languages",
        "Administration",
    ]
    hrefs = [href for href, _cls, _text in links]
    assert len(hrefs) == len(set(hrefs))


def test_only_the_link_of_the_current_page_is_marked(client, cast):
    login_as(client, cast["admin"])
    for path, label in (
        ("/status-codes", "Status Codes"),
        ("/releases", "Releases"),
        ("/admin/withdrawn-codes", "Withdrawn Codes"),
        ("/terminology", "Terminology"),
        ("/admin/users", "Users"),
    ):
        _page, _nav_html, links, labels, _titles = _nav(client, path)
        active = [
            re.sub(r"\s*\d+\s*$", "", lab)
            for (_h, cls, _t), lab in zip(links, labels, strict=False)
            if "is-active" in cls
        ]
        assert active == [label], (path, active)
    # the New buttons are not "Status Codes"
    _page, nav_html, _links, _labels, _titles = _nav(client, "/status-codes/new")
    assert (
        nav_html.count("is-active") == 0
        or "Status Codes</a>" not in nav_html.split("is-active")[1][:80]
    )


def test_what_waits_for_the_user_is_counted_in_the_menu(app, client, cast, wcnv_ids):
    draft, cr_id = create_draft(app, client, cast, wcnv_ids)
    domain_sign(client, cast, cr_id)
    assert submit(client, cast, cr_id).status_code == 200

    login_as(client, cast["engineer"])
    _page, nav, _links, labels, _titles = _nav(client)
    assert any(lab.startswith("My Change Requests") and lab.endswith("1") for lab in labels), labels
    # one's own open requests are counted at the link, not on the group: nothing waits for the engineer
    assert not re.search(r'Workflow\s*<span class="nav-count"', nav)

    login_as(client, cast["reviewer"])
    _page, nav, _links, labels, _titles = _nav(client)
    assert any(lab.startswith("Review Queue") and lab.endswith("1") for lab in labels), labels
    # the group shows what waits in it, so a group the user closed does not hide it
    assert re.search(r'Workflow\s*<span class="nav-count"[^>]*>1</span>', nav)

    login_as(client, cast["viewer"])
    _page, nav, _links, _labels, _titles = _nav(client)
    assert "nav-count" not in nav


def test_groups_can_be_closed_and_a_narrow_window_has_a_menu_button(client, cast):
    login_as(client, cast["admin"])
    page, nav, _links, _labels, _titles = _nav(client)
    assert nav.count("<details") == 6 and nav.count(" open>") == 6  # open until the user closes one
    assert 'data-menu-toggle aria-controls="sidebar" aria-expanded="false"' in page
    assert 'id="sidebar"' in nav
    script = client.get("/static/js/app.js").get_data(as_text=True)
    assert "function initMenu" in script and "data-menu-toggle" in script
    css = client.get("/static/css/app.css").get_data(as_text=True)
    assert ".sidebar.is-open" in css and ".menu-toggle" in css


def test_the_menu_is_translated_and_a_group_title_too(client, cast):
    login_as(client, cast["admin"])
    client.post("/language", data={"lang": "de"})
    _page, _nav_html, _links, labels, titles = _nav(client)
    assert "Katalog" in titles and "Import und Migration" in titles and "Sprachen" in titles
    assert "Statuscodes" in " ".join(labels) or any("Status" in lab for lab in labels)


# ------------------------------------------------------------------------- beta languages (FR-170)
def _language_menu(client):
    page = client.get("/").get_data(as_text=True)
    return page.split('<details class="lang-menu">', 1)[1].split("</details>", 1)[0]


def _review(app, cast, language, fingerprint_value=None):
    from app.extensions import db
    from app.models.translation import TranslationReview
    from app.translation_catalogue import effective, fingerprint
    from app.utils import utcnow_iso

    with app.app_context():
        db.session.add(
            TranslationReview(
                language_code=language,
                reviewer_id=cast["reviewer"].id,
                status="COMPLETED",
                started_at=utcnow_iso(),
                completed_at=utcnow_iso(),
                fingerprint=fingerprint_value or fingerprint(effective(language)),
                string_count=1,
            )
        )
        db.session.commit()


def _codes(menu):
    return re.findall(r'<button type="submit" name="lang" value="(\w+)"', menu)


@pytest.mark.parametrize("role", ["engineer", "reviewer", "admin", "chief_engineer", "stcd_owner"])
def test_the_working_roles_see_every_language_and_the_unreviewed_ones_are_marked_beta(
    app, client, cast, role
):
    login_as(client, cast[role])
    menu = _language_menu(client)
    assert len(_codes(menu)) == 19
    assert menu.count('class="beta-tag"') == 18  # every language but the English source
    en_item = menu.split('lang="en"', 1)[1].split("</li>", 1)[0]
    assert "beta-tag" not in en_item
    assert 'lang="fr"' in menu and "beta-tag" in menu.split('lang="fr"', 1)[1].split("</li>", 1)[0]


def test_a_review_of_the_current_text_removes_the_mark_and_an_older_one_does_not_count(
    app, client, cast
):
    from app.extensions import db
    from app.models.translation import TranslationReview

    login_as(client, cast["engineer"])
    _review(app, cast, "fr")
    menu = _language_menu(client)
    assert menu.count('class="beta-tag"') == 17
    assert "beta-tag" not in menu.split('lang="fr"', 1)[1].split("</li>", 1)[0]

    with app.app_context():
        review = db.session.query(TranslationReview).one()
        review.fingerprint = "00000000"  # the text changed since the review
        db.session.commit()
    assert _language_menu(client).count('class="beta-tag"') == 18


def test_a_viewer_sees_only_the_reviewed_languages_and_nothing_marked(app, client, cast):
    login_as(client, cast["viewer"])
    assert _codes(_language_menu(client)) == ["en"]
    _review(app, cast, "fr")
    _review(app, cast, "de")
    menu = _language_menu(client)
    assert sorted(_codes(menu)) == ["de", "en", "fr"] and "beta-tag" not in menu


def test_a_viewer_cannot_choose_or_keep_a_language_nobody_has_reviewed(app, client, cast):
    from app.extensions import db
    from app.models.user import User

    login_as(client, cast["viewer"])
    client.post("/language", data={"lang": "hi"})  # refused: nobody reviewed Hindi
    page = client.get("/").get_data(as_text=True)
    assert '<html lang="en"' in page
    with app.app_context():
        assert db.session.get(User, cast["viewer"].id).ui_language == "en"
        # a preference stored before the rule (or while the person had another role) reads as English
        db.session.get(User, cast["viewer"].id).ui_language = "de"
        db.session.commit()
    assert '<html lang="en"' in client.get("/").get_data(as_text=True)
    _review(app, cast, "de")
    assert '<html lang="de"' in client.get("/").get_data(as_text=True)


def test_a_viewer_who_reviews_a_language_sees_that_one(app, client, cast):
    from app.extensions import db
    from app.models.translation import LanguageReviewer
    from app.utils import utcnow_iso

    with app.app_context():
        db.session.add(
            LanguageReviewer(
                user_id=cast["viewer"].id,
                language_code="ur",
                assigned_by=cast["admin"].id,
                assigned_at=utcnow_iso(),
            )
        )
        db.session.commit()
    login_as(client, cast["viewer"])
    assert sorted(_codes(_language_menu(client))) == ["en", "ur"]


def test_the_login_page_offers_only_the_reviewed_languages(app, client, cast):
    page = client.get("/login").get_data(as_text=True)
    options = (
        re.findall(
            r'<option value="(\w+)"', page.split('id="lang"', 1)[-1].split("</select>", 1)[0]
        )
        if 'id="lang"' in page
        else re.findall(r'<option value="(\w\w)"', page)
    )
    assert set(options) <= {"en"}
    _review(app, cast, "fr")
    page = client.get("/login").get_data(as_text=True)
    assert 'value="fr"' in page and 'value="hi"' not in page


def test_the_marker_can_be_switched_off_in_the_settings(app, client, cast):
    login_as(client, cast["admin"])
    page = client.get("/admin/settings").get_data(as_text=True)
    assert "languages.beta_marker" in page
    saved = client.post(
        "/admin/settings", data={"s_languages.beta_marker": "0"}, follow_redirects=True
    )
    assert "Settings saved." in saved.get_data(as_text=True)
    assert 'class="beta-tag"' not in _language_menu(client)
    # with the mark off nothing is hidden either
    login_as(client, cast["viewer"])
    assert len(_codes(_language_menu(client))) == 19

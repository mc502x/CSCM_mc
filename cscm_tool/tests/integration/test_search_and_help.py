"""I-31 ranked, typo-tolerant search (with a substring fallback), I-35 in-app help content.

TC-047. Requirements: FR-148, FR-154.
"""

from pathlib import Path

import pytest
from sqlalchemy import text

from app.domain.lifecycle import STATES
from app.extensions import db
from app.help_content import (
    NEXT_STEP,
    QUICK_START,
    ROLE_GLOSSARY,
    ROLES,
    STATE_GLOSSARY,
    TERM_GLOSSARY,
)
from app.repositories import fts
from tests.helpers import login_as, make_cast, valid_payload

GLOSSARY = (Path(__file__).resolve().parents[3] / "docs" / "19-glossary.md").read_text(
    encoding="utf-8"
)


def _create(client, wcnv_ids, **fields):
    resp = client.post("/api/v1/status-codes", json=valid_payload(*wcnv_ids, **fields))
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def _titles(client, query):
    return [
        i["title"]
        for i in client.get(
            "/api/v1/status-codes", query_string={"q": query, "page_size": 50}
        ).get_json()["items"]
    ]


@pytest.fixture()
def corpus(client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    _create(
        client,
        wcnv_ids,
        title="Converter overcurrent trip",
        description="Phase current above limit.",
    )
    _create(
        client,
        wcnv_ids,
        title="Gearbox oil temperature high",
        description="The converter cooling loop is not involved.",
    )
    _create(
        client,
        wcnv_ids,
        title="Pitch battery voltage low",
        description="Emergency battery check failed.",
    )
    return cast


def test_the_search_index_exists_on_a_fresh_database(app):
    with app.app_context():
        fts.forget_availability()
        assert fts.available() is True


def test_prefix_and_multi_word_search(client, corpus):
    assert set(_titles(client, "conv")) == {
        "Converter overcurrent trip",
        "Gearbox oil temperature high",
    }
    assert _titles(client, "converter overcurrent") == ["Converter overcurrent trip"]
    assert _titles(client, "battery voltage") == ["Pitch battery voltage low"]
    assert _titles(client, "zzzz") == []


def test_a_hit_in_the_title_outranks_a_hit_in_the_description(client, corpus):
    assert _titles(client, "converter")[0] == "Converter overcurrent trip"


def test_typos_still_find_the_code(client, corpus):
    assert "Converter overcurrent trip" in _titles(client, "convertor")
    assert "Pitch battery voltage low" in _titles(client, "batery")
    assert _titles(client, "xqzv") == []


def test_several_misspelt_words_are_all_tolerated_together(client, corpus):
    """Each word may expand to a group of close spellings; the groups must be joined with AND
    (a regression: a bare space between a word and a group is an FTS5 syntax error)."""
    assert "Converter overcurrent trip" in _titles(client, "convertor overcurent")
    assert "Pitch battery voltage low" in _titles(client, "pitch batery voltge")
    assert _titles(client, "convertor zzzzqq") == []


def test_search_ignores_fts_operators_and_punctuation(client, corpus):
    for hostile in (
        'converter" OR "x',
        "conv*",
        "(converter",
        "NEAR(a b)",
        "converter -trip",
        "'; DROP TABLE status_code; --",
    ):
        assert (
            client.get("/api/v1/status-codes", query_string={"q": hostile}).status_code == 200
        ), hostile
    assert _titles(client, "converter:") == _titles(client, "converter")


def test_a_new_code_and_an_edit_are_reflected_without_a_rebuild(app, client, corpus, wcnv_ids):
    created = _create(client, wcnv_ids, title="Yaw brake wear detected")
    assert _titles(client, "yaw brake") == ["Yaw brake wear detected"]
    resp = client.patch(
        f"/api/v1/revisions/{created['id']}",
        json={
            **valid_payload(*wcnv_ids, title="Azimuth brake wear detected"),
            "row_version": created["row_version"],
        },
    )
    assert resp.status_code == 200, resp.get_json()
    assert _titles(client, "yaw brake") == [] and _titles(client, "azimuth") == [
        "Azimuth brake wear detected"
    ]


def test_without_the_index_search_falls_back_to_substrings(app, client, corpus):
    with app.app_context():
        for statement in (
            "DROP TABLE IF EXISTS status_code_fts_vocab",
            "DROP TABLE IF EXISTS status_code_fts",
        ):
            db.session.execute(text(statement))
        db.session.commit()
        fts.forget_availability()
        assert fts.available() is False
    assert _titles(client, "overcurrent") == ["Converter overcurrent trip"]
    assert _titles(client, "battery") == ["Pitch battery voltage low"]
    assert client.get("/status-codes?q=converter").status_code == 200


def test_the_search_box_works_on_the_ui_list(client, corpus):
    page = client.get("/status-codes?q=battery").get_data(as_text=True)
    assert "Pitch battery voltage low" in page and "Gearbox oil" not in page


# ------------------------------------------------------------------ help content (I-35)
def test_every_lifecycle_state_role_and_cr_state_has_help():
    assert set(STATE_GLOSSARY) == set(STATES)
    assert set(ROLE_GLOSSARY) == set(ROLES)
    assert set(QUICK_START) <= set(ROLES) and "ENGINEER" in QUICK_START
    for state in ("DRAFT", "REVIEW", "PENDING_APPROVAL", "APPROVED", "REJECTED", "WITHDRAWN"):
        assert NEXT_STEP[state].strip()


def test_help_texts_are_plain_sentences():
    for text_ in [
        *STATE_GLOSSARY.values(),
        *ROLE_GLOSSARY.values(),
        *TERM_GLOSSARY.values(),
        *NEXT_STEP.values(),
    ]:
        assert text_.strip() == text_ and text_.endswith(".") and 20 <= len(text_) <= 400


def test_the_roles_and_states_are_named_in_the_project_glossary():
    names = {
        "Administrator",
        "Engineer",
        "Reviewer",
        "Chief Engineer",
        "Viewer",
        "Draft",
        "Review",
        "Approved",
        "Released",
        "Deprecated",
        "Archived",
        "PendingApproval",
    }
    missing = [n for n in names if f"**{n}**" not in GLOSSARY]
    assert missing == []


def test_new_terms_are_in_the_project_glossary():
    for term in (
        "Step-up",
        "Change Set",
        "Delegation",
        "Manifest",
        "Audit Hash Chain",
        "Row Version",
    ):
        assert f"**{term}**" in GLOSSARY, term


def test_the_help_page_shows_the_quick_start_of_the_signed_in_role(client, make_user):
    cast = make_cast(make_user)
    for key, role in (("engineer", "ENGINEER"), ("reviewer", "REVIEWER"), ("viewer", "VIEWER")):
        login_as(client, cast[key])
        page = client.get("/help").get_data(as_text=True)
        assert QUICK_START[role][0][0] in page
        assert ROLE_GLOSSARY[role].split(".")[0] in page


def test_state_badges_carry_their_glossary_text_as_a_tooltip(client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    _create(client, wcnv_ids)
    page = client.get("/status-codes").get_data(as_text=True)
    assert f'title="{STATE_GLOSSARY["DRAFT"]}"' in page


def test_the_change_request_screen_says_what_happens_next(app, client, make_user, wcnv_ids):
    from tests.helpers import create_draft

    cast = make_cast(make_user)
    _, cr_id = create_draft(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    assert NEXT_STEP["DRAFT"] in client.get(f"/change-requests/{cr_id}").get_data(as_text=True)

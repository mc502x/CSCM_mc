"""New and changed translations are approved separately, and every change of the text or of the
nomenclature goes through the confidence check (docs/03-srs.md FR-176, docs/26-translations.md §8c).

TC-067. Requirements: FR-176, FR-170, FR-172, FR-164.
"""

import json

import pytest

from app import translation_precheck as pc
from app.extensions import db
from app.models.translation import (
    TranslationOverride,
    TranslationReview,
    TranslationReviewItem,
)
from app.services.translation_review_service import TranslationReviewService as Reviews
from app.translation_catalogue import effective, string_id
from app.utils import utcnow_iso
from tests.helpers import login_as, make_cast


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


def _complete_review(app, cast, language="fr"):
    """A completed review in which every string was answered OK."""
    with app.app_context():
        current = effective(language)
        review = TranslationReview(
            language_code=language,
            reviewer_id=cast["reviewer"].id,
            status="COMPLETED",
            started_at=utcnow_iso(),
            completed_at=utcnow_iso(),
            fingerprint="x",
            string_count=len(current),
        )
        db.session.add(review)
        db.session.flush()
        for english, text in current.items():
            db.session.add(
                TranslationReviewItem(
                    review_id=review.id,
                    string_id=string_id(english),
                    english=english,
                    current_text=text,
                    verdict="OK",
                    decision="PENDING",
                    updated_at=utcnow_iso(),
                )
            )
        db.session.commit()


def _change(app, cast, english="Dashboard", text="XYZ-Tableau", language="fr"):
    with app.app_context():
        db.session.add(
            TranslationOverride(
                language_code=language,
                string_id=string_id(english),
                english=english,
                text=text,
                created_by=cast["admin"].id,
                created_at=utcnow_iso(),
            )
        )
        db.session.commit()


# ------------------------------------------------------------------ approval of the delta
def test_a_reviewed_language_has_nothing_pending_until_a_string_changes(app, cast):
    with app.app_context():
        assert len(Reviews.pending("fr")) == len(effective("fr"))  # no review yet
    _complete_review(app, cast)
    with app.app_context():
        assert Reviews.pending("fr") == {}
    _change(app, cast)
    with app.app_context():
        assert Reviews.pending("fr") == {"Dashboard": "XYZ-Tableau"}
        assert "fr" in Reviews.beta_languages()


def test_a_viewer_reads_a_changed_string_in_english_until_it_is_approved(app, client, cast):
    _complete_review(app, cast)
    _change(app, cast)
    login_as(client, cast["viewer"])
    client.post("/language", data={"lang": "fr"})
    page = client.get("/").get_data(as_text=True)
    assert '<html lang="fr"' in page  # the language is reviewed: still offered
    assert "XYZ-Tableau" not in page and ">Dashboard<" in page  # the new text is withheld
    assert "Codes de statut" in page  # the approved strings stay French

    login_as(client, cast["engineer"])  # the working roles see what is pending
    client.post("/language", data={"lang": "fr"})
    assert "XYZ-Tableau" in client.get("/").get_data(as_text=True)


def test_a_language_never_reviewed_stays_hidden_from_a_viewer(app, client, cast):
    login_as(client, cast["viewer"])
    menu = client.get("/").get_data(as_text=True).split('<details class="lang-menu">', 1)[1]
    assert 'value="fr"' not in menu.split("</details>", 1)[0]


def test_a_follow_up_review_covers_only_what_is_new_or_changed(app, client, cast):
    from app.models.translation import LanguageReviewer

    _complete_review(app, cast)
    _change(app, cast, "Dashboard", "XYZ-Tableau")
    _change(app, cast, "Languages", "XYZ-Langues")
    with app.app_context():
        db.session.add(
            LanguageReviewer(
                user_id=cast["reviewer"].id,
                language_code="fr",
                assigned_by=cast["admin"].id,
                assigned_at=utcnow_iso(),
            )
        )
        db.session.commit()
    login_as(client, cast["reviewer"])
    page = client.get("/translations/fr").get_data(as_text=True)
    assert "New and changed translations (2)" in page and "All translations (" in page
    assert "XYZ-Tableau" in page and "XYZ-Langues" in page
    assert "Connexion" not in page.split("<tbody", 1)[1]  # the approved strings are not listed

    with app.app_context():
        review = Reviews.start("fr", _auth(cast["reviewer"]))
        # completing needs a verdict for the two strings only
        with pytest.raises(ValueError, match="2 of 2 strings"):
            Reviews.complete(review.id, _auth(cast["reviewer"]))
        Reviews.save(
            review.id,
            [
                {"string_id": string_id("Dashboard"), "verdict": "OK"},
                {"string_id": string_id("Languages"), "verdict": "OK"},
            ],
            _auth(cast["reviewer"]),
        )
        Reviews.complete(review.id, _auth(cast["reviewer"]))
        assert Reviews.pending("fr") == {}
        assert "fr" not in Reviews.beta_languages()


def test_an_accepted_proposal_is_approved_and_an_undecided_one_is_not(app, cast):
    _complete_review(app, cast)
    with app.app_context():
        review = db.session.query(TranslationReview).one()
        item = db.session.query(TranslationReviewItem).filter_by(english="Dashboard").one()
        item.verdict, item.proposal, item.decision = "CHANGE", "Tableau", "PENDING"
        db.session.commit()
        assert "Dashboard" not in Reviews.approved("fr")  # undecided: approves nothing
        assert review.status == "COMPLETED"
        item.decision = "REJECTED"
        db.session.commit()
        assert Reviews.approved("fr")["Dashboard"] == item.current_text  # the text stays, approved


class _Auth:
    def __init__(self, user):
        self.id, self.role_code = user.id, user.role.code


def _auth(user):
    return _Auth(user)


# ------------------------------------------------------------------ the confidence check
def test_the_colour_intervals_run_from_red_to_green():
    assert pc.bucket(30) == 0 and pc.bucket(50) == 0  # 50 % or less: red
    assert pc.bucket(50.1) == 1 and pc.bucket(75) == 5 and pc.bucket(80) == 6
    assert pc.bucket(95) == 9 and pc.bucket(95.1) == 10  # above 95 %: green
    assert pc.bucket(100) == 10


def test_the_overview_shows_the_confidence_of_every_language_in_colour(client, cast):
    login_as(client, cast["admin"])
    page = client.get("/translations").get_data(as_text=True)
    record = pc.load()["languages"]
    assert len(record) == 18
    for code in ("de", "or"):
        shown = f"{round(record[code]['confidence'])} %"
        bucket = pc.bucket(record[code]["confidence"])
        assert f'class="conf conf-b{bucket}"' in page and shown in page
    assert "not a review" in page.lower() or "It is not a review" in page


def test_the_record_holds_a_confidence_for_every_language_with_its_findings():
    languages = pc.load()["languages"]
    assert set(languages) == {c for c in pc.catalogue() if c != "en"}
    for code, row in languages.items():
        assert 0 < row["confidence"] <= 100, code
        assert row["sample_size"] == 160 and row["haircut"] > 0
        assert row["mechanical"]["placeholders"] == 0 and row["mechanical"]["missing"] == 0
        assert row["errors"] == sum(1 for f in row["findings"] if f["kind"] == "E")
    assert languages["or"]["confidence"] < languages["fr"]["confidence"]  # the checker's own doubt


def test_every_change_of_the_text_or_the_nomenclature_has_been_through_the_check():
    """The gate: this fails while a string or a term changed and the check was not done for it.
    Run `python scripts/translation_precheck.py --check`, read the changed strings and record a
    verdict for each with `--delta` (docs/26-translations.md §8c)."""
    found = pc.changes()
    summary = {lang: len(strings) for lang, strings in found["strings"].items()}
    assert not found["glossary_changed"], "the nomenclature changed: check it, then --delta"
    assert summary == {}, f"strings changed since the last confidence check: {summary}"


@pytest.fixture()
def workbench(tmp_path, monkeypatch):
    """The record and its state in a scratch folder, so the real ones stay as they are."""
    result, state = tmp_path / "precheck.json", tmp_path / "precheck_state.json"
    result.write_text(pc.RESULT.read_text(encoding="utf-8"), encoding="utf-8")
    state.write_text(pc.STATE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(pc, "RESULT", result)
    monkeypatch.setattr(pc, "STATE", state)
    return result


def test_a_changed_string_must_get_a_verdict_before_the_record_is_current(workbench, monkeypatch):
    from app import i18n_de

    monkeypatch.setitem(i18n_de.DE, "Dashboard", "Neue Übersicht")
    found = pc.changes()
    assert found["strings"] == {"de": ["Dashboard"]} and not pc.is_current()
    before = json.loads(workbench.read_text(encoding="utf-8"))["languages"]["de"]["confidence"]

    with pytest.raises(ValueError, match="no verdict"):
        pc.record(delta={"checked": {}})
    with pytest.raises(ValueError, match="must be OK, A or E"):
        pc.record(delta={"checked": {"de": [{"english": "Dashboard", "kind": "fine"}]}})

    pc.record(
        delta={
            "checked_by": "test",
            "checked": {"de": [{"english": "Dashboard", "kind": "A", "note": "stiff"}]},
        }
    )
    assert pc.is_current()
    after = json.loads(workbench.read_text(encoding="utf-8"))
    assert after["languages"]["de"]["confidence"] <= before  # an awkward string cannot raise it
    assert after["languages"]["de"]["checked"][string_id("Dashboard")]["kind"] == "A"
    assert after["history"][-1]["by"] == "test"


def test_a_change_of_the_nomenclature_needs_the_flag_as_well(workbench, monkeypatch):
    from app import terminology_seed

    real = terminology_seed.terms()
    changed = [dict(t) for t in real]
    changed[0] = {**changed[0], "english": changed[0]["english"] + " (changed)"}
    monkeypatch.setattr(pc, "terms", lambda: changed)
    assert pc.changes()["glossary_changed"]
    with pytest.raises(ValueError, match="nomenclature"):
        pc.record(delta={"checked": {}})
    pc.record(delta={"nomenclature_checked": True, "checked": {}})
    assert not pc.changes()["glossary_changed"]


def test_a_delta_read_one_by_one_can_lower_or_keep_the_confidence(workbench, monkeypatch):
    from app import i18n_extra

    table = i18n_extra.CATALOGUES["ka"]
    monkeypatch.setitem(table, "Dashboard", table["Dashboard"] + "!")
    row = {"english": "Dashboard", "kind": "E", "note": "wrong"}
    pc.record(delta={"checked": {"ka": [row]}})
    data = json.loads(workbench.read_text(encoding="utf-8"))["languages"]["ka"]
    assert data["checked"] and data["confidence"] < 100

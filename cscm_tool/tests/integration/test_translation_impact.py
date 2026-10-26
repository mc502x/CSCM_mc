"""A change of the vocabulary is tested automatically and its language impact reaches the StCd Owner
(docs/03-srs.md FR-178, docs/26-translations.md §8d).

TC-068. Requirements: FR-178, FR-176, FR-177, FR-166.
"""

import pytest

from app import translation_precheck as pc
from app.extensions import db
from app.models.operations import Notification
from app.models.translation import LanguageReviewer
from app.services.terminology_service import TerminologyService
from app.services.translation_impact_service import KIND, TranslationImpactService
from app.utils import utcnow_iso
from tests.helpers import login_as, make_cast


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


class _Auth:
    def __init__(self, user):
        self.id, self.role_code = user.id, user.role.code


def _notices(user_id):
    return [
        n.message
        for n in db.session.query(Notification).filter_by(user_id=user_id, kind=KIND).all()
    ]


def _add_term(cast, code="cable-loop", english="Cable loop", keep=False):
    return TerminologyService.create_term(
        code=code,
        english=english,
        category="PRODUCT",
        definition="The loop of the power cable in the tower.",
        keep_english=keep,
        actor=_Auth(cast["stcd_owner"]),
    )


def test_a_new_term_tells_the_stcd_owner_which_languages_need_attention(app, cast):
    with app.app_context():
        _add_term(cast)
        [message] = _notices(cast["stcd_owner"].id)
    assert "Terminology added: 'Cable loop'" in message
    assert "18 of 18 languages need attention" in message
    assert "no approved translation in" in message and "and 12 more" in message


def test_the_reviewer_of_an_affected_language_is_told_too(app, cast):
    with app.app_context():
        db.session.add(
            LanguageReviewer(
                user_id=cast["viewer"].id,
                language_code="fr",
                assigned_by=cast["admin"].id,
                assigned_at=utcnow_iso(),
            )
        )
        db.session.commit()
        _add_term(cast)
        assert len(_notices(cast["viewer"].id)) == 1
        assert _notices(cast["engineer"].id) == []  # nobody else is bothered


def test_a_term_that_stays_in_english_touches_no_language(app, cast):
    with app.app_context():
        _add_term(cast, "wxyz", "WXYZ", keep=True)
        [message] = _notices(cast["stcd_owner"].id)
    assert "stays in English in every language" in message


def test_a_changed_term_and_an_approved_translation_are_reported_again(app, cast):
    with app.app_context():
        term = _add_term(cast)
        owner, chief = _Auth(cast["stcd_owner"]), _Auth(cast["chief_engineer"])
        TerminologyService.update_term(
            term.id,
            english="Cable loop section",
            category="PRODUCT",
            definition="x",
            keep_english=False,
            is_active=True,
            actor=owner,
        )
        translation = TerminologyService.propose(term.id, "fr", "Boucle de câble", None, chief)
        TerminologyService.approve(translation.id, owner)
        messages = _notices(cast["stcd_owner"].id)
    assert len(messages) == 3
    assert any("changed" in m for m in messages)
    assert any("translation approved" in m and "fr" in m for m in messages)


def test_a_failing_notice_never_undoes_the_change(app, cast, monkeypatch):
    def broken(_term):
        raise RuntimeError("boom")

    monkeypatch.setattr(TranslationImpactService, "term_impact", staticmethod(broken))
    with app.app_context():
        term = _add_term(cast)
        assert term.id and _notices(cast["stcd_owner"].id) == []


def test_the_notice_appears_on_the_notices_page_of_the_stcd_owner(app, client, cast):
    with app.app_context():
        _add_term(cast)
    login_as(client, cast["stcd_owner"])
    page = client.get("/notifications").get_data(as_text=True)
    assert "Terminology added" in page and "Cable loop" in page


# ------------------------------------------------------------------ shipped text and nomenclature
def test_nothing_is_reported_while_the_confidence_check_is_current(app, cast):
    with app.app_context():
        assert TranslationImpactService.catalogue_impact() == {
            "glossary_changed": False,
            "rows": [],
        }
        assert TranslationImpactService.notify_catalogue_changes() == 0


def test_changed_shipped_text_is_reported_once_per_change(app, cast, monkeypatch):
    changed = {
        "strings": {"fr": ["Dashboard", "Languages"], "de": ["Dashboard"]},
        "glossary_changed": False,
    }
    monkeypatch.setattr(pc, "changes", lambda: changed)
    with app.app_context():
        first = TranslationImpactService.notify_catalogue_changes()
        again = TranslationImpactService.notify_catalogue_changes()
        [message] = _notices(cast["stcd_owner"].id)
    assert first >= 1 and again == 0  # the same change is not announced twice
    assert "3 strings in 2 languages" in message and "fr (2)" in message
    assert "confidence check must be recorded" in message

    changed["strings"]["ka"] = ["Languages"]  # a further change is a new notice
    with app.app_context():
        assert TranslationImpactService.notify_catalogue_changes() >= 1
        assert len(_notices(cast["stcd_owner"].id)) == 2


def test_a_changed_nomenclature_is_named_in_the_notice(app, cast, monkeypatch):
    monkeypatch.setattr(pc, "changes", lambda: {"strings": {}, "glossary_changed": True})
    with app.app_context():
        assert TranslationImpactService.notify_catalogue_changes() >= 1
        [message] = _notices(cast["stcd_owner"].id)
    assert "The technical nomenclature changed." in message


def test_the_command_for_the_deployment_reports_and_notifies(app, cast, monkeypatch):
    monkeypatch.setattr(
        pc, "changes", lambda: {"strings": {"fr": ["Dashboard"]}, "glossary_changed": False}
    )
    result = app.test_cli_runner().invoke(args=["translation-impact"])
    assert result.exit_code == 0, result.output
    assert "fr: 1 changed" in result.output and '"notices": 1' in result.output


def test_the_start_of_the_server_and_the_installers_run_the_check():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    assert "notify_catalogue_changes" in (root / "wsgi.py").read_text(encoding="utf-8")
    for installer in ("deploy/linux/install.sh", "deploy/windows/install.ps1"):
        assert "translation-impact" in (root / installer).read_text(encoding="utf-8")

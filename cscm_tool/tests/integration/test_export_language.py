"""The words around an export follow the language of the export (docs/03-srs.md FR-171): the title
page, the column headings of the PDF, the footer and the notice are printed in the language chosen for
the export; English stays the default and the data rows are never touched.

TC-065. Requirements: FR-171, FR-165, FR-110, FR-045.
"""

import pytest

from app.export import pdf_exporter as pdf
from app.i18n import translate_for
from app.services.export_service import TITLE_PAGE_TEXT
from app.translation_catalogue import languages

ROWS = [
    {
        "status_code_identifier": "StCd-01000",
        "functional_system_group": "WCNV",
        "functional_subgroup": "010xx",
        "title": "Converter not ready",
        "description": "The converter is not ready for operation.",
        "status_category": "ERROR",
        "alarm_flag": False,
        "set_delay": "10ms",
        "reset_delay": "2min",
        "turbine_platforms": "3XM",
        "lifecycle_status": "RELEASED",
    }
]
TITLE = {
    "heading": None,
    "lines": [("Release", "R1")],
    "content_digest": "ab" * 32,
    "footer": "CSCM Tool",
}


@pytest.fixture()
def printed(monkeypatch):
    """Every text the PDF writes."""
    seen: list[str] = []
    for name in ("cell", "multi_cell"):
        original = getattr(pdf._CataloguePdf, name)

        def spy(self, *args, _original=original, **kwargs):
            text = kwargs.get("text") or (args[2] if len(args) > 2 else "")
            if isinstance(text, str) and not kwargs.get("dry_run"):
                seen.append(text)
            return _original(self, *args, **kwargs)

        monkeypatch.setattr(pdf._CataloguePdf, name, spy)
    return seen


def test_a_pdf_in_french_prints_its_own_words_in_french(printed):
    pdf.build_pdf(
        ROWS, notice="Not for distribution - unapproved data", title=dict(TITLE), language="fr"
    )
    text = "\n".join(printed)
    assert "Catalogue des codes de statut" in text  # the default heading
    assert "Empreinte du contenu" in text  # the digest label
    assert "Code de statut" in text and "Temporisation d'activation" in text  # the columns
    assert "Page 1 sur" in text
    assert "Ne pas diffuser" in text  # the banner
    assert "Converter not ready" in text  # the data is the data


def test_english_and_no_language_leave_the_text_as_it_is(printed):
    pdf.build_pdf(ROWS, title=dict(TITLE))
    text = "\n".join(printed)
    assert "Status code catalogue" in text and "Page 1 of" in text and "Set delay" in text


def test_every_word_around_an_export_exists_in_every_language():
    words = (*pdf.TRANSLATED_TEXT, *TITLE_PAGE_TEXT)
    missing = {
        lang: [w for w in words if translate_for(lang, w) == w and w not in ("Release", "alarm")]
        for lang in languages()
        if lang != "en"
    }
    # a few words are the same in some languages (Release, Version, Alarm, ...): never more than that
    assert all(len(m) <= 4 for m in missing.values()), missing


def test_a_placeholder_survives_in_every_language():
    for lang in languages():
        text = translate_for(lang, "Page %(page)s of %(total)s", page=3, total=9)
        assert "3" in text and "9" in text and "%(" not in text, lang

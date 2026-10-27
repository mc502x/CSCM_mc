"""The PDF export prints every script of the languages the tool offers (docs/03-srs.md FR-165,
docs/21-improvement-ideas.md I-37): Latin, Devanagari, Bengali, Gurmukhi, Gujarati, Odia, Tamil,
Telugu, Kannada, Malayalam, Georgian and Arabic-script text (Arabic, Urdu), shaped and, for Arabic
and Urdu, right to left, with the fonts that ship with the application.

TC-060. Requirements: FR-165, FR-157, FR-045, NFR-008.
"""

import pytest

from app.export import pdf_exporter as pdf
from app.i18n import LANGUAGE_META
from app.i18n_de import DE
from app.i18n_extra import CATALOGUES

SAMPLES = {
    "devanagari": "स्थिति कोड नियंत्रक की जाँच",
    "bengali": "স্থিতি কোড নিয়ন্ত্রক পরীক্ষা",
    "gurmukhi": "ਸਥਿਤੀ ਕੋਡ ਕੰਟਰੋਲਰ ਜਾਂਚ",
    "gujarati": "સ્થિતિ કોડ નિયંત્રક તપાસ",
    "odia": "ସ୍ଥିତି କୋଡ୍ ନିୟନ୍ତ୍ରକ ଯାଞ୍ଚ",
    "tamil": "நிலை குறியீடு கட்டுப்படுத்தி சோதனை",
    "telugu": "స్థితి కోడ్ నియంత్రిక తనిఖీ",
    "kannada": "ಸ್ಥಿತಿ ಕೋಡ್ ನಿಯಂತ್ರಕ ಪರಿಶೀಲನೆ",
    "malayalam": "സ്ഥിതി കോഡ് നിയന്ത്രകം പരിശോധന",
    "georgian": "სტატუსის კოდი კონტროლერის შემოწმება",
    "arabic": "رمز الحالة وحدة التحكم StCd-01000",
    "urdu": "اسٹیٹس کوڈ کنٹرولر کی جانچ",
}


@pytest.fixture()
def registered(monkeypatch):
    """The font keys a build registers."""
    keys: list[str] = []
    original = pdf._CataloguePdf.add_font

    def spy(self, family, *args, **kwargs):
        keys.append(family)
        return original(self, family, *args, **kwargs)

    monkeypatch.setattr(pdf._CataloguePdf, "add_font", spy)
    return keys


def test_the_fonts_and_their_licence_are_bundled_and_shaping_is_available():
    for name in pdf.FONT_FILES.values():
        assert (pdf.FONT_DIR / name).stat().st_size > 20_000, name
    licence = (pdf.FONT_DIR / "OFL.txt").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE" in licence
    assert pdf.SHAPING_AVAILABLE  # uharfbuzz is in requirements.txt


@pytest.mark.parametrize("script,text", SAMPLES.items())
def test_a_script_gets_its_own_font(script, text):
    assert pdf.script_fonts(text)[0] == script
    assert pdf.script_fonts(text + " 12 ms Latin Überprüfung")[0] == script
    assert pdf.is_rtl(text) == (script in ("arabic", "urdu"))


def test_latin_text_needs_no_script_font_and_arabic_is_told_from_urdu():
    assert pdf.script_fonts("Status code StCd-01000 Überprüfung Привет Ελληνικά") == []
    assert pdf.script_fonts("رمز الحالة") == ["arabic"]
    assert pdf.script_fonts("رمز الحالة", language="ur") == ["urdu"]
    assert pdf.script_fonts("اسٹیٹس کوڈ", language="ar") == ["arabic"]  # the language wins
    assert pdf.script_fonts("ASCII then اسٹیٹس")[0] == "urdu"
    assert not pdf.is_rtl("Latin first, then عربي") and pdf.is_rtl("عربي then Latin")


def test_every_script_builds_a_pdf_with_its_font(registered):
    rows = [{"id": f"StCd-{i:05d}", "text": text} for i, text in enumerate(SAMPLES.values())]
    data = pdf.build_pdf(rows, columns=[("id", "ID"), ("text", "Text")])
    assert data.startswith(b"%PDF") and len(data) > 40_000  # the script fonts are embedded
    assert set(SAMPLES) <= set(registered)  # one font per script, registered once each
    assert len(registered) == len(set(registered))


def test_a_plain_latin_export_loads_only_noto_sans(registered):
    pdf.build_pdf(
        [{"a": "Status code", "b": "Überprüfung 12 ms"}], columns=[("a", "A"), ("b", "B")]
    )
    assert registered == [pdf.BASE_FONT]


def test_the_title_page_and_notice_may_carry_any_script(registered):
    data = pdf.build_pdf(
        [{"a": "x"}],
        notice="केवल आंतरिक उपयोग",
        columns=[("a", "ستون")],
        title={
            "heading": "Status code catalogue – कैटलॉग",
            "subtitle": "სტატუსის კოდი",
            "lines": [("Language", "ur"), ("عنوان", "اسٹیٹس")],
            "content_digest": "ab" * 32,
            "footer": "CSCM Tool",
        },
        language="ur",
    )
    assert data.startswith(b"%PDF")
    assert {"devanagari", "georgian", "urdu"} <= set(registered)


def test_shaping_is_switched_on_per_cell_only_where_a_script_needs_it(monkeypatch):
    calls: list[bool] = []
    original = pdf._CataloguePdf.set_text_shaping

    def spy(self, flag=True, *args, **kwargs):
        calls.append(flag)
        return original(self, flag, *args, **kwargs)

    monkeypatch.setattr(pdf._CataloguePdf, "set_text_shaping", spy)
    pdf.build_pdf(
        [{"a": "Latin"}, {"a": SAMPLES["bengali"]}, {"a": "Latin again"}],
        columns=[("a", "A")],
    )
    assert True in calls  # the Bengali cell was shaped
    assert False in calls  # the Latin cells were not (they stay fast)


def test_every_character_of_every_translation_is_drawn_by_a_bundled_font():
    covered = pdf._covered()
    missing: dict[str, set[str]] = {}
    texts = {code: list(cat.values()) for code, cat in CATALOGUES.items()}
    texts["de"] = list(DE.values())
    texts.update({code: [meta[1]] for code, meta in LANGUAGE_META.items()})
    for code, strings in texts.items():
        for text in strings:
            for ch in text:
                if ord(ch) not in covered and ch not in "\n\t​":
                    missing.setdefault(code, set()).add(ch)
    assert missing == {}, missing


def test_a_large_export_stays_fast_for_latin_text():
    import time

    rows = [
        {"id": f"StCd-{i:05d}", "title": f"Converter voltage {i}", "d": "text " * 30}
        for i in range(1500)
    ]
    started = time.perf_counter()
    data = pdf.build_pdf(rows, columns=[("id", "ID"), ("title", "Title"), ("d", "Description")])
    assert data.startswith(b"%PDF") and time.perf_counter() - started < 15  # NFR-001: 5,000 rows

"""PDF catalogue export (FR-045, I-02, FR-165). Uses fpdf2 - pure Python, no system dependency,
consistent with the no-cloud/offline-deployable constraint (docs/11-security-
architecture.md §12, NFR-008).

Cells are wrapped, never truncated: a cut-off description in a document that feeds
technical manuals is misleading data. The header row repeats on every page, a title page
can carry the release name, version, effective date and content digest, and the
page footer shows "Page x of y".

**All scripts (FR-165).** The text is Unicode. Latin, Greek and Cyrillic text is set in the bundled
Noto Sans; a cell that contains Devanagari, Bengali, Gurmukhi, Gujarati, Odia, Tamil, Telugu,
Kannada, Malayalam, Georgian or Arabic-script text additionally gets the Noto font of that script
(Noto Nastaliq Urdu for Urdu, Noto Naskh Arabic for Arabic), is shaped with HarfBuzz (conjuncts,
vowel signs, joining forms) and, for Arabic and Urdu, laid out right to left and right-aligned. The
fonts are under app/static/fonts/ with their licence (SIL Open Font License), so a deployment needs
no font installation and no internet. Plain Latin cells skip the shaping engine and stay fast."""

import functools
import logging
from pathlib import Path
from typing import Any

from fpdf import FPDF
from fpdf.enums import MethodReturnValue

try:  # HarfBuzz binding; without it the scripts are drawn unshaped
    import uharfbuzz  # noqa: F401

    SHAPING_AVAILABLE = True
except ImportError:  # pragma: no cover - uharfbuzz is in requirements.txt
    SHAPING_AVAILABLE = False

_log = logging.getLogger(__name__)
FONT_DIR = Path(__file__).resolve().parents[1] / "static" / "fonts"  # also served to browsers
BASE_FONT = "base"
# font key -> file; the key is also the family name registered with fpdf2
FONT_FILES = {
    BASE_FONT: "NotoSans-Regular.ttf",
    "devanagari": "NotoSansDevanagari-Regular.ttf",
    "bengali": "NotoSansBengali-Regular.ttf",
    "gurmukhi": "NotoSansGurmukhi-Regular.ttf",
    "gujarati": "NotoSansGujarati-Regular.ttf",
    "odia": "NotoSansOriya-Regular.ttf",
    "tamil": "NotoSansTamil-Regular.ttf",
    "telugu": "NotoSansTelugu-Regular.ttf",
    "kannada": "NotoSansKannada-Regular.ttf",
    "malayalam": "NotoSansMalayalam-Regular.ttf",
    "georgian": "NotoSansGeorgian-Regular.ttf",
    "arabic": "NotoNaskhArabic-Regular.ttf",
    "urdu": "NotoNastaliqUrdu-Regular.ttf",
}
# (first, last, font key) code point ranges of the scripts that need their own font
_SCRIPT_RANGES = (
    (0x0900, 0x097F, "devanagari"),
    (0xA8E0, 0xA8FF, "devanagari"),
    (0x0980, 0x09FF, "bengali"),
    (0x0A00, 0x0A7F, "gurmukhi"),
    (0x0A80, 0x0AFF, "gujarati"),
    (0x0B00, 0x0B7F, "odia"),
    (0x0B80, 0x0BFF, "tamil"),
    (0x0C00, 0x0C7F, "telugu"),
    (0x0C80, 0x0CFF, "kannada"),
    (0x0D00, 0x0D7F, "malayalam"),
    (0x10A0, 0x10FF, "georgian"),
    (0x1C90, 0x1CBF, "georgian"),
    (0x2D00, 0x2D2F, "georgian"),
    (0x0600, 0x06FF, "arabic"),
    (0x0750, 0x077F, "arabic"),
    (0x08A0, 0x08FF, "arabic"),
    (0xFB50, 0xFDFF, "arabic"),
    (0xFE70, 0xFEFF, "arabic"),
)
# letters that Urdu (and Persian) use and Arabic does not: their presence selects Nastaliq
_URDU_LETTERS = frozenset("ٹڈڑںےہھیکگچپژ")

LINE_HEIGHT = 3.4
FONT_SIZE = 7
PADDING = 1.0
MARGIN = 10
MIN_COLUMN_MM = 12
COMPRESS = True  # tests switch this off to read the page text
MAX_WEIGHT = 60

# Used when no export profile is chosen: a readable subset of the ~50 columns of the flat
# export (CSV/JSON/XLSX keep every column).
DEFAULT_PDF_FIELDS = (
    ("status_code_identifier", "Status code"),
    ("functional_system_group", "Group"),
    ("functional_subgroup", "Subgroup"),
    ("title", "Title"),
    ("description", "Description"),
    ("status_category", "Category"),
    ("alarm_flag", "Alarm"),
    ("set_delay", "Set delay"),
    ("reset_delay", "Reset delay"),
    ("turbine_platforms", "Platforms"),
    ("lifecycle_status", "State"),
)


_FALLBACK_TEXT = {"→": "->", "≥": ">=", "≤": "<=", "–": "-", "—": "-"}


@functools.cache
def _covered() -> frozenset[int]:
    """The code points that at least one bundled font can draw."""
    from fontTools.ttLib import TTFont

    covered: set[int] = set()
    for name in FONT_FILES.values():
        font = TTFont(FONT_DIR / name, lazy=True)
        covered.update(font.getBestCmap())
        font.close()
    return frozenset(covered)


def clean(value: Any) -> str:
    """The text of a cell: a character no bundled font draws becomes an ASCII stand-in (or `?`)
    rather than an empty gap."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    text = str(value).replace("\r", "")
    if text.isascii():
        return text
    covered = _covered()
    return "".join(
        ch if ord(ch) in covered or ch in "\n\t" else _FALLBACK_TEXT.get(ch, "?") for ch in text
    )


def script_fonts(text: str, language: str | None = None) -> list[str]:
    """The script fonts a text needs besides Noto Sans, the most frequent script first."""
    counts: dict[str, int] = {}
    for ch in text:
        code = ord(ch)
        if code < 0x0600:
            continue
        for first, last, key in _SCRIPT_RANGES:
            if first <= code <= last:
                counts[key] = counts.get(key, 0) + 1
                break
    if "arabic" in counts:
        urdu = language == "ur" or (language != "ar" and any(c in _URDU_LETTERS for c in text))
        if urdu:
            counts["urdu"] = counts.pop("arabic")
    return sorted(counts, key=lambda k: -counts[k])


def is_rtl(text: str) -> bool:
    """True when the first letter with a direction of its own is Arabic-script."""
    for ch in text:
        code = ord(ch)
        if ch.isalpha():
            return any(
                first <= code <= last for first, last, key in _SCRIPT_RANGES if key == "arabic"
            )
    return False


class _CataloguePdf(FPDF):
    def __init__(self, orientation: str, footer_note: str, language: str | None = None):
        super().__init__(orientation=orientation, unit="mm", format="A4")
        self.footer_note = footer_note
        self.language = language
        self._registered: set[str] = set()
        self._register(BASE_FONT)
        self.set_auto_page_break(False)
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.alias_nb_pages()
        self.set_compression(COMPRESS)

    def _register(self, key: str) -> None:
        if key not in self._registered:
            self.add_font(key, "", str(FONT_DIR / FONT_FILES[key]))
            self._registered.add(key)

    def use(self, text: str, size: float) -> bool:
        """Sets the font for `text` (Noto Sans plus the fonts of its scripts, shaping on when it
        contains one); returns True for right-to-left text."""
        keys = script_fonts(text, self.language)
        for key in keys:
            self._register(key)
        # The script font leads and Noto Sans follows for Latin letters, digits and punctuation:
        # fpdf2 2.7.9 misplaces marks of some scripts (Bengali, Odia) when the script font is only
        # a fallback.
        self.set_font(keys[0] if keys else BASE_FONT, size=size)
        self.set_fallback_fonts([BASE_FONT, *keys[1:]] if keys else [])
        shaped = bool(keys) and SHAPING_AVAILABLE
        if shaped != getattr(self, "_shaped", None):
            self.set_text_shaping(shaped)
            self._shaped = shaped
        return is_rtl(text)

    def footer(self) -> None:
        self.set_y(-8)
        self.use(self.footer_note, 6)
        self.set_text_color(90, 90, 90)
        self.cell(0, 4, self.footer_note, align="L")
        self.set_x(MARGIN)
        self.use("", 6)
        self.cell(0, 4, f"Page {self.page_no()} of {{nb}}", align="R")
        self.set_text_color(0, 0, 0)


def _weights(columns: list[tuple[str, str]], rows: list[dict]) -> list[float]:
    sample = rows[:200]
    weights = []
    for field, label in columns:
        longest = max((len(clean(r.get(field))) for r in sample), default=0)
        average = sum(len(clean(r.get(field))) for r in sample) / len(sample) if sample else 0
        weights.append(min(MAX_WEIGHT, max(len(label) + 2, (average + longest) / 2, 6)))
    return weights


def column_widths(columns: list[tuple[str, str]], rows: list[dict], total: float) -> list[float]:
    weights = _weights(columns, rows)
    minimum = MIN_COLUMN_MM * len(columns)
    if minimum >= total:  # too many columns for a page: share the width equally
        return [total / len(columns)] * len(columns)
    spare = total - minimum
    scale = spare / sum(weights)
    return [MIN_COLUMN_MM + w * scale for w in weights]


def _block(pdf: _CataloguePdf, width: float, height: float, text: str, size: float) -> None:
    """A wrapped paragraph in the font of its own script."""
    pdf.use(text, size)
    align = "R" if is_rtl(text) else "L"
    pdf.multi_cell(width, height, text, align=align, new_x="LMARGIN", new_y="NEXT")


def _title_page(pdf: _CataloguePdf, title: dict, notice: str | None) -> None:
    pdf.add_page()
    pdf.set_y(40)
    _block(pdf, 0, 10, clean(title.get("heading") or "Status code catalogue"), 22)
    if title.get("subtitle"):
        _block(pdf, 0, 7, clean(title["subtitle"]), 13)
    pdf.ln(8)
    if notice:
        pdf.set_text_color(180, 0, 0)
        _block(pdf, 0, 6, clean(notice), 11)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(4)
    for label, value in title.get("lines", []):
        pdf.use(clean(label), 10)
        pdf.cell(50, 6, clean(label))
        _block(pdf, 0, 6, clean(value), 10)
    digest = title.get("content_digest")
    if digest:
        pdf.ln(6)
        pdf.use("", 10)
        pdf.cell(0, 6, "Content digest (SHA-256 of the data rows)", new_x="LMARGIN", new_y="NEXT")
        _block(pdf, 0, 4.5, digest, 8)
        pdf.set_text_color(90, 90, 90)
        _block(
            pdf,
            0,
            4,
            "The digest of the file itself is listed in the accompanying manifest "
            "(MANIFEST.json); verify it with `flask verify-export`.",
            8,
        )
        pdf.set_text_color(0, 0, 0)


def _lines(pdf: _CataloguePdf, width: float, text: str) -> tuple[list[str], bool]:
    """The wrapped lines of a cell (measured in the font its text needs) and its direction."""
    rtl = pdf.use(text, FONT_SIZE)
    lines = pdf.multi_cell(width, LINE_HEIGHT, text, dry_run=True, output=MethodReturnValue.LINES)
    return lines, rtl


def _draw_lines(
    pdf: _CataloguePdf, x: float, y: float, width: float, lines: list[str], rtl: bool
) -> None:
    """cell() rather than text(): only cell() falls back to the script font and shapes."""
    for i, text in enumerate(lines):
        pdf.set_xy(x + PADDING, y + PADDING + i * LINE_HEIGHT)
        pdf.cell(width - 2 * PADDING, LINE_HEIGHT, text, align="R" if rtl else "L")


def build_pdf(
    rows: list[dict],
    notice: str | None = None,
    *,
    columns: list[tuple[str, str]] | None = None,
    title: dict | None = None,
    orientation: str = "L",
    language: str | None = None,
) -> bytes:
    footer_note = (title or {}).get("footer") or "CSCM Tool status code catalogue"
    pdf = _CataloguePdf(orientation, footer_note, language)
    pdf.set_creator("CSCM Tool")
    if not SHAPING_AVAILABLE:  # pragma: no cover
        _log.warning("uharfbuzz is not installed: Indic and Arabic text is drawn without shaping")

    if title:
        _title_page(pdf, title, notice)

    pdf.add_page()
    if notice and not title:
        pdf.set_text_color(180, 0, 0)
        pdf.use(clean(notice), 10)
        pdf.cell(0, 8, clean(notice), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

    if not rows:
        pdf.use("", 10)
        pdf.cell(0, 10, "No records.")
        return bytes(pdf.output())

    if columns is None:
        columns = [(f, label) for f, label in DEFAULT_PDF_FIELDS if f in rows[0]]
    widths = column_widths(columns, rows, pdf.epw)
    bottom = pdf.h - 12

    def header() -> None:
        pdf.set_fill_color(232, 236, 241)
        wrapped = [
            _lines(pdf, w - 2 * PADDING, clean(label))
            for (_f, label), w in zip(columns, widths, strict=True)
        ]
        height = max(len(ls) for ls, _ in wrapped) * LINE_HEIGHT + 2 * PADDING
        x, y = pdf.l_margin, pdf.get_y()
        for (_f, label), w, (ls, rtl) in zip(columns, widths, wrapped, strict=True):
            pdf.rect(x, y, w, height, style="DF")
            pdf.use(clean(label), FONT_SIZE)
            _draw_lines(pdf, x, y, w, ls, rtl)
            x += w
        pdf.set_y(y + height)

    header()
    split_cache: dict[tuple[int, str], tuple[list[str], bool]] = {}

    def split(index: int, text: str) -> tuple[list[str], bool]:
        # Short repeated values (group, category, state, ...) are split once.
        if len(text) > 24:
            return _lines(pdf, widths[index] - 2 * PADDING, text)
        key = (index, text)
        if key not in split_cache:
            split_cache[key] = _lines(pdf, widths[index] - 2 * PADDING, text)
        return split_cache[key]

    for row in rows:
        cells = [split(i, clean(row.get(f))) for i, (f, _l) in enumerate(columns)]
        height = max(len(ls) for ls, _ in cells) * LINE_HEIGHT + 2 * PADDING
        if pdf.get_y() + height > bottom:
            pdf.add_page()
            header()
        x, y = pdf.l_margin, pdf.get_y()
        for i, (w, (ls, rtl)) in enumerate(zip(widths, cells, strict=True)):
            pdf.rect(x, y, w, height)
            pdf.use(clean(row.get(columns[i][0])), FONT_SIZE)
            _draw_lines(pdf, x, y, w, ls or [""], rtl)
            x += w
        pdf.set_y(y + height)

    return bytes(pdf.output())

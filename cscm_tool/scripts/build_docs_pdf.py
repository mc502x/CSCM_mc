"""The documents of a release as PDF, with the version in every file name.

    python scripts/build_docs_pdf.py                    all four, into releases/v<version>/
    python scripts/build_docs_pdf.py --only manual,report
    python scripts/build_docs_pdf.py --out D:/release --with-translations

The four documents (FR-185):

    full      CSCM-Tool_v<version>_Full-Documentation.pdf
              docs/00 .. 25 and DEPLOYMENT-QUICKSTART.md, with the artefacts (the OpenAPI
              contract and the database schema) as appendices
    software  CSCM-Tool_v<version>_Software-Description.pdf   docs/22-software-description.md
    manual    CSCM-Tool_v<version>_User-Manual.pdf            docs/23-user-manual.md
    report    CSCM-Tool_v<version>_Test-Report.pdf            docs/24-test-report.md

The PDFs are made from the Markdown sources in docs/ with fpdf2 and the Noto fonts of the
application (app/static/fonts, SIL Open Font License): no browser, no office program and no network
are needed. `docs/26-translations.md` (every interface text in 19 languages, several MB) is left out
of the full documentation unless --with-translations is given. The symbols a PDF font cannot draw
are written as words: OK, FAIL, yes, ->, <=, flags as their two letters."""

import argparse
import datetime
import hashlib
import math
import re
import subprocess  # nosec B404 - runs `git rev-parse` with fixed arguments to name the commit
import sys
from dataclasses import dataclass, field
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
REPO = APP_DIR.parent
DOCS = REPO / "docs"
sys.path.insert(0, str(APP_DIR))

from fpdf.enums import TextMode, WrapMode  # noqa: E402
from fpdf.fonts import FontFace  # noqa: E402

from app.export import pdf_exporter as px  # noqa: E402
from app.version import VERSION  # noqa: E402

# kind -> (file label, title, what it is)
KINDS = {
    "full": ("Full-Documentation", "Full documentation", "The complete documentation package"),
    "software": ("Software-Description", "Software description", "What the software is and does"),
    "manual": ("User-Manual", "User manual", "How to work with the tool, role by role"),
    "report": ("Test-Report", "Test report", "Results of the automated verification"),
}
BLUE = (0, 46, 109)
GREY = (90, 90, 90)
CODE_BG = (244, 246, 248)
HEAD_FILL = (222, 230, 242)
BODY = 9.0
LINE = 4.4
TOC_LINE = 4.6
MARGIN = 18
CODE_FONT = "Courier"

# symbols the bundled fonts cannot draw -> words (checked in this order)
_WORDS = {
    "✅": "OK",
    "✓": "yes",
    "❌": "FAIL",
    "➖": "-",
    "🧑": "(manual)",
    "→": "->",
    "↔": "<->",
    "←": "<-",
    "⇒": "=>",
    "≤": "<=",
    "≥": ">=",
    "≈": "~",
    "≠": "!=",
    "▶": ">",
    "►": ">",
    "▼": "v",
    "▲": "^",
    "⌊": "[",
    "⌋": "]",
    "✖": "x",
    "◐": "(o)",
    "─": "-",
    "━": "-",
    "│": "|",
    "┃": "|",
    "├": "+",
    "┤": "+",
    "┬": "+",
    "┴": "+",
    "┼": "+",
    "┌": "+",
    "┐": "+",
    "└": "+",
    "┘": "+",
}
_CIRCLES = "🟠🟢🔴🟡🔵🟣⚪⚫🟤"
_LATIN1 = re.compile(r"[^\x00-\xff]")


def plain(text: str) -> str:
    """Words for the symbols no bundled font draws; a pair of regional indicators (a flag) becomes
    its two letters."""
    text = text.replace("\t", "    ")
    for symbol, word in _WORDS.items():
        text = text.replace(symbol, word)
    for circle in _CIRCLES:
        text = text.replace(circle + " ", "").replace(circle, "")
    out = []
    for ch in text:
        code = ord(ch)
        out.append(chr(code - 0x1F1E6 + 65) if 0x1F1E6 <= code <= 0x1F1FF else ch)
    return "".join(out)


def mono(text: str) -> str:
    """Text for the built-in Courier font, which draws Latin-1 only."""
    text = plain(text).replace("\t", "    ")
    return _LATIN1.sub("?", text)


# ---------------------------------------------------------------------------------------- model
@dataclass
class Source:
    path: Path
    title: str
    kind: str = "md"  # md | code
    note: str = ""


@dataclass
class Block:
    type: str  # heading | para | list | table | code | quote | rule
    text: str = ""
    level: int = 0
    rows: list[list[str]] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    ordered: str = ""


_FENCE = re.compile(r"^\s*```")
_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
_RULE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    cells, current, escaped = [], [], False
    for ch in line:
        if escaped:
            current.append(ch if ch == "|" else "\\" + ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    cells.append("".join(current).strip())
    return cells


def parse(markdown: str) -> list[Block]:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[Block] = []
    i = 0

    def starts_block(index: int) -> bool:
        line = lines[index]
        return bool(
            not line.strip()
            or _FENCE.match(line)
            or _HEADING.match(line)
            or _RULE.match(line)
            or line.lstrip().startswith(">")
            or _ITEM.match(line)
            or (
                line.lstrip().startswith("|")
                and index + 1 < len(lines)
                and _SEPARATOR.match(lines[index + 1])
            )
        )

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif _FENCE.match(line):
            i += 1
            body = []
            while i < len(lines) and not _FENCE.match(lines[i]):
                body.append(lines[i])
                i += 1
            i += 1
            blocks.append(Block("code", lines=body))
        elif _HEADING.match(line):
            match = _HEADING.match(line)
            if match is None:
                raise ValueError(line)
            blocks.append(Block("heading", text=match.group(2), level=len(match.group(1))))
            i += 1
        elif _RULE.match(line) and not _ITEM.match(line):
            blocks.append(Block("rule"))
            i += 1
        elif (
            line.lstrip().startswith("|") and i + 1 < len(lines) and _SEPARATOR.match(lines[i + 1])
        ):
            rows = [split_row(line)]
            i += 2
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            blocks.append(Block("table", rows=rows))
        elif line.lstrip().startswith(">"):
            body = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                body.append(lines[i].lstrip()[1:].strip())
                i += 1
            blocks.append(Block("quote", text=" ".join(b for b in body if b)))
        elif _ITEM.match(line):
            match = _ITEM.match(line)
            if match is None:
                raise ValueError(line)
            indent, marker, text = match.groups()
            i += 1
            while (
                i < len(lines)
                and lines[i].strip()
                and not starts_block(i)
                and lines[i].startswith(" ")
            ):
                text += " " + lines[i].strip()
                i += 1
            ordered = marker if marker[0].isdigit() else ""
            blocks.append(
                Block(
                    "list", text=text, level=len(indent.replace("\t", "    ")) // 2, ordered=ordered
                )
            )
        else:
            body = [line.strip()]
            i += 1
            while i < len(lines) and not starts_block(i):
                body.append(lines[i].strip())
                i += 1
            blocks.append(Block("para", text=" ".join(body)))
    return blocks


# ---------------------------------------------------------------------------------------- inline
_TOKENS = re.compile(
    r"(`[^`\n]+`|\*\*.+?\*\*|\[[^\]\n]+\]\([^)\s]+\)|(?<![\w*])\*(?![\s*])[^*\n]+?(?<![\s*])\*(?![\w*])|(?<!\w)_(?![\s_])[^_\n]+?(?<![\s_])_(?!\w))"
)
_UNESCAPE = re.compile(r"\\([\\`*_{}\[\]()#+.!&|<>~-])")
_TAGS = re.compile(r"<br\s*/?>", re.I)
_ANY_TAG = re.compile(r"</?[A-Za-z][^>]*>")


def spans(text: str, bold: bool = False) -> list[tuple[str, dict]]:
    """[(text, {bold, code, link, italic})] of one paragraph; markers are removed."""
    text = _ANY_TAG.sub("", _TAGS.sub(" ", text)).replace("&nbsp;", " ").replace("&amp;", "&")
    out: list[tuple[str, dict]] = []
    position = 0
    for match in _TOKENS.finditer(text):
        if match.start() > position:
            out.append((_UNESCAPE.sub(r"\1", text[position : match.start()]), {"bold": bold}))
        token = match.group(0)
        if token.startswith("`"):
            out.append((token[1:-1], {"bold": bold, "code": True}))
        elif token.startswith("**"):
            out.extend(spans(token[2:-2], True))
        elif token.startswith("["):
            label, target = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token).groups()  # type: ignore[union-attr]
            for piece, flags in spans(label, bold):
                out.append((piece, {**flags, "link": target}))
        else:
            out.append((token[1:-1], {"bold": bold, "italic": True}))
        position = match.end()
    if position < len(text):
        out.append((_UNESCAPE.sub(r"\1", text[position:]), {"bold": bold}))
    return out


def strip_inline(text: str) -> str:
    return "".join(piece for piece, _flags in spans(text)).replace("\\|", "|").strip()


# ---------------------------------------------------------------------------------------- pdf
class DocPdf(px._CataloguePdf):
    """A document PDF: A4 portrait, running text, tables, code, outline and page numbers."""

    def __init__(self, note: str, docs: dict[str, str]):
        super().__init__("P", note)
        self.set_margins(MARGIN, 16, MARGIN)
        self.set_auto_page_break(True, 16)
        self.docs = docs  # file name -> title, for links between the documents
        self.doc_links: dict[str, int] = {}
        self._all_registered = False
        self.set_creator("CSCM Tool scripts/build_docs_pdf.py")

    # fonts ----------------------------------------------------------------------------------
    def fallbacks_on(self) -> None:
        """Every script font as a fallback, for text in a table cell (no shaping there)."""
        if not self._all_registered:
            for key in px.FONT_FILES:
                self._register(key)
            self._all_registered = True
        self.set_fallback_fonts([k for k in px.FONT_FILES if k != px.BASE_FONT])

    def text_font(self, text: str, size: float) -> None:
        self.use(plain(text), size)

    def footer(self) -> None:
        if self.page_no() == 1:
            return
        self.set_y(-10)
        self.set_text_color(*GREY)
        self.set_font(px.BASE_FONT, size=7)
        self.set_fallback_fonts([])
        if getattr(self, "_shaped", None):
            self.set_text_shaping(False)
            self._shaped = False
        self.cell(0, 4, self.footer_note, align="L")
        self.set_x(self.l_margin)
        self.cell(0, 4, f"Page {self.page_no()} of {{nb}}", align="R")
        self.set_text_color(0, 0, 0)

    def link_for(self, name: str) -> int:
        if name not in self.doc_links:
            self.doc_links[name] = self.add_link()
        return self.doc_links[name]

    # inline text ----------------------------------------------------------------------------
    def write_spans(
        self, items: list[tuple[str, dict]], size: float = BODY, height: float = LINE
    ) -> None:
        """Running text. fpdf2's write() breaks a word that does not fit the rest of the line in
        the middle, so the words are placed one by one: a word that does not fit starts a new line.
        """
        for piece, flags in items:
            link = self.resolve(flags.get("link"))
            code = bool(flags.get("code"))
            if code:
                self.set_font(CODE_FONT, size=size * 0.92)
                self.set_fallback_fonts([])
                text = mono(piece)
            else:
                self.text_font(piece, size)
                text = plain(piece)
            colour = BLUE if link else (0, 0, 0)
            self.set_text_color(*colour)
            for word in re.findall(r"\s+|\S+", text):
                at_start = self.get_x() <= self.l_margin + 0.01
                if word.isspace():
                    if at_start:
                        continue
                elif not at_start and self.get_x() + self.get_string_width(word) > (
                    self.w - self.r_margin - 2 * self.c_margin
                ):
                    self.ln(height)
                    self.set_x(self.l_margin)
                if flags.get("bold") and not code:
                    with self.local_context(
                        text_mode=TextMode.FILL_STROKE, line_width=0.12, draw_color=colour
                    ):
                        self.write(height, word, link=link or "")
                else:
                    self.write(height, word, link=link or "")
        self.set_text_color(0, 0, 0)

    def resolve(self, target: str | None):
        if not target:
            return None
        if re.match(r"(https?://|mailto:)", target):
            return target
        name = target.split("#", 1)[0].split("/")[-1]
        return self.link_for(name) if name in self.docs else None

    # blocks ---------------------------------------------------------------------------------
    def heading(self, block: Block, outline: bool) -> None:
        sizes = {1: 18, 2: 14, 3: 11.5, 4: 10, 5: 9.5, 6: 9}
        size = sizes[block.level]
        title = strip_inline(block.text)
        self.ln(3 if block.level > 1 else 0)
        if self.get_y() > self.h - 40:
            self.add_page()
        if outline and block.level <= 3:
            self.start_section(plain(title)[:120], level=block.level - 1, strict=False)
        self.set_text_color(*BLUE)
        self.text_font(title, size)
        with self.local_context(text_mode=TextMode.FILL_STROKE, line_width=0.15, draw_color=BLUE):
            self.multi_cell(0, size * 0.5, plain(title), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        if block.level == 1:
            self.set_draw_color(*BLUE)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

    def paragraph(self, text: str, indent: float = 0.0) -> None:
        self.set_x(self.l_margin + indent)
        old = self.l_margin
        self.set_left_margin(old + indent)
        self.write_spans(spans(text))
        self.set_left_margin(old)
        self.ln(LINE + 1.2)

    def list_item(self, block: Block) -> None:
        indent = 5 + block.level * 5
        old = self.l_margin
        self.set_left_margin(old + indent)
        self.set_x(old + indent)
        marker = (block.ordered or "-").rstrip(".)") + "." if block.ordered else "-"
        self.set_x(old + indent - 4.5)
        self.text_font("x", BODY)
        self.write(LINE, "• " if marker == "-" else marker + " ")
        self.set_x(old + indent)
        self.write_spans(spans(block.text))
        self.set_left_margin(old)
        self.ln(LINE + 0.6)

    def quote(self, text: str) -> None:
        old = self.l_margin
        top = self.get_y()
        self.set_left_margin(old + 5)
        self.set_x(old + 5)
        self.set_text_color(*GREY)
        self.write_spans(spans(text), size=BODY - 0.5)
        self.set_text_color(0, 0, 0)
        self.set_left_margin(old)
        bottom = self.get_y() + LINE
        self.set_draw_color(*BLUE)
        self.set_line_width(0.6)
        if self.get_y() >= top:
            self.line(old + 1.5, top, old + 1.5, bottom)
        self.set_line_width(0.2)
        self.ln(LINE + 1.5)

    def code(self, lines: list[str], size: float = 7.0) -> None:
        self.set_font(CODE_FONT, size=size)
        self.set_fallback_fonts([])
        width = self.w - self.l_margin - self.r_margin - 2
        per_line = max(20, int(width / (size * 0.6 * 0.3528)))
        self.set_fill_color(*CODE_BG)
        self.ln(1)
        for raw in lines or [""]:
            text = mono(raw).rstrip()
            parts = [text[k : k + per_line] for k in range(0, len(text), per_line)] or [""]
            for k, part in enumerate(parts):
                self.set_x(self.l_margin)
                self.cell(
                    width + 2,
                    size * 0.45,
                    ("  " if k else "") + part,
                    fill=True,
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
        self.ln(2.5)

    def data_table(self, rows: list[list[str]]) -> None:
        columns = max(len(r) for r in rows)
        rows = [r + [""] * (columns - len(r)) for r in rows]
        cleaned = [[plain(strip_inline(c)) for c in r] for r in rows]
        width = self.w - self.l_margin - self.r_margin
        size = 7.5 if columns <= 5 else 7.0
        weights, minimum = [], []
        for c in range(columns):
            lengths = sorted(len(r[c]) for r in cleaned)
            average = sum(lengths) / len(lengths)
            high = lengths[int(0.9 * (len(lengths) - 1))]
            longest_word = max((len(w) for r in cleaned for w in r[c].split()), default=1)
            weights.append(max(min(0.5 * average + 0.5 * high, 70.0), min(longest_word, 24.0), 4.0))
            short = max(
                (n for n in lengths if n <= 12), default=0
            )  # a short cell stays on one line
            minimum.append(max(min(longest_word, 18), short) * 0.23 * size + 2.0)
        total = sum(weights)
        widths = [max(width * w / total, m) for w, m in zip(weights, minimum, strict=True)]
        scale = width / sum(widths)
        widths = [w * scale for w in widths]
        self.fallbacks_on()
        self.set_font(px.BASE_FONT, size=size)
        if getattr(self, "_shaped", None):
            self.set_text_shaping(False)
            self._shaped = False
        self.ln(1)
        with self.table(
            col_widths=tuple(widths),
            text_align="LEFT",
            line_height=size * 0.46,
            wrapmode=WrapMode.CHAR if columns >= 6 else WrapMode.WORD,
            headings_style=FontFace(emphasis=None, color=(0, 0, 0), fill_color=HEAD_FILL),
            padding=0.8,
            borders_layout="HORIZONTAL_LINES",
        ) as table:
            for row in cleaned:
                table.row(row)
        self.set_fallback_fonts([])
        self.ln(3)


def render_blocks(pdf: DocPdf, blocks: list[Block], outline: bool = True) -> None:
    for block in blocks:
        if block.type == "heading":
            pdf.heading(block, outline)
        elif block.type == "para":
            pdf.paragraph(block.text)
        elif block.type == "list":
            pdf.list_item(block)
        elif block.type == "quote":
            pdf.quote(block.text)
        elif block.type == "code":
            pdf.code(block.lines)
        elif block.type == "table":
            pdf.data_table(block.rows)
        elif block.type == "rule":
            pdf.set_draw_color(180, 180, 180)
            pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.w - pdf.r_margin, pdf.get_y() + 1)
            pdf.ln(4)


# ---------------------------------------------------------------------------------------- sources
def doc(name: str) -> Source:
    path = DOCS / name
    first = next(
        (ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.startswith("# ")), name
    )
    return Source(path, strip_inline(first[2:]).strip())


def sources_for(kind: str, with_translations: bool) -> list[Source]:
    if kind == "software":
        return [doc("22-software-description.md")]
    if kind == "manual":
        return [doc("23-user-manual.md")]
    if kind == "report":
        return [doc("24-test-report.md")]
    names = sorted(p.name for p in DOCS.glob("[0-9][0-9]-*.md"))
    if not with_translations:
        names = [n for n in names if not n.startswith("26-")]
    found = [doc(n) for n in names]
    quick = REPO / "DEPLOYMENT-QUICKSTART.md"
    if quick.is_file():
        found.append(Source(quick, "Quick deployment guide"))
    artefacts = DOCS / "artifacts"
    for name, title, note in (
        (
            "openapi.yaml",
            "Appendix A - REST API contract (OpenAPI)",
            "The contract of the REST API.",
        ),
        (
            "schema.sql",
            "Appendix B - Database schema (SQL)",
            "The schema every migration builds on.",
        ),
        ("schema-fts5.sql", "Appendix C - Search index (SQL)", "The full-text search index."),
    ):
        if (artefacts / name).is_file():
            found.append(Source(artefacts / name, title, "code", note))
    return found


def git_commit() -> str:
    try:
        out = subprocess.run(  # nosec B603 B607
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def digest_of(sources: list[Source]) -> str:
    h = hashlib.sha256()
    for s in sources:
        h.update(s.path.name.encode())
        h.update(s.path.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------------------- build
def title_page(pdf: DocPdf, kind: str, when: datetime.date, commit: str, digest: str) -> None:
    _label, title, summary = KINDS[kind]
    pdf.add_page()
    pdf.set_y(60)
    pdf.set_text_color(*BLUE)
    pdf.set_font(px.BASE_FONT, size=34)
    with pdf.local_context(text_mode=TextMode.FILL_STROKE, line_width=0.3, draw_color=BLUE):
        pdf.cell(0, 16, "CSCM Tool", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(px.BASE_FONT, size=22)
    pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(px.BASE_FONT, size=12)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 8, summary, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(14)
    facts = [("Version", VERSION), ("Date", when.isoformat())]
    if commit:
        facts.append(("Commit", commit))
    facts.append(("Source digest", digest[:24] + " (SHA-256 of the source files)"))
    for label, value in facts:
        pdf.set_font(px.BASE_FONT, size=10)
        pdf.set_text_color(*GREY)
        pdf.cell(35, 7, label)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(px.BASE_FONT, size=12)
        pdf.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)
    pdf.set_font(px.BASE_FONT, size=8)
    pdf.set_text_color(*GREY)
    note = (
        "Generated from the Markdown documents of the repository by scripts/build_docs_pdf.py; "
        "do not edit by hand. Status symbols are written as words (OK, FAIL, yes), arrows and "
        "comparison signs as ASCII (->, <=, >=). The same version number is shown in the menu of "
        "the application and in /api/v1/health."
    )
    pdf.multi_cell(0, 4, note, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)


def render_toc(pdf: DocPdf, outline: list) -> None:
    pdf.set_font(px.BASE_FONT, size=9)
    for entry in outline:
        if entry.level > 1:
            continue
        indent = 0 if entry.level == 0 else 6
        link = pdf.add_link(page=entry.page_number)
        pdf.set_x(pdf.l_margin + indent)
        pdf.set_text_color(*(BLUE if entry.level == 0 else (0, 0, 0)))
        text = plain(entry.name)
        width = pdf.w - pdf.l_margin - pdf.r_margin - indent - 12
        while text and pdf.get_string_width(text) > width:
            text = text[:-2]
        pdf.cell(width, TOC_LINE, text, link=link)
        pdf.cell(
            12,
            TOC_LINE,
            str(entry.page_number),
            align="R",
            link=link,
            new_x="LMARGIN",
            new_y="NEXT",
        )
    pdf.set_text_color(0, 0, 0)


def build(
    kind: str,
    out_dir: Path,
    with_translations: bool = False,
    when: datetime.date | None = None,
    sources: list[Source] | None = None,
) -> Path:
    """Writes one PDF and returns its path."""
    label, title, _summary = KINDS[kind]
    when = when or datetime.date.today()
    sources = sources if sources is not None else sources_for(kind, with_translations)
    docs = {s.path.name: s.title for s in sources}
    parsed = {
        s.path.name: (parse(s.path.read_text(encoding="utf-8")) if s.kind == "md" else [])
        for s in sources
    }

    pdf = DocPdf(f"CSCM Tool v{VERSION} - {title}", docs)
    pdf.set_title(f"CSCM Tool - {title} - v{VERSION}")
    pdf.set_author("CSCM Tool")
    pdf.set_subject(KINDS[kind][2])
    pdf.set_keywords(f"CSCM Tool, v{VERSION}, {title}")
    title_page(pdf, kind, when, git_commit(), digest_of(sources))

    if kind == "full":
        # the entries of the contents list: the headings of level 1 and 2, the artefact appendices
        entries = 1 + sum(  # + the appendix on the other files
            (
                1
                if s.kind == "code"
                else sum(1 for b in parsed[s.path.name] if b.type == "heading" and b.level <= 2)
            )
            for s in sources
        )
        pdf.add_page()
        pdf.set_font(px.BASE_FONT, size=18)
        pdf.set_text_color(*BLUE)
        pdf.cell(0, 10, "Contents", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)
        first = int((pdf.page_break_trigger - pdf.get_y() + 1e-6) // TOC_LINE)
        other = int((pdf.page_break_trigger - pdf.t_margin + 1e-6) // TOC_LINE)
        pages = 1 + max(0, math.ceil((entries - first) / other))
        pdf.insert_toc_placeholder(render_toc, pages=pages)

    for s in sources:
        pdf.add_page()
        pdf.set_link(pdf.link_for(s.path.name))
        if s.kind == "md":
            render_blocks(pdf, parsed[s.path.name])
        else:
            pdf.start_section(plain(s.title), level=0, strict=False)
            pdf.heading(Block("heading", text=s.title, level=1), False)
            if s.note:
                pdf.paragraph(s.note)
            pdf.code(s.path.read_text(encoding="utf-8").splitlines(), size=6.6)
    if kind == "full":
        pdf.add_page()
        heading = "Appendix D - Other files of the artefact folder"
        pdf.start_section(heading, level=0, strict=False)
        pdf.heading(Block("heading", text=heading, level=1), False)
        pdf.paragraph(
            "These files are part of the repository (docs/artifacts), not reproduced here:"
        )
        for path in sorted((DOCS / "artifacts").iterdir()):
            if path.suffix in (".xlsx", ".json"):
                size = path.stat().st_size // 1024 + 1
                pdf.list_item(Block("list", text=f"`{path.name}` ({size} KB)"))

    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"CSCM-Tool_v{VERSION}_{label}.pdf"
    pdf.output(str(target))
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The documents of a release as PDF.")
    parser.add_argument("--out", type=Path, default=REPO / "releases" / f"v{VERSION}")
    parser.add_argument(
        "--only", default=",".join(KINDS), help="comma separated: " + ", ".join(KINDS)
    )
    parser.add_argument("--with-translations", action="store_true")
    args = parser.parse_args(argv)
    wanted = [k.strip() for k in args.only.split(",") if k.strip()]
    unknown = [k for k in wanted if k not in KINDS]
    if unknown:
        print("Unknown document:", ", ".join(unknown), "- choose from", ", ".join(KINDS))
        return 2
    for kind in wanted:
        target = build(kind, args.out, args.with_translations)
        print(f"{target}  ({target.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

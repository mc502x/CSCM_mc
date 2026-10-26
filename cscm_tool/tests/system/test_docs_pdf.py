"""The documents of a release as PDF with the version in the file name (FR-185,
scripts/build_docs_pdf.py): the Markdown reader, the symbols, the file names and the build of the
four documents (the user manual and a small full documentation for real).

TC-072. Requirements: FR-185, FR-184, NFR-013.
"""

import importlib.util
import re
import sys
from pathlib import Path

import pytest

from app.export import pdf_exporter as px
from app.version import VERSION

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_docs_pdf.py"
DOCS = SCRIPT.parents[2] / "docs"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("build_docs_pdf", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_docs_pdf"] = module
    spec.loader.exec_module(module)
    return module


SAMPLE = """# Title

Intro with **bold**, `code`, _italic_ and a [link](other.md) and [web](https://example.org).

## Section

- first item
  continued here
  - nested item
1. numbered

> a quote
> over two lines

| Name | Value |
|---|---|
| a \| b | `c` |

```
+--+
|  |
```

---
"""


def test_the_reader_finds_every_kind_of_block(tool):
    blocks = tool.parse(SAMPLE)
    assert [b.type for b in blocks] == [
        "heading",
        "para",
        "heading",
        "list",
        "list",
        "list",
        "quote",
        "table",
        "code",
        "rule",
    ]
    assert blocks[3].text == "first item continued here" and blocks[4].level == 1
    assert blocks[5].ordered == "1."
    assert blocks[6].text == "a quote over two lines"
    assert blocks[7].rows == [["Name", "Value"], ["a | b", "`c`"]]
    assert blocks[8].lines == ["+--+", "|  |"]


def test_inline_markup_is_removed_and_kept_as_styles(tool):
    items = tool.spans("A **bold** `code` _it_ [x](y.md) test_a_b and \& done")
    flags = {text: f for text, f in items}
    assert flags["bold"]["bold"] and flags["code"]["code"] and flags["it"]["italic"]
    assert flags["x"]["link"] == "y.md"
    assert "".join(t for t, _ in items) == "A bold code it x test_a_b and & done"


def test_symbols_a_pdf_font_cannot_draw_become_words(tool):
    assert tool.plain("✅ ✓ ❌ → ≤ ≥ 🟠 MEDIUM 🇬🇧") == "OK yes FAIL -> <= >= MEDIUM GB"
    assert tool.mono("┌─┐ → é") == "+-+ -> é"


@pytest.mark.parametrize(
    "name", sorted(p.name for p in DOCS.glob("[0-9][0-9]-*.md") if not p.name.startswith("26-"))
)
def test_every_character_of_the_documents_can_be_drawn(tool, name):
    """A new symbol in a document must be given a word in `_WORDS`, or it prints as a gap."""
    text = tool.plain((DOCS / name).read_text(encoding="utf-8"))
    covered = px._covered()
    missing = sorted({c for c in text if ord(c) > 127 and ord(c) not in covered})
    assert missing == [], "".join(missing)


def test_a_document_is_built_with_the_version_in_its_name(tool, tmp_path):
    small = tmp_path / "01-small.md"
    small.write_text(SAMPLE, encoding="utf-8")
    other = tmp_path / "other.md"
    other.write_text("# Other\n\nSee [small](01-small.md).\n", encoding="utf-8")
    sources = [tool.Source(small, "Small"), tool.Source(other, "Other")]
    path = tool.build("software", tmp_path / "out", sources=sources)
    assert path.name == f"CSCM-Tool_v{VERSION}_Software-Description.pdf"
    data = path.read_bytes()
    assert data.startswith(b"%PDF") and f"v{VERSION}".encode() in data
    assert len(re.findall(rb"/Type /Page\b", data)) >= 3  # title page and the documents


def test_the_full_documentation_has_a_contents_list_and_the_artefacts(tool, tmp_path):
    first = tmp_path / "00-first.md"
    first.write_text(
        "# First\n\n" + "\n\n".join(f"## Part {i}\n\ntext" for i in range(80)), encoding="utf-8"
    )
    sql = tmp_path / "schema.sql"
    sql.write_text("CREATE TABLE t (id INTEGER);\n" * 30, encoding="utf-8")
    sources = [
        tool.Source(first, "First"),
        tool.Source(sql, "Appendix B - Schema", "code", "The schema."),
    ]
    path = tool.build("full", tmp_path / "out", sources=sources)
    assert path.name == f"CSCM-Tool_v{VERSION}_Full-Documentation.pdf"
    data = path.read_bytes()
    assert b"/Outlines" in data and len(re.findall(rb"/Type /Page\b", data)) >= 6


def test_the_four_documents_have_their_file_names(tool):
    names = {k: f"CSCM-Tool_v{VERSION}_{v[0]}.pdf" for k, v in tool.KINDS.items()}
    assert names == {
        "full": f"CSCM-Tool_v{VERSION}_Full-Documentation.pdf",
        "software": f"CSCM-Tool_v{VERSION}_Software-Description.pdf",
        "manual": f"CSCM-Tool_v{VERSION}_User-Manual.pdf",
        "report": f"CSCM-Tool_v{VERSION}_Test-Report.pdf",
    }
    assert tool.sources_for("software", False)[0].path.name == "22-software-description.md"
    full = [s.path.name for s in tool.sources_for("full", False)]
    assert "26-translations.md" not in full and "openapi.yaml" in full and "schema.sql" in full
    assert "26-translations.md" in [s.path.name for s in tool.sources_for("full", True)]


def test_the_user_manual_is_built_from_the_real_document(tool, tmp_path):
    path = tool.build("manual", tmp_path)
    assert path.name == f"CSCM-Tool_v{VERSION}_User-Manual.pdf"
    assert path.stat().st_size > 50_000


def test_an_unknown_document_is_refused(tool, capsys):
    assert tool.main(["--only", "bogus"]) == 2
    assert "Unknown document" in capsys.readouterr().out

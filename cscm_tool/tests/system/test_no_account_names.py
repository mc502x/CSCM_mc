"""The documents and the guide do not name the Git account or the repository (a decision of the
owner): the address of the repository is given by the Software Owner or the Administrator.

Requirements: NFR-013.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
# written in pieces so that this file does not contain what it looks for
FORBIDDEN = ("mc" + "502x", "CSCM" + "_mc", "github.com/" + "mc")


def _texts():
    for pattern in (
        "docs/*.md",
        "*.md",
        "cscm_tool/*.md",
        "cscm_tool/scripts/**/*.py",
        "cscm_tool/deploy/**/*",
    ):
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file() and path.suffix in (
                ".md",
                ".py",
                ".sh",
                ".ps1",
                ".conf",
                ".service",
                ".timer",
            ):
                yield path


def test_no_document_or_script_names_the_account_or_the_repository():
    found = []
    for path in _texts():
        text = path.read_text(encoding="utf-8", errors="ignore")
        found += [f"{path.relative_to(ROOT)}: {word}" for word in FORBIDDEN if word in text]
    assert found == []


def test_the_guide_says_who_to_ask_for_the_repository():
    guide = (ROOT / "DEPLOYMENT-QUICKSTART.md").read_text(encoding="utf-8")
    assert "Who to ask" in guide and "Software Owner" in guide and "Administrator" in guide
    assert "<address of the repository>" in guide

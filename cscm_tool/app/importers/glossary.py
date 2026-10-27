# ruff: noqa: E501  (docstring lines)
"""Does the English title of the mapping say what the German name in the program says?

The programs carry the German name (`StCd: 3000, 'Umrichter nicht bereit'`); the mapping carries the
English title. `title_glossary.csv` lists the technical terms that occur in the names with the English
words and abbreviations that stand for them. For every term found in the German name, one of its English
renderings has to occur in the title; otherwise the import warns. It is a check for a person to look at,
never a translation: nothing is changed and nothing is blocked."""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

GLOSSARY = Path(__file__).resolve().parent / "data" / "title_glossary.csv"


@lru_cache(maxsize=1)
def terms() -> tuple[tuple[str, tuple[str, ...]], ...]:
    out = []
    with GLOSSARY.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            english = tuple(w.strip().lower() for w in row["english"].split(",") if w.strip())
            out.append((row["german"].strip().lower(), english))
    return tuple(out)


def _found(term: str, name: str) -> bool:
    """A short term (up to three letters) must start a word; a longer one may sit inside a compound
    word (Hydrauliköl, Netzspannung)."""
    if len(term) <= 3:
        return re.search(r"(?<![^\W\d_])" + re.escape(term), name) is not None
    return term in name


def check(german_name: str, english_title: str) -> list[str]:
    """One message per term of the German name whose English rendering is missing from the title."""
    name = (german_name or "").lower()
    title = (english_title or "").lower()
    if not name or not title:
        return []
    messages = []
    for term, english in terms():
        if _found(term, name) and not any(word in title for word in english):
            messages.append(
                f"the program name has '{term}'; the title would be expected to have "
                + " or ".join(f"'{w}'" for w in english)
            )
    return messages

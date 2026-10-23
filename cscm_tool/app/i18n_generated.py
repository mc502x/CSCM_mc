"""The translations that are kept as data files (app/translations/<language>.json).

The first catalogues were written by hand as Python dictionaries (app/i18n_de.py, app/i18n_extra.py,
...). The complete catalogue of every language is a JSON file per language: {English text:
translation}, written once for the whole inventory (docs/26-translations.md, FR-167) and corrected
through the translation review of the application. A hand-written entry wins over a file entry, an
accepted proposal (translation_override) wins over both."""

import json
from functools import cache
from pathlib import Path

DIRECTORY = Path(__file__).resolve().parent / "translations"


@cache
def generated() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    if DIRECTORY.is_dir():
        for path in sorted(DIRECTORY.glob("*.json")):
            out[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    return out


def merged(language: str, hand_written: dict[str, str]) -> dict[str, str]:
    """The data file of the language with the hand-written entries on top."""
    return {**generated().get(language, {}), **hand_written}

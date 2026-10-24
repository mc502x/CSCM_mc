# ruff: noqa: E501  (docstring lines)
"""The confidence check of the translations (docs/26-translations.md §8c).

    python scripts/translation_precheck.py --check            # what changed since the last check?
    python scripts/translation_precheck.py --baseline FILE    # record a full pre-check
    python scripts/translation_precheck.py --delta FILE       # record verdicts for the changed strings
    python scripts/translation_precheck.py --template         # print a delta file for the changes

`--check` exits 1 while a string or a term of the nomenclature changed and has not been checked;
`ci.py` and a test use it, so no change of the text or the nomenclature goes through unchecked.
A delta file is `{"checked_by": "...", "nomenclature_checked": true, "checked": {"fr": [{"english":
"...", "kind": "OK|A|E", "note": "..."}]}}`: one verdict for every changed string (OK = fine,
A = awkward or inconsistent, E = wrong meaning). Reading the strings is the point; the script only
checks that none was skipped."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import translation_precheck as pc  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--template", action="store_true")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--delta", type=Path)
    args = parser.parse_args()

    if args.baseline:
        result = pc.record(baseline=json.loads(args.baseline.read_text(encoding="utf-8")))
        for code, row in result["languages"].items():
            print(f"{code}: {row['confidence']}%")
        return 0
    if args.delta:
        result = pc.record(delta=json.loads(args.delta.read_text(encoding="utf-8")))
        for code, row in result["languages"].items():
            print(f"{code}: {row['confidence']}%")
        return 0

    found = pc.changes()
    if args.template:
        print(
            json.dumps(
                {
                    "checked_by": "",
                    "nomenclature_checked": found["glossary_changed"],
                    "checked": {
                        lang: [{"english": e, "kind": "", "note": ""} for e in strings]
                        for lang, strings in found["strings"].items()
                    },
                },
                ensure_ascii=False,
                indent=1,
            )
        )
        return 0

    total = sum(len(v) for v in found["strings"].values())
    if not total and not found["glossary_changed"]:
        print("The confidence check is current.")
        return 0
    if found["glossary_changed"]:
        print("The nomenclature changed since the last check.")
    for language, strings in found["strings"].items():
        print(f"{language}: {len(strings)} changed strings, e.g. {strings[0]!r}")
    print(
        "Read the changed strings, then run: python scripts/translation_precheck.py --template "
        "> delta.json, fill in a verdict for each, and --delta delta.json."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

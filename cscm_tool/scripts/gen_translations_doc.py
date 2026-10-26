"""The translation catalogue of the web application, as a document and as sheets for native speakers.

    python scripts/gen_translations_doc.py --write            # regenerate the catalogue in docs/26-translations.md
    python scripts/gen_translations_doc.py --check            # exit 1 when the file is out of date
    python scripts/gen_translations_doc.py --xlsx ar -o out/  # the review sheet of one language
    python scripts/gen_translations_doc.py --xlsx all -o out/ # one sheet per language

The catalogues are the Python files app/i18n_de.py, app/i18n_extra.py, app/i18n_ar.py, app/i18n_in.py
and app/i18n_eu.py; every string a template wraps in `_()` is the English source. The data and the
sheet builder are in app/translation_catalogue.py, shared with the application's translation review
section, where native speakers check the translations in the browser (Translations in the sidebar);
the sheets here are the offline way to do the same and can be uploaded there.

The generated part of docs/26-translations.md sits between two markers, so the concept text around
it is hand-written and the tables can never drift from the code (tests/system/test_translations_doc.py).
The document describes what the code ships; proposals accepted in the application are overrides in the
database and are not in it until they are moved into the catalogue files."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from app import translation_precheck as precheck  # noqa: E402
from app.translation_catalogue import (  # noqa: E402,F401  (re-exported for the tests)
    CHECKLIST,
    ENGLISH_NAMES,
    VERDICTS,
    build_sheet,
    catalogue,
    fingerprint,
    is_rtl,
    label,
    languages,
    screens,
    string_id,
)

DOC = APP_DIR.parent / "docs" / "26-translations.md"
START = "<!-- translations:start -->"
END = "<!-- translations:end -->"


def _screens() -> dict[str, list[str]]:
    return screens()


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def render() -> str:
    known = screens()
    cat = catalogue()
    total = len(known)
    out: list[str] = []
    out.append(
        f"The interface has **{total} strings** (every text a template wraps in `_()`, the role names and the "
        "help texts). English is the source; the other languages are listed below. A string without a "
        "translation is shown in English.\n"
    )
    out.append("### 9.1 Coverage\n")
    checks = precheck.load().get("languages", {})
    out.append(
        "| Language | Code | Direction | Translated | Share | Pre-check confidence | Fingerprint |"
    )
    out.append("|---|---|---|---|---|---|---|")
    for code in languages():
        if code == "en":
            out.append(f"| {_cell(label(code))} | `en` | ltr | source | — | — | — |")
            continue
        t = cat[code]
        check = checks.get(code)
        confidence = precheck.badge(check["confidence"]) if check else "not checked"
        out.append(
            f"| {_cell(label(code))} ({ENGLISH_NAMES[code]}) | `{code}` | {'rtl' if is_rtl(code) else 'ltr'} "
            f"| {len(t)} | {100 * len(t) // total} % | {confidence} | `{fingerprint(t)}` |"
        )
    out.append("")
    out.append(
        "The pre-check confidence is the estimate of section 8c - the share of strings a native speaker is "
        "expected to accept unchanged, by an AI checker and not by a native speaker; red is 50 % or less, "
        "green above 95 %.\n"
    )
    out.append(
        "The fingerprint is a short hash of the language's catalogue as shipped in the code (string ids and "
        "translations). Whether a language has been reviewed, by whom and when, and which proposals were "
        "accepted since, is kept in the application (Translations in the sidebar), not in this file.\n"
    )

    if checks:
        out.append("### 9.1a Pre-check: findings per language\n")
        out.append(
            "| Language | Wrong meaning | Awkward or inconsistent | Terms differing from the nomenclature "
            "| Haircut (points) | Confidence |"
        )
        out.append("|---|---|---|---|---|---|")
        for code in languages():
            check = checks.get(code)
            if code == "en" or not check:
                continue
            out.append(
                f"| {_cell(label(code))} | {check['errors']} | {check['awkward']} "
                f"| {check['mechanical']['glossary_mismatches']} | {check['haircut']:g} "
                f"| {precheck.badge(check['confidence'])} |"
            )
        out.append("")
        out.append(
            "The wrong and awkward counts are findings in the sample of "
            f"{next(iter(checks.values()))['sample_size']} strings, the same strings in every language. The "
            "strings that were flagged, for the native speaker to look at first:\n"
        )
        out.append("| Language | Kind | English | Translation | Finding |")
        out.append("|---|---|---|---|---|")
        for code in languages():
            check = checks.get(code)
            if code == "en" or not check:
                continue
            for finding in sorted(
                check["findings"], key=lambda f: (f["kind"], f["english"].lower())
            ):
                kind = "wrong" if finding["kind"] == "E" else "awkward"
                out.append(
                    f"| `{code}` | {kind} | {_cell(finding['english'])} "
                    f"| {_cell(finding['translation'])} | {_cell(finding['note'])} |"
                )
        out.append("")

    for number, code in enumerate((c for c in languages() if c != "en"), start=2):
        t = cat[code]
        rows = defaultdict(list)
        for english, translated in t.items():
            primary = known.get(english, ["help and messages"])
            rows[primary[0]].append((english, translated, primary))
        out.append(f"### 9.{number} {label(code)} — {ENGLISH_NAMES[code]}\n")
        out.append(
            f"{len(t)} of {total} strings translated; direction "
            f"{'right to left' if is_rtl(code) else 'left to right'}.\n"
        )
        out.append("| Id | Screens | English | Translation |")
        out.append("|---|---|---|---|")
        for screen in sorted(rows):
            for english, translated, used in sorted(rows[screen], key=lambda r: r[0].lower()):
                out.append(
                    f"| `{string_id(english)}` | {_cell(', '.join(used[:3]))} | {_cell(english)} | {_cell(translated)} |"
                )
        out.append("")

    out.append(f"### 9.{len(languages()) + 1} Strings with the screens that show them\n")
    out.append(
        "Every string of the interface with the templates that use it. A native speaker adding a missing "
        "translation finds the context here.\n"
    )
    out.append("| Id | English | Screens | Languages |")
    out.append("|---|---|---|---|")
    for english in sorted(known, key=str.lower):
        have = [c for c in languages() if c != "en" and english in cat[c]]
        out.append(
            f"| `{string_id(english)}` | {_cell(english)} | {_cell(', '.join(known[english][:4]))} "
            f"| {len(have)} of {len(languages()) - 1} |"
        )
    return "\n".join(out) + "\n"


def write_document() -> bool:
    text = DOC.read_text(encoding="utf-8")
    head, rest = text.split(START, 1)
    _old, tail = rest.split(END, 1)
    new = head + START + "\n\n" + render() + "\n" + END + tail
    if new == text:
        return False
    DOC.write_text(new, encoding="utf-8")
    return True


def is_current() -> bool:
    text = DOC.read_text(encoding="utf-8")
    block = text.split(START, 1)[1].split(END, 1)[0]
    return block.strip() == render().strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--write", action="store_true", help="regenerate the catalogue in docs/26-translations.md"
    )
    parser.add_argument(
        "--check", action="store_true", help="exit 1 when docs/26-translations.md is out of date"
    )
    parser.add_argument(
        "--xlsx", metavar="LANG", help="write the review sheet of a language code, or 'all'"
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("."), help="directory for the sheets"
    )
    args = parser.parse_args(argv)
    if args.xlsx:
        codes = [c for c in languages() if c != "en"] if args.xlsx == "all" else [args.xlsx]
        args.output.mkdir(parents=True, exist_ok=True)
        for code in codes:
            if code not in languages() or code == "en":
                print(f"unknown or source language: {code}", file=sys.stderr)
                return 2
            path = args.output / f"translation-review-{code}.xlsx"
            path.write_bytes(build_sheet(code))
            print(f"{path}")
    if args.write:
        print(
            "updated docs/26-translations.md"
            if write_document()
            else "docs/26-translations.md is current"
        )
    if args.check and not is_current():
        print(
            "docs/26-translations.md is out of date: run python scripts/gen_translations_doc.py --write",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

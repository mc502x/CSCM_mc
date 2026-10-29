# ruff: noqa: E501  (docstring lines)
"""The confidence check of the translations (docs/26-translations.md §8c, FR-176).

Before a native speaker has looked at a language, a *pre-check* says how far the text can be trusted:
every string is checked mechanically (placeholders, untranslated text, the nomenclature) and a sample
of 160 strings is read for meaning, register and consistency. Findings are weighted - a wrong meaning
counts 1, an awkward or inconsistent wording 0.5 - the rate is carried over to the whole catalogue and
reduced by what the checker cannot see in that language (the *haircut*) and by the terms of the
nomenclature that the interface renders differently. The result is a percentage per language: the
share of strings a native speaker is expected to accept unchanged. It is an estimate, not a review;
the beta mark and the review of the native speakers (FR-170, FR-172) are unaffected.

Whenever a string or a term of the nomenclature changes, the check must be done again for what
changed: `scripts/translation_precheck.py --check` lists the changed strings, `--record` takes a verdict
for each of them and updates the percentage, and a test fails while the record is out of date.

The data are `app/translations/precheck.json` (the result, read by the application) and
`app/translations/precheck_state.json` (a short hash of every string at the last check)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from flask import g, has_request_context

from app.terminology_seed import terms
from app.translation_catalogue import catalogue, screens, string_id

DIRECTORY = Path(__file__).resolve().parent / "translations"
RESULT = DIRECTORY / "precheck.json"
STATE = DIRECTORY / "precheck_state.json"
WEIGHT = {"OK": 0.0, "A": 0.5, "E": 1.0}
UNTRANSLATED = {"d", "WNEW", "TCC"}
_PLACEHOLDER = re.compile(r"%\(\w+\)[sd]")

# the colour intervals of the overview: red up to 50 %, green above 95 %, steps of 5 points between
BUCKETS = (50, 55, 60, 65, 70, 75, 80, 85, 90, 95)


COLOURS = (
    "#e5484d",
    "#ec6a4a",
    "#f08a47",
    "#f4a947",
    "#f6c445",
    "#f3dc4a",
    "#d9e050",
    "#bcd957",
    "#9ccf5c",
    "#7fc561",
    "#4fb26b",
)  # fmt: skip - the same steps as .conf-b0 ... .conf-b10 in app.css


def badge(confidence: float) -> str:
    """The percentage on its colour, for the Markdown documents."""
    colour = COLOURS[bucket(confidence)]
    text = "#ffffff" if bucket(confidence) in (0, 10) else "#1b1b1b"
    return (
        f'<span style="background:{colour};color:{text};padding:1px 8px;border-radius:9px">'
        f"<b>{round(confidence)} %</b></span>"
    )


def bucket(confidence: float) -> int:
    """0 (red, 50 % or less) ... 10 (green, above 95 %)."""
    return sum(1 for edge in BUCKETS if confidence > edge)


def digest(english: str, translation: str) -> str:
    return hashlib.sha1(  # nosec B324 - not a secret
        f"{english}\t{translation}".encode()
    ).hexdigest()[:6]


def glossary_hash() -> str:
    rows = sorted(
        (t["code"], t["english"], json.dumps(t["translations"], sort_keys=True, ensure_ascii=False))
        for t in terms()
    )
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False).encode()).hexdigest()[:12]


def state_now() -> dict[str, dict[str, str]]:
    """The digest of every string of every language as shipped. The Translations page asked for it
    once per language (eighteen times, seconds each); inside one request it is computed once."""
    if has_request_context() and "state_now" in g:
        return g.state_now
    known = screens()
    out: dict[str, dict[str, str]] = {}
    for language, table in catalogue().items():
        out[language] = {string_id(e): digest(e, table[e]) for e in sorted(known) if e in table}
    if has_request_context():
        g.state_now = out
    return out


def load() -> dict[str, Any]:
    try:
        return json.loads(RESULT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def confidence_of(language: str) -> float | None:
    entry = load().get("languages", {}).get(language)
    return None if entry is None else float(entry["confidence"])


def _load_state() -> dict[str, Any]:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# ---------------------------------------------------------------------------- mechanical checks
def mechanical(language: str) -> dict[str, Any]:
    """Checks that need no reader: every string, one language."""
    known = sorted(screens())
    table = catalogue()[language]
    glossary = {
        t["english"].lower(): t["translations"][language]
        for t in terms()
        if not t["keep_english"] and language in t["translations"]
    }
    missing, placeholders, identical, glossary_mismatch = [], [], [], []
    for english in known:
        translated = table.get(english)
        if translated is None:
            if english not in UNTRANSLATED:
                missing.append(english)
            continue
        if sorted(_PLACEHOLDER.findall(english)) != sorted(_PLACEHOLDER.findall(translated)):
            placeholders.append(english)
        if translated == english and english not in UNTRANSLATED and len(english) > 25:
            identical.append(english)
        wanted = glossary.get(english.rstrip(".:… ").lower())
        if wanted and translated.rstrip(".:… ").lower() != wanted.lower():
            glossary_mismatch.append(english)
    return {
        "strings": len(table),
        "missing": len(missing),
        "placeholders": len(placeholders),
        "identical": len(identical),
        "glossary_mismatches": len(glossary_mismatch),
    }


# ---------------------------------------------------------------------------- the changes
def changes() -> dict[str, Any]:
    """What changed since the last record: {language: [english, ...]}, and the glossary flag."""
    state = _load_state()
    now = state_now()
    known = {string_id(e): e for e in screens()}
    changed: dict[str, list[str]] = {}
    for language, hashes in now.items():
        before = state.get(language, {})
        moved = sorted(known[sid] for sid, h in hashes.items() if before.get(sid) != h)
        if moved:
            changed[language] = moved
    return {
        "strings": changed,
        "glossary_changed": state.get("_glossary") != glossary_hash(),
    }


def is_current() -> bool:
    found = changes()
    return not found["strings"] and not found["glossary_changed"]


# ---------------------------------------------------------------------------- the record
def _confidence(
    language: str,
    strings: int,
    rate: float,
    haircut: float,
    glossary_mismatches: int,
    checked: dict[str, dict[str, Any]],
    now: dict[str, str],
) -> tuple[float, float]:
    """(confidence %, accuracy %) from the sample rate, the strings read one by one and the haircut."""
    live = {sid: c for sid, c in checked.items() if now.get(sid) == c["hash"]}
    mass = rate * max(strings - len(live), 0) + sum(WEIGHT[c["kind"]] for c in live.values())
    accuracy = 100.0 * (1 - mass / strings) if strings else 0.0
    penalty = 100.0 * 0.5 * glossary_mismatches / strings if strings else 0.0
    return round(max(accuracy - haircut - penalty, 0.0), 1), round(accuracy, 1)


def record(baseline: dict[str, Any] | None = None, delta: dict[str, Any] | None = None) -> dict:
    """Writes the result and the state. `baseline` is a full pre-check (findings of a read of the
    sample, haircut per language); `delta` carries a verdict for every string that changed."""
    if (baseline is None) == (delta is None):
        raise ValueError("Give either a baseline or a delta.")
    previous = load()
    changed = changes()
    now = state_now()
    known = {e: string_id(e) for e in screens()}
    table = catalogue()
    languages: dict[str, Any] = {}
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")

    if baseline is not None:
        sample = int(baseline["sample_size"])
        for language, findings in baseline["findings"].items():
            errors = sum(1 for f in findings if f["kind"] == "E")
            awkward = sum(1 for f in findings if f["kind"] == "A")
            rate = (errors + 0.5 * awkward) / sample
            mech = mechanical(language)
            haircut = float(baseline["haircut"][language])
            confidence, accuracy = _confidence(
                language, mech["strings"], rate, haircut, mech["glossary_mismatches"], {}, {}
            )
            languages[language] = {
                "confidence": confidence,
                "accuracy": accuracy,
                "haircut": haircut,
                "sample_size": sample,
                "sample_rate": round(rate, 5),
                "errors": errors,
                "awkward": awkward,
                "mechanical": mech,
                "findings": [
                    {
                        **f,
                        "string_id": known.get(f["english"], ""),
                        "hash": digest(f["english"], table[language].get(f["english"], "")),
                    }
                    for f in findings
                ],
                "checked": {},
                "checked_at": baseline.get("date", stamp),
            }
        note = f"baseline: sample of {sample} strings per language"
        by = baseline.get("checked_by", "AI pre-check (Claude)")
    elif delta is not None:
        if changed["glossary_changed"] and not delta.get("nomenclature_checked"):
            raise ValueError(
                "The nomenclature changed: check the interface against the new terms and set "
                "'nomenclature_checked' to true."
            )
        verdicts = delta.get("checked", {})
        for language, english_list in changed["strings"].items():
            given = {v["english"]: v for v in verdicts.get(language, [])}
            absent = [e for e in english_list if e not in given]
            if absent:
                raise ValueError(
                    f"{language}: {len(absent)} changed strings have no verdict, e.g. {absent[0]!r}."
                )
            for v in given.values():
                if v.get("kind") not in WEIGHT:
                    raise ValueError(
                        f"{language}: the verdict of {v['english']!r} must be OK, A or E."
                    )
        for language, old in previous.get("languages", {}).items():
            mech = mechanical(language)
            checked = dict(old.get("checked", {}))
            for v in verdicts.get(language, []):
                sid = known[v["english"]]
                checked[sid] = {
                    "english": v["english"],
                    "hash": digest(v["english"], table[language][v["english"]]),
                    "kind": v["kind"],
                    "note": v.get("note", ""),
                }
            live = {sid: c for sid, c in checked.items() if now[language].get(sid) == c["hash"]}
            findings = [
                f
                for f in old.get("findings", [])
                if now[language].get(f.get("string_id", "")) == f.get("hash")
            ]
            confidence, accuracy = _confidence(
                language,
                mech["strings"],
                old["sample_rate"],
                old["haircut"],
                mech["glossary_mismatches"],
                live,
                now[language],
            )
            languages[language] = {
                **old,
                "confidence": confidence,
                "accuracy": accuracy,
                "mechanical": mech,
                "findings": findings,
                "checked": live,
                "checked_at": stamp,
            }
        count = sum(len(v) for v in changed["strings"].values())
        note = f"delta: {count} changed strings read one by one"
        by = delta.get("checked_by", "unnamed")

    else:  # pragma: no cover - guarded at the top
        raise ValueError("Give either a baseline or a delta.")

    history = list(previous.get("history", []))
    history.append({"date": stamp, "by": by, "note": note})
    result = {
        "date": stamp,
        "method": (
            "Every string is checked mechanically; a sample of 160 strings per language is read for "
            "meaning, register and consistency (a wrong meaning counts 1, an awkward or inconsistent "
            "wording 0.5); the rate is carried over to the whole catalogue, reduced by the haircut "
            "(what the checker cannot see in that language) and by the terms the interface renders "
            "differently from the nomenclature. A string that changed later is read one by one."
        ),
        "history": history,
        "languages": languages,
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    state: dict[str, Any] = dict(now)
    state["_glossary"] = glossary_hash()
    STATE.write_text(json.dumps(state, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return result

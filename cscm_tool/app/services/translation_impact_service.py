# ruff: noqa: E501  (the sentences of the notices)
"""Language impact of a change of the vocabulary (docs/26-translations.md §8d, FR-178).

A new or changed term, a translation of a term that is approved, or new interface text shipped with a
version, touches every language: a term may have no translation yet, an interface string may use
another word than the nomenclature, a reviewed language gets strings that no native speaker has
approved. The StCd Owner (and the reviewers assigned to an affected language) is told **in the
application**, with the languages and the numbers, so nothing changes silently:

* `notify_term_change` - called when a term is created or changed or when a translation of a term is
  approved (Terminology section); checks the term against every language at once;
* `notify_catalogue_changes` - called when the server starts and by `flask translation-impact` after a
  deployment; compares the shipped text and nomenclature with the last confidence check
  (`app/translation_precheck.py`) and tells what changed per language.

Both are best effort: a failing notice never undoes the change it reports. A notice is sent once per
change and person (the dedupe key)."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from flask import current_app

from app import translation_precheck as precheck
from app.extensions import db
from app.models.translation import LanguageReviewer
from app.services.notification_service import NotificationService, _active_users
from app.services.terminology_service import TerminologyService
from app.services.translation_review_service import TranslationReviewService
from app.translation_catalogue import (
    effective,
    reviewable_languages,
    screens,
)

KIND = "TRANSLATION_IMPACT"
LINK_TERMS = "/terminology"
LINK_TRANSLATIONS = "/translations"
SHOWN = 6  # languages named in a notice; the rest is counted


def _owners() -> list:
    return _active_users("STCD_OWNER")


def _reviewers_of(languages: set[str]) -> list[int]:
    if not languages:
        return []
    rows = db.session.query(LanguageReviewer.user_id).filter(
        LanguageReviewer.language_code.in_(languages)
    )
    return sorted({r[0] for r in rows})


def _pattern(term_english: str) -> re.Pattern[str]:
    return re.compile(r"(?<![A-Za-z])" + re.escape(term_english) + r"(?![A-Za-z])")


def _summary(rows: list[dict[str, Any]], key: str) -> str:
    shown = ", ".join(f"{r['code']} ({r[key]})" for r in rows[:SHOWN])
    more = len(rows) - SHOWN
    return shown + (f" and {more} more" if more > 0 else "")


class TranslationImpactService:
    @staticmethod
    def term_impact(term) -> list[dict[str, Any]]:
        """One row per language: the state of the term there and how many interface strings that
        contain the term do not use its approved translation."""
        reviewed = TranslationReviewService.reviewed_languages()
        pattern = _pattern(term.english)
        containing = [s for s in screens() if pattern.search(s)]
        rows = []
        for language in reviewable_languages():
            translation = TerminologyService.translations(language).get(term.id)
            if term.keep_english:
                state, differing = "KEEP", 0
            elif translation is None:
                state, differing = "MISSING", 0
            else:
                state = translation.status
                table = effective(language)
                wanted = translation.text.casefold()
                differing = sum(
                    1
                    for s in containing
                    if s in table and len(term.english) >= 4 and wanted not in table[s].casefold()
                )
            rows.append(
                {
                    "code": language,
                    "state": state,
                    "strings": len(containing),
                    "differing": differing,
                    "reviewed": language in reviewed,
                }
            )
        return rows

    @staticmethod
    def _needs_attention(row: dict[str, Any]) -> bool:
        return row["state"] in ("MISSING", "DRAFT") or row["differing"] > 0

    @staticmethod
    def notify_term_change(term, action: str, language: str | None = None) -> int:
        """Tells the StCd Owner which languages a change of `term` touches. Returns the notices sent."""
        try:
            impact = TranslationImpactService.term_impact(term)
            if language is not None:  # a translation of one language was approved
                impact = [r for r in impact if r["code"] == language]
            affected = [r for r in impact if TranslationImpactService._needs_attention(r)]
            if term.keep_english:
                message = (
                    f"Terminology {action}: '{term.english}' stays in English in every language; "
                    "no translation is affected."
                )
            elif language is not None:
                row = impact[0]
                message = (
                    f"Terminology {action}: '{term.english}' in {language}. "
                    f"{row['strings']} interface strings contain the term"
                    + (
                        f"; {row['differing']} do not use the approved translation"
                        + (" and need a follow-up review." if row["reviewed"] else ".")
                        if row["differing"]
                        else "; all of them use it."
                    )
                )
            elif not affected:
                message = (
                    f"Terminology {action}: '{term.english}'. All {len(impact)} languages have an "
                    "approved translation that the interface uses."
                )
            else:
                missing = [r for r in affected if r["state"] in ("MISSING", "DRAFT")]
                differing = [r for r in affected if r["differing"]]
                parts = []
                if missing:
                    parts.append(f"no approved translation in {_summary(missing, 'state')}")
                if differing:
                    parts.append(
                        f"interface strings that do not use the term in {_summary(differing, 'differing')}"
                    )
                reviewed = [r["code"] for r in affected if r["reviewed"]]
                message = (
                    f"Terminology {action}: '{term.english}'. {len(affected)} of {len(impact)} "
                    f"languages need attention: {'; '.join(parts)}."
                )
                if reviewed:
                    message += (
                        f" Reviewed languages affected: {', '.join(reviewed[:SHOWN])}; their changed "
                        "strings need a follow-up review."
                    )
            recipients = {u.id for u in _owners()} | set(
                _reviewers_of({r["code"] for r in (impact if language else affected)})
            )
            stamp = f"{term.id}:{action}:{language or ''}:{term.updated_at}"
            sent = 0
            for user_id in sorted(recipients):
                notice = NotificationService.notify(
                    user_id,
                    KIND,
                    message,
                    link=LINK_TERMS,
                    dedupe_key=f"term-impact:{stamp}:{user_id}",
                )
                sent += 1 if notice else 0
            db.session.commit()
            return sent
        except Exception:  # noqa: BLE001 - a notice never undoes the change it reports
            db.session.rollback()
            current_app.logger.exception(
                "translation impact of term %s could not be reported", term
            )
            return 0

    @staticmethod
    def catalogue_impact() -> dict[str, Any]:
        """What changed in the shipped text or nomenclature since the last confidence check, per
        language, with the strings that await approval (FR-176) and the review state."""
        found = precheck.changes()
        reviewed = TranslationReviewService.reviewed_languages()
        rows = []
        for language in reviewable_languages():
            changed = len(found["strings"].get(language, []))
            if not changed and not found["glossary_changed"]:
                continue
            rows.append(
                {
                    "code": language,
                    "changed": changed,
                    "awaiting": len(TranslationReviewService.pending(language)),
                    "reviewed": language in reviewed,
                }
            )
        return {"glossary_changed": found["glossary_changed"], "rows": rows}

    @staticmethod
    def notify_catalogue_changes() -> int:
        """Tells the StCd Owner what a new version changed in the interface text or the nomenclature.
        Sends nothing when the confidence check is current; one notice per change and person."""
        try:
            impact = TranslationImpactService.catalogue_impact()
            rows = impact["rows"]
            if not rows and not impact["glossary_changed"]:
                return 0
            total = sum(r["changed"] for r in rows)
            reviewed = [r for r in rows if r["reviewed"] and r["awaiting"]]
            message = (
                f"Interface text or nomenclature changed in this version: {total} strings in "
                f"{len([r for r in rows if r['changed']])} languages"
                + (f" ({_summary([r for r in rows if r['changed']], 'changed')})" if total else "")
                + ". "
            )
            if impact["glossary_changed"]:
                message += "The technical nomenclature changed. "
            message += (
                "The confidence check must be recorded for the change "
                "(scripts/translation_precheck.py --check)."
            )
            if reviewed:
                message += (
                    f" Follow-up reviews are due in {', '.join(r['code'] for r in reviewed[:SHOWN])} "
                    "(strings awaiting approval; Viewers read them in English until approved)."
                )
            digest = hashlib.sha256(
                json.dumps(
                    [[r["code"], r["changed"]] for r in rows] + [impact["glossary_changed"]]
                ).encode()
            ).hexdigest()[:12]
            recipients = {u.id for u in _owners()} | set(
                _reviewers_of({r["code"] for r in rows if r["changed"]})
            )
            sent = 0
            for user_id in sorted(recipients):
                notice = NotificationService.notify(
                    user_id,
                    KIND,
                    message,
                    link=LINK_TRANSLATIONS,
                    dedupe_key=f"catalogue-impact:{digest}:{user_id}",
                )
                sent += 1 if notice else 0
            db.session.commit()
            return sent
        except Exception:  # noqa: BLE001 - never stops a server from starting
            db.session.rollback()
            current_app.logger.exception(
                "translation impact of the catalogue could not be reported"
            )
            return 0

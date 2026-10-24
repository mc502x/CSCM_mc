"""Technical nomenclature (docs/26-translations.md, docs/03-srs.md FR-166).

The words of the controller and the workflow - Status Code, Hub Controller, Set delay, Draft,
Cross-Domain Sign-Off - have to be translated the same way in the interface, in the status code
content and in the manuals. This service keeps them as a vocabulary of its own, **apart from the
interface translations** of the translation review: other people (the technical staff, not the
native-speaker reviewers of the interface), other rules and other tables.

Who may do what:

* everybody who is signed in **reads** the terms;
* the Administrator, the StCd Owner and the Chief Engineer **manage** the terms (add, change the
  English, the definition, the category, switch a term off);
* they and the Engineer and the Reviewer **propose** a translation (a DRAFT);
* they and the Reviewer **approve** one; nobody approves their own proposal, the same segregation
  as BR-018. A proposal that ships with the tool has no proposer and any approver may approve it.

A term marked `keep_english` (StCd, MC, 2XM ...) is never translated."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from sqlalchemy import func

from app.domain.errors import DomainError, ForbiddenError, NotFoundError
from app.extensions import db
from app.models.terminology import TerminologyTerm, TerminologyTranslation
from app.models.user import User
from app.services.audit_service import AuditService
from app.terminology_seed import CATEGORIES
from app.translation_catalogue import (
    ENGLISH_NAMES,
    effective,
    reviewable_languages,
    screens,
    string_id,
)
from app.utils import utcnow_iso

MANAGE_ROLES = ("ADMINISTRATOR", "STCD_OWNER", "CHIEF_ENGINEER")
PROPOSE_ROLES = (*MANAGE_ROLES, "ENGINEER", "REVIEWER")
APPROVE_ROLES = (*MANAGE_ROLES, "REVIEWER")
MAX_TEXT = 200
_CODE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,79}$")


def _role(actor) -> str | None:
    return getattr(actor, "role_code", None)


def _need(actor, roles: tuple[str, ...], what: str) -> None:
    if _role(actor) not in roles:
        raise ForbiddenError(f"Only {', '.join(roles)} may {what}.")


def _language(code: str) -> str:
    if code not in reviewable_languages():
        raise NotFoundError("Unknown language")
    return code


class TerminologyService:
    # ------------------------------------------------------------------ access
    @staticmethod
    def can_manage(actor) -> bool:
        return _role(actor) in MANAGE_ROLES

    @staticmethod
    def can_propose(actor) -> bool:
        return _role(actor) in PROPOSE_ROLES

    @staticmethod
    def can_approve(actor) -> bool:
        return _role(actor) in APPROVE_ROLES

    # ------------------------------------------------------------------ reading
    @staticmethod
    def terms(
        *, category: str = "", q: str = "", include_inactive: bool = False
    ) -> list[TerminologyTerm]:
        query = db.session.query(TerminologyTerm)
        if not include_inactive:
            query = query.filter(TerminologyTerm.is_active == 1)
        if category in CATEGORIES:
            query = query.filter(TerminologyTerm.category == category)
        if q.strip():
            like = f"%{q.strip().lower()}%"
            query = query.filter(
                func.lower(TerminologyTerm.english).like(like)
                | func.lower(TerminologyTerm.code).like(like)
                | func.lower(TerminologyTerm.definition).like(like)
            )
        return query.order_by(TerminologyTerm.category, TerminologyTerm.english).all()

    @staticmethod
    def get(term_id: int) -> TerminologyTerm:
        term = db.session.get(TerminologyTerm, term_id)
        if term is None:
            raise NotFoundError("Term not found")
        return term

    @staticmethod
    def translations(language: str) -> dict[int, TerminologyTranslation]:
        rows = db.session.query(TerminologyTranslation).filter_by(language_code=language).all()
        return {row.term_id: row for row in rows}

    @staticmethod
    def coverage() -> list[dict[str, Any]]:
        """Per language: how many of the translatable terms are approved, draft or missing."""
        total = (
            db.session.query(func.count(TerminologyTerm.id))
            .filter(TerminologyTerm.is_active == 1, TerminologyTerm.keep_english == 0)
            .scalar()
        )
        counts: dict[tuple[str, str], int] = {}
        rows = (
            db.session.query(
                TerminologyTranslation.language_code,
                TerminologyTranslation.status,
                func.count(TerminologyTranslation.id),
            )
            .join(TerminologyTerm, TerminologyTerm.id == TerminologyTranslation.term_id)
            .filter(TerminologyTerm.is_active == 1, TerminologyTerm.keep_english == 0)
            .group_by(TerminologyTranslation.language_code, TerminologyTranslation.status)
            .all()
        )
        for language, status, n in rows:
            counts[(language, status)] = n
        out = []
        for code in reviewable_languages():
            approved, draft = counts.get((code, "APPROVED"), 0), counts.get((code, "DRAFT"), 0)
            out.append(
                {
                    "code": code,
                    "name": ENGLISH_NAMES[code],
                    "total": total,
                    "approved": approved,
                    "draft": draft,
                    "missing": max(total - approved - draft, 0),
                }
            )
        return out

    @staticmethod
    def worklist(
        language: str, *, category: str = "", q: str = "", state: str = ""
    ) -> list[dict[str, Any]]:
        """One row per term for one language: the term, its translation and what may be done."""
        _language(language)
        translations = TerminologyService.translations(language)
        names = {u.id: u.full_name for u in db.session.query(User).all()}
        rows = []
        for term in TerminologyService.terms(category=category, q=q):
            tr = translations.get(term.id)
            if term.keep_english:
                status = "KEEP"
            elif tr is None:
                status = "MISSING"
            else:
                status = tr.status
            if state and state != status:
                continue
            rows.append(
                {
                    "term": term,
                    "translation": tr,
                    "status": status,
                    "proposer": names.get(tr.proposed_by) if tr and tr.proposed_by else None,
                    "approver": names.get(tr.approved_by) if tr and tr.approved_by else None,
                }
            )
        return rows

    @staticmethod
    def approved(language: str) -> dict[str, str]:
        """code -> approved translation of the language (for exports and the interface)."""
        rows = (
            db.session.query(TerminologyTerm.code, TerminologyTranslation.text)
            .join(TerminologyTranslation, TerminologyTranslation.term_id == TerminologyTerm.id)
            .filter(
                TerminologyTranslation.language_code == language,
                TerminologyTranslation.status == "APPROVED",
                TerminologyTerm.is_active == 1,
            )
            .all()
        )
        return dict(rows)

    @staticmethod
    def term_text(code: str, language: str | None) -> str:
        """The approved translation of a term, else its English text (never blank)."""
        term = db.session.query(TerminologyTerm).filter_by(code=code).first()
        if term is None:
            return code
        if term.keep_english or not language or language == "en":
            return term.english
        text = TerminologyService.approved(language).get(code)
        return text or term.english

    # ------------------------------------------------------------------ managing terms
    @staticmethod
    def create_term(
        *, code: str, english: str, category: str, definition: str, keep_english: bool, actor
    ) -> TerminologyTerm:
        _need(actor, MANAGE_ROLES, "add a term")
        code = (code or "").strip().lower()
        english = (english or "").strip()
        if not _CODE.match(code):
            raise ValueError("The code is lower-case letters, digits and hyphens (2 to 80).")
        if not english or len(english) > MAX_TEXT:
            raise ValueError(f"The English term is required (at most {MAX_TEXT} characters).")
        if category not in CATEGORIES:
            raise ValueError("Choose a category.")
        if db.session.query(TerminologyTerm).filter_by(code=code).first():
            raise DomainError("A term with this code exists already.")
        now = utcnow_iso()
        term = TerminologyTerm(
            code=code,
            category=category,
            english=english,
            definition=(definition or "").strip()[:1000],
            keep_english=1 if keep_english else 0,
            is_active=1,
            created_by=actor.id,
            created_at=now,
            updated_at=now,
        )
        db.session.add(term)
        db.session.flush()
        AuditService.log(
            "TerminologyTerm",
            term.id,
            "TERM_CREATE",
            actor=actor,
            after={"code": code, "english": english, "category": category},
        )
        db.session.commit()
        TerminologyService._tell_owner(term, "added")
        return term

    @staticmethod
    def _tell_owner(term, action: str, language: str | None = None) -> None:
        """The StCd Owner learns which languages the change touches (FR-178)."""
        from app.services.translation_impact_service import TranslationImpactService

        TranslationImpactService.notify_term_change(term, action, language)

    @staticmethod
    def update_term(
        term_id: int,
        *,
        english: str,
        category: str,
        definition: str,
        keep_english: bool,
        is_active: bool,
        actor,
    ) -> TerminologyTerm:
        _need(actor, MANAGE_ROLES, "change a term")
        term = TerminologyService.get(term_id)
        english = (english or "").strip()
        if not english or len(english) > MAX_TEXT:
            raise ValueError(f"The English term is required (at most {MAX_TEXT} characters).")
        if category not in CATEGORIES:
            raise ValueError("Choose a category.")
        before = {
            "english": term.english,
            "category": term.category,
            "definition": term.definition,
            "keep_english": term.keep_english,
            "is_active": term.is_active,
        }
        reopened = 0
        if english != term.english:  # a changed meaning: every approval has to be given again
            for tr in db.session.query(TerminologyTranslation).filter_by(
                term_id=term.id, status="APPROVED"
            ):
                tr.status, tr.approved_by, tr.approved_at = "DRAFT", None, None
                reopened += 1
        term.english, term.category = english, category
        term.definition = (definition or "").strip()[:1000]
        term.keep_english = 1 if keep_english else 0
        term.is_active = 1 if is_active else 0
        term.updated_at = utcnow_iso()
        AuditService.log(
            "TerminologyTerm",
            term.id,
            "TERM_UPDATE",
            actor=actor,
            before=before,
            after={
                "english": term.english,
                "category": term.category,
                "definition": term.definition,
                "keep_english": term.keep_english,
                "is_active": term.is_active,
                "approvals_reopened": reopened,
            },
        )
        db.session.commit()
        TerminologyService._tell_owner(term, "changed")
        return term

    # ------------------------------------------------------------------ translating
    @staticmethod
    def propose(
        term_id: int, language: str, text: str, note: str | None, actor
    ) -> TerminologyTranslation | None:
        """Sets the translation of a term in a language as a DRAFT. Returns None when nothing
        changed (the same text again)."""
        _need(actor, PROPOSE_ROLES, "propose a translation")
        _language(language)
        term = TerminologyService.get(term_id)
        if term.keep_english:
            raise DomainError("This term is never translated.")
        text = (text or "").strip()
        note = (note or "").strip() or None
        if not text:
            raise ValueError("Enter the translation.")
        if len(text) > MAX_TEXT:
            raise ValueError(f"A translation has at most {MAX_TEXT} characters.")
        if note and len(note) > 500:
            raise ValueError("A note has at most 500 characters.")
        tr = (
            db.session.query(TerminologyTranslation)
            .filter_by(term_id=term_id, language_code=language)
            .first()
        )
        now = utcnow_iso()
        if tr is not None and tr.text == text and (note is None or note == tr.note):
            return None
        before = {"text": tr.text, "status": tr.status} if tr else None
        if tr is None:
            tr = TerminologyTranslation(term_id=term_id, language_code=language, text=text)
            db.session.add(tr)
        tr.text, tr.note, tr.status = text, note, "DRAFT"
        tr.proposed_by, tr.proposed_at = actor.id, now
        tr.approved_by = tr.approved_at = None
        db.session.flush()
        AuditService.log(
            "TerminologyTranslation",
            tr.id,
            "TERM_TRANSLATE",
            actor=actor,
            before=before,
            after={"term": term.code, "language": language, "text": text},
        )
        db.session.commit()
        return tr

    @staticmethod
    def approve(translation_id: int, actor) -> TerminologyTranslation:
        _need(actor, APPROVE_ROLES, "approve a translation")
        tr = db.session.get(TerminologyTranslation, translation_id)
        if tr is None:
            raise NotFoundError("Translation not found")
        if tr.status == "APPROVED":
            raise DomainError("This translation is approved already.")
        if tr.proposed_by is not None and tr.proposed_by == actor.id:
            raise DomainError("You cannot approve your own proposal; another person does.")
        tr.status, tr.approved_by, tr.approved_at = "APPROVED", actor.id, utcnow_iso()
        term = TerminologyService.get(tr.term_id)
        AuditService.log(
            "TerminologyTranslation",
            tr.id,
            "TERM_APPROVE",
            actor=actor,
            after={"term": term.code, "language": tr.language_code, "text": tr.text},
        )
        db.session.commit()
        TerminologyService._tell_owner(term, "translation approved", tr.language_code)
        return tr

    @staticmethod
    def approve_all(language: str, actor) -> int:
        """Approves every draft of the language that the actor did not propose."""
        _need(actor, APPROVE_ROLES, "approve a translation")
        _language(language)
        done = 0
        drafts = (
            db.session.query(TerminologyTranslation)
            .join(TerminologyTerm, TerminologyTerm.id == TerminologyTranslation.term_id)
            .filter(
                TerminologyTranslation.language_code == language,
                TerminologyTranslation.status == "DRAFT",
                TerminologyTerm.is_active == 1,
            )
            .all()
        )
        for tr in drafts:
            if tr.proposed_by == actor.id:
                continue
            TerminologyService.approve(tr.id, actor)
            done += 1
        return done

    @staticmethod
    def reject(translation_id: int, note: str | None, actor) -> TerminologyTranslation:
        """Sends an approved or proposed translation back to DRAFT with a note for the proposer."""
        _need(actor, APPROVE_ROLES, "reject a translation")
        tr = db.session.get(TerminologyTranslation, translation_id)
        if tr is None:
            raise NotFoundError("Translation not found")
        note = (note or "").strip()
        if not note:
            raise ValueError("Say why in the note.")
        tr.status, tr.approved_by, tr.approved_at = "DRAFT", None, None
        tr.note = note[:500]
        term = TerminologyService.get(tr.term_id)
        AuditService.log(
            "TerminologyTranslation",
            tr.id,
            "TERM_REJECT",
            actor=actor,
            after={"term": term.code, "language": tr.language_code, "note": tr.note},
        )
        db.session.commit()
        return tr

    # ------------------------------------------------------------------ consistency
    @staticmethod
    def check(language: str, limit: int = 300) -> list[dict[str, str]]:
        """Interface strings that contain a term of the vocabulary whose translation does not
        contain the translation of that term. A hint for the reviewer, not a verdict: inflected
        languages (Hindi, Georgian, Finnic ...) change the ending of a word."""
        _language(language)
        translations = TerminologyService.translations(language)
        catalogue = effective(language)
        findings: list[dict[str, str]] = []
        terms = [
            t
            for t in TerminologyService.terms()
            if not t.keep_english and t.id in translations and len(t.english) >= 4
        ]
        # longest English first, so "Status Code Identifier" is looked for before "Status Code"
        terms.sort(key=lambda t: -len(t.english))
        for english, translated in catalogue.items():
            remaining = english
            for term in terms:
                pattern = re.compile(r"(?<![A-Za-z])" + re.escape(term.english) + r"(?![A-Za-z])")
                if not pattern.search(remaining):
                    continue
                remaining = pattern.sub(" ", remaining)  # a longer term uses up its words
                expected = translations[term.id].text
                if expected.casefold() not in translated.casefold():
                    findings.append(
                        {
                            "string_id": string_id(english),
                            "english": english,
                            "translation": translated,
                            "term": term.english,
                            "expected": expected,
                            "status": translations[term.id].status,
                        }
                    )
                if len(findings) >= limit:
                    return findings
        return findings

    @staticmethod
    def screens_with(term: TerminologyTerm) -> int:
        """How many interface strings contain the term (for the term's page)."""
        pattern = re.compile(r"(?<![A-Za-z])" + re.escape(term.english) + r"(?![A-Za-z])")
        return sum(1 for s in screens() if pattern.search(s))

    # ------------------------------------------------------------------ export
    @staticmethod
    def export_rows(language: str | None = None) -> tuple[list[str], list[list[str]]]:
        """Header and rows of the vocabulary: one language, or every language side by side."""
        languages = [_language(language)] if language else reviewable_languages()
        header = ["code", "category", "english", "definition", "keep_english"]
        header += [f"{lang}" for lang in languages] + [f"{lang}_status" for lang in languages]
        translations = {lang: TerminologyService.translations(lang) for lang in languages}
        rows = []
        for term in TerminologyService.terms():
            line = [term.code, term.category, term.english, term.definition, str(term.keep_english)]
            line += [
                translations[lang][term.id].text if term.id in translations[lang] else ""
                for lang in languages
            ]
            line += [
                translations[lang][term.id].status if term.id in translations[lang] else ""
                for lang in languages
            ]
            rows.append(line)
        return header, rows

    @staticmethod
    def export_csv(language: str | None = None) -> bytes:
        header, rows = TerminologyService.export_rows(language)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(header)
        for row in rows:
            # a cell that starts with a formula character is neutralised (SEC-024)
            writer.writerow(
                ["'" + c if c[:1] in ("=", "+", "-", "@") and len(c) > 1 else c for c in row]
            )
        return ("﻿" + buffer.getvalue()).encode("utf-8")

    @staticmethod
    def export_xlsx(language: str | None = None) -> bytes:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font

        header, rows = TerminologyService.export_rows(language)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Terminology"
        sheet.append(header)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for row in rows:
            sheet.append(["'" + c if c[:1] in ("=", "+", "@") and len(c) > 1 else c for c in row])
        for column in sheet.columns:
            width = max(len(str(c.value or "")) for c in column[:60])
            sheet.column_dimensions[column[0].column_letter].width = min(max(width + 2, 10), 60)
        if language in ("ar", "ur"):
            for row in sheet.iter_rows(min_row=2, min_col=6, max_col=6):
                for cell in row:
                    cell.alignment = Alignment(horizontal="right", readingOrder=2)
        out = io.BytesIO()
        workbook.save(out)
        return out.getvalue()

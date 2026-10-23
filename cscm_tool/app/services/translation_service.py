"""Multilingual content with its own light review (I-15, decision D-03).

The text stored on a revision is in the catalogue's *source* language (English). Other
languages are translations of one revision: `revision_translation`, status DRAFT or
APPROVED; no row means MISSING. A translation is reviewed by one person other than the
translator - deliberately not the three-decision cycle of the source text. Editing an
approved translation sends it back to DRAFT. Exports in a language use approved
translations only."""

from app.domain.errors import DomainError, ForbiddenError, InvalidTransitionError, NotFoundError
from app.extensions import db
from app.models.lookup import LookupLanguage
from app.models.operations import RevisionTranslation
from app.models.status_code import StatusCode, StatusCodeRevision
from app.services.audit_service import AuditService
from app.utils import utcnow_iso

# The source text is stable (and so worth translating) from Approved onwards.
_TRANSLATABLE_STATES = ("APPROVED", "RELEASED", "DEPRECATED")


def source_language() -> LookupLanguage:
    language = db.session.query(LookupLanguage).filter(LookupLanguage.is_source == 1).first()
    if language is None:  # cannot happen with the seed data; fail loudly rather than guess
        raise DomainError("No source language is configured.")
    return language


def _language(code: str) -> LookupLanguage:
    language = (
        db.session.query(LookupLanguage)
        .filter(LookupLanguage.code == code, LookupLanguage.is_active == 1)
        .first()
    )
    if language is None:
        raise ValueError(f"Unknown or inactive language '{code}'.")
    if language.is_source:
        raise ValueError("The source language is edited on the revision itself.")
    return language


def _revision(revision_id: int) -> StatusCodeRevision:
    revision = db.session.get(StatusCodeRevision, revision_id)
    if revision is None or revision.status_code.is_sandbox:
        raise NotFoundError("Revision not found")
    return revision


class TranslationService:
    @staticmethod
    def approved_for(revision_ids: list[int], language_code: str) -> dict[int, RevisionTranslation]:
        """revision id -> approved translation, for the export pipeline."""
        if not revision_ids:
            return {}
        language = _language(language_code)
        rows = (
            db.session.query(RevisionTranslation)
            .filter(
                RevisionTranslation.language_id == language.id,
                RevisionTranslation.translation_status == "APPROVED",
                RevisionTranslation.status_code_revision_id.in_(revision_ids),
            )
            .all()
        )
        return {row.status_code_revision_id: row for row in rows}

    @staticmethod
    def status_matrix(revision_id: int, actor) -> list[dict]:
        revision = _revision(revision_id)
        existing = {
            t.language_id: t
            for t in db.session.query(RevisionTranslation)
            .filter(RevisionTranslation.status_code_revision_id == revision.id)
            .all()
        }
        rows = []
        for language in (
            db.session.query(LookupLanguage)
            .filter(LookupLanguage.is_active == 1, LookupLanguage.is_source == 0)
            .order_by(LookupLanguage.sort_order)
            .all()
        ):
            translation = existing.get(language.id)
            if actor.role_code == "VIEWER" and (
                translation is None or translation.translation_status != "APPROVED"
            ):
                translation = None  # Viewers only ever see approved text
            rows.append(
                {
                    "language": language.code,
                    "label": language.label,
                    "status": translation.translation_status if translation else "MISSING",
                    "title": translation.title if translation else None,
                    "description": translation.description if translation else None,
                    "remedy_text": translation.remedy_text if translation else None,
                    "translated_by": translation.translated_by if translation else None,
                    "approved_by": translation.approved_by if translation else None,
                }
            )
        return rows

    @staticmethod
    def save(
        revision_id: int,
        language_code: str,
        title: str,
        description: str,
        remedy_text: str | None,
        actor,
    ) -> RevisionTranslation:
        if actor.role_code not in ("ENGINEER", "ADMINISTRATOR"):
            raise ForbiddenError("SEC-010: only Engineers and Administrators can translate.")
        revision = _revision(revision_id)
        language = _language(language_code)
        if revision.lifecycle_status not in _TRANSLATABLE_STATES:
            raise InvalidTransitionError(
                "Translate a revision once its source text is Approved (or Released)."
            )
        title, description = (title or "").strip(), (description or "").strip()
        remedy_text = (remedy_text or "").strip() or None
        if not 1 <= len(title) <= 120:
            raise ValueError("The translated title must be 1-120 characters.")
        if not 1 <= len(description) <= 4000:
            raise ValueError("The translated description must be 1-4000 characters.")
        if remedy_text and len(remedy_text) > 4000:
            raise ValueError("The translated remedy text must be at most 4000 characters.")

        row = (
            db.session.query(RevisionTranslation)
            .filter(
                RevisionTranslation.status_code_revision_id == revision.id,
                RevisionTranslation.language_id == language.id,
            )
            .first()
        )
        before = None
        if row is None:
            row = RevisionTranslation(
                status_code_revision_id=revision.id,
                language_id=language.id,
                title=title,
                description=description,
                remedy_text=remedy_text,
                translation_status="DRAFT",
                translated_by=actor.id,
                translated_at=utcnow_iso(),
            )
            db.session.add(row)
        else:
            before = {"status": row.translation_status, "title": row.title}
            row.title, row.description, row.remedy_text = title, description, remedy_text
            row.translation_status = "DRAFT"
            row.translated_by, row.translated_at = actor.id, utcnow_iso()
            row.approved_by = row.approved_at = None
        db.session.flush()
        AuditService.log(
            "StatusCodeRevision",
            revision.id,
            "TRANSLATION_SAVE",
            actor=actor,
            before=before,
            after={"language": language.code, "status": "DRAFT", "title": title},
        )
        db.session.commit()
        return row

    @staticmethod
    def approve(revision_id: int, language_code: str, actor) -> RevisionTranslation:
        if actor.role_code not in ("REVIEWER", "ADMINISTRATOR"):
            raise ForbiddenError(
                "SEC-010: only a Reviewer or Administrator approves a translation."
            )
        revision = _revision(revision_id)
        language = _language(language_code)
        row = (
            db.session.query(RevisionTranslation)
            .filter(
                RevisionTranslation.status_code_revision_id == revision.id,
                RevisionTranslation.language_id == language.id,
            )
            .first()
        )
        if row is None:
            raise NotFoundError("There is no translation to approve.")
        if row.translated_by == actor.id:
            raise ForbiddenError("BR-005: a translation must be approved by someone else.")
        if row.translation_status == "APPROVED":
            return row
        row.translation_status = "APPROVED"
        row.approved_by, row.approved_at = actor.id, utcnow_iso()
        AuditService.log(
            "StatusCodeRevision",
            revision.id,
            "TRANSLATION_APPROVE",
            actor=actor,
            after={"language": language.code, "translated_by": row.translated_by},
        )
        db.session.commit()
        return row

    @staticmethod
    def carry_over(revision_id: int, actor) -> list[str]:
        """Copy the previous revision's translations as DRAFTs for every language the new
        revision does not have yet - a head start when only a detail changed."""
        if actor.role_code not in ("ENGINEER", "ADMINISTRATOR"):
            raise ForbiddenError("SEC-010: only Engineers and Administrators can translate.")
        revision = _revision(revision_id)
        previous = (
            db.session.query(StatusCodeRevision)
            .filter(
                StatusCodeRevision.status_code_id == revision.status_code_id,
                StatusCodeRevision.revision_number < revision.revision_number,
            )
            .order_by(StatusCodeRevision.revision_number.desc())
            .first()
        )
        if previous is None:
            return []
        copied = []
        have = {
            t.language_id
            for t in db.session.query(RevisionTranslation)
            .filter(RevisionTranslation.status_code_revision_id == revision.id)
            .all()
        }
        for old in (
            db.session.query(RevisionTranslation)
            .filter(RevisionTranslation.status_code_revision_id == previous.id)
            .all()
        ):
            if old.language_id in have:
                continue
            db.session.add(
                RevisionTranslation(
                    status_code_revision_id=revision.id,
                    language_id=old.language_id,
                    title=old.title,
                    description=old.description,
                    remedy_text=old.remedy_text,
                    translation_status="DRAFT",
                    translated_by=actor.id,
                    translated_at=utcnow_iso(),
                )
            )
            copied.append(old.language.code)
        if copied:
            AuditService.log(
                "StatusCodeRevision",
                revision.id,
                "TRANSLATION_CARRY_OVER",
                actor=actor,
                after={"languages": sorted(copied), "from_revision": previous.revision_number},
            )
        db.session.commit()
        return sorted(copied)

    @staticmethod
    def worklist(language_code: str) -> list[dict]:
        """Current Released codes that still lack an approved translation."""
        language = _language(language_code)
        approved = {
            row.status_code_revision_id
            for row in db.session.query(RevisionTranslation).filter(
                RevisionTranslation.language_id == language.id,
                RevisionTranslation.translation_status == "APPROVED",
            )
        }
        drafts = {
            row.status_code_revision_id
            for row in db.session.query(RevisionTranslation).filter(
                RevisionTranslation.language_id == language.id,
                RevisionTranslation.translation_status == "DRAFT",
            )
        }
        items = []
        revisions = (
            db.session.query(StatusCodeRevision, StatusCode)
            .join(StatusCode, StatusCode.id == StatusCodeRevision.status_code_id)
            .filter(
                StatusCode.is_sandbox == 0,
                StatusCodeRevision.is_current == 1,
                StatusCodeRevision.lifecycle_status.in_(("APPROVED", "RELEASED")),
            )
            .order_by(StatusCode.status_code_identifier)
            .all()
        )
        for revision, code in revisions:
            if revision.id in approved:
                continue
            items.append(
                {
                    "revision_id": revision.id,
                    "status_code_id": code.id,
                    "status_code_identifier": code.status_code_identifier,
                    "title": revision.title,
                    "status": "DRAFT" if revision.id in drafts else "MISSING",
                }
            )
        return items

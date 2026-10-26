"""Soft referential integrity between status codes (I-04).

`status_code_for_repeated_error` is deliberately an opaque number, not a foreign
key (docs/06-data-dictionary.md §2b: the escalation pool may be outside StCd
governance), so none of this ever blocks a save. It *warns* when a reference
cannot be resolved or points at a code that is Deprecated or Archived, and it
answers "what depends on this code?" for the Where-used panel and for the
acknowledgement a deprecation request has to give.

A number N is resolved against the catalogue as the identifier `StCd-NNNNN` or
as a `legacy_reference_number` equal to N - whichever exists."""

from app.extensions import db
from app.models.status_code import StatusCode, StatusCodeRevision
from app.services.validation import split_identifier_list

_DEAD_STATES = ("DEPRECATED", "ARCHIVED")


def _identifier_for(number: int) -> str:
    return f"StCd-{number:05d}"


class ReferenceService:
    @staticmethod
    def resolve_number(number: int) -> list[StatusCode]:
        """Catalogue codes that a bare reference number can mean (usually zero or one)."""
        return (
            db.session.query(StatusCode)
            .filter(
                StatusCode.is_sandbox == 0,
                (StatusCode.status_code_identifier == _identifier_for(number))
                | (StatusCode.legacy_reference_number == str(number)),
            )
            .all()
        )

    @staticmethod
    def _current(status_code: StatusCode) -> StatusCodeRevision | None:
        return (
            db.session.query(StatusCodeRevision)
            .filter(
                StatusCodeRevision.status_code_id == status_code.id,
                StatusCodeRevision.is_current == 1,
            )
            .first()
        )

    @staticmethod
    def _finding(field: str, reference: str, target: StatusCode | None) -> dict | None:
        if target is None:
            return {
                "type": "UNKNOWN_REFERENCE",
                "field": field,
                "message": f"{reference} does not match any catalogue code. That is fine for an "
                "external escalation number; otherwise check the number.",
            }
        current = ReferenceService._current(target)
        if current is not None and current.lifecycle_status in _DEAD_STATES:
            return {
                "type": f"{current.lifecycle_status}_REFERENCE",
                "field": field,
                "message": f"{reference} ({target.status_code_identifier}) is "
                f"{current.lifecycle_status.title()}; the reference may mislead readers.",
            }
        return None

    @staticmethod
    def warnings_for_revision(revision: StatusCodeRevision) -> list[dict]:
        """Findings for the references this revision carries."""
        warnings: list[dict] = []
        own_id = revision.status_code_id

        number = revision.status_code_for_repeated_error
        if number is not None:
            matches = ReferenceService.resolve_number(number)
            if matches and all(m.id == own_id for m in matches):
                warnings.append(
                    {
                        "type": "SELF_REFERENCE",
                        "field": "status_code_for_repeated_error",
                        "message": "The escalation code for a repeated error points at this "
                        "very code.",
                    }
                )
            else:
                finding = ReferenceService._finding(
                    "status_code_for_repeated_error",
                    f"Escalation code {number}",
                    matches[0] if matches else None,
                )
                if finding:
                    warnings.append(finding)

        for identifier in split_identifier_list(revision.related_status_codes):
            target = (
                db.session.query(StatusCode)
                .filter(StatusCode.status_code_identifier == identifier)
                .first()
            )
            finding = ReferenceService._finding("related_status_codes", identifier, target)
            if finding:
                warnings.append(finding)

        if revision.superseded_by_status_code_id:
            target = db.session.get(StatusCode, revision.superseded_by_status_code_id)
            finding = ReferenceService._finding(
                "superseded_by_status_code_id",
                "The superseding code",
                target,
            )
            if finding:
                warnings.append(finding)
        return warnings

    @staticmethod
    def where_used(status_code_id: int, live_only: bool = False) -> list[dict]:
        """Every other code whose *current* revision refers to `status_code_id`.
        `live_only` leaves out codes that are themselves Deprecated/Archived (they no
        longer matter to a deprecation decision)."""
        target = db.session.get(StatusCode, status_code_id)
        if target is None:
            return []
        numbers: set[int] = set()
        if target.status_code_identifier and target.status_code_identifier[5:].isdigit():
            numbers.add(int(target.status_code_identifier[5:]))
        if target.legacy_reference_number and target.legacy_reference_number.isdigit():
            numbers.add(int(target.legacy_reference_number))

        query = (
            db.session.query(StatusCodeRevision, StatusCode)
            .join(StatusCode, StatusCode.id == StatusCodeRevision.status_code_id)
            .filter(
                StatusCodeRevision.is_current == 1,
                StatusCode.id != status_code_id,
                StatusCode.is_sandbox == 0,
            )
        )
        if live_only:
            query = query.filter(StatusCodeRevision.lifecycle_status.notin_(_DEAD_STATES))

        found: dict[tuple[int, str], dict] = {}

        def add(revision: StatusCodeRevision, code: StatusCode, relation: str) -> None:
            found.setdefault(
                (code.id, relation),
                {
                    "status_code_id": code.id,
                    "status_code_identifier": code.status_code_identifier,
                    "title": revision.title,
                    "lifecycle_status": revision.lifecycle_status,
                    "relation": relation,
                },
            )

        if numbers:
            for revision, code in query.filter(
                StatusCodeRevision.status_code_for_repeated_error.in_(numbers)
            ):
                add(revision, code, "REPEATED_ERROR")
        for revision, code in query.filter(
            StatusCodeRevision.superseded_by_status_code_id == status_code_id
        ):
            add(revision, code, "SUPERSEDED_BY")
        if target.status_code_identifier:
            for revision, code in query.filter(
                StatusCodeRevision.related_status_codes.like(f"%{target.status_code_identifier}%")
            ):
                if target.status_code_identifier in split_identifier_list(
                    revision.related_status_codes
                ):
                    add(revision, code, "RELATED")
        for revision, code in query.filter(
            StatusCode.platform_variant_of_status_code_id == status_code_id
        ):
            add(revision, code, "PLATFORM_VARIANT")

        return sorted(
            found.values(),
            key=lambda d: (d["status_code_identifier"] or "", d["relation"]),
        )

"""Field-level revision diff (FR-032, FR-064; docs/09-api-specification.md
`GET /status-codes/{id}/revisions/{a}/diff/{b}`). Compares the flat export
rows of two revisions (the same column names the catalogue exports use), so
every content field is covered and audience-access values read as codes."""

from app.domain.errors import NotFoundError
from app.models.status_code import StatusCodeRevision
from app.services.export_service import flatten_revision
from app.services.status_code_service import StatusCodeService

# Bookkeeping that differs between any two revisions and is not a content change.
_IGNORED = frozenset({"revision_number", "lifecycle_status", "effective_date"})

_BASELINE_STATES = ("APPROVED", "RELEASED", "DEPRECATED", "ARCHIVED")


class RevisionDiffService:
    @staticmethod
    def field_changes(old: StatusCodeRevision | None, new: StatusCodeRevision) -> list[dict]:
        """`old=None` means a brand-new code: every populated field is an addition."""
        new_payload = flatten_revision(new)
        old_payload = flatten_revision(old) if old is not None else {}
        changes = []
        for field, new_value in new_payload.items():
            if field in _IGNORED:
                continue
            old_value = old_payload.get(field)
            if old_value != new_value:
                changes.append({"field": field, "old_value": old_value, "new_value": new_value})
        return changes

    @staticmethod
    def diff_revisions(status_code_id: int, rev_a: int, rev_b: int, actor_user) -> dict:
        """`rev_a`/`rev_b` are revision numbers within the status code."""
        visible = {
            r.revision_number: r
            for r in StatusCodeService.list_revision_history(status_code_id, actor_user)
        }
        if rev_a not in visible or rev_b not in visible:
            raise NotFoundError("Revision not found")
        return {
            "status_code_id": status_code_id,
            "from_revision": rev_a,
            "to_revision": rev_b,
            "field_changes": RevisionDiffService.field_changes(visible[rev_a], visible[rev_b]),
        }

    @staticmethod
    def baseline_for(revision: StatusCodeRevision) -> StatusCodeRevision | None:
        """FR-032: the latest decided revision of the same code before this
        one (None means this is a new code)."""
        candidates = [
            r
            for r in revision.status_code.revisions
            if r.revision_number < revision.revision_number
            and r.lifecycle_status in _BASELINE_STATES
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.revision_number)

    @staticmethod
    def diff_against_baseline(revision: StatusCodeRevision) -> dict:
        baseline = RevisionDiffService.baseline_for(revision)
        return {
            "is_new_code": baseline is None,
            "baseline_revision_number": baseline.revision_number if baseline else None,
            "field_changes": RevisionDiffService.field_changes(baseline, revision),
        }

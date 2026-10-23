"""Software-version binding and the applicability matrix (I-07, decision D-01).

A status code only means something for a given controller software version. The model:

* `lookup_controller_software_version` is an ordered list (sort_order = release order).
* Each revision declares the version range it applies to - `applies_from`/`applies_to`,
  inclusive, either end open.
* A Release targets one or more versions (`release_target_version`).

The matrix answers "which codes exist in version X" and "what changed between X and Y"
from the latest Released revision of every code."""

from app.domain.errors import NotFoundError
from app.extensions import db
from app.models.lookup import LookupControllerSoftwareVersion
from app.models.status_code import StatusCodeRevision
from app.repositories.status_code_repository import StatusCodeRepository


class SoftwareVersionService:
    _repo = StatusCodeRepository()

    @staticmethod
    def ordered() -> list[LookupControllerSoftwareVersion]:
        return (
            db.session.query(LookupControllerSoftwareVersion)
            .filter(LookupControllerSoftwareVersion.is_active == 1)
            .order_by(
                LookupControllerSoftwareVersion.sort_order, LookupControllerSoftwareVersion.id
            )
            .all()
        )

    @staticmethod
    def get_by_code(code: str) -> LookupControllerSoftwareVersion:
        version = (
            db.session.query(LookupControllerSoftwareVersion)
            .filter(LookupControllerSoftwareVersion.code == code)
            .first()
        )
        if version is None:
            raise NotFoundError(f"Unknown controller software version '{code}'.")
        return version

    @staticmethod
    def applies(revision: StatusCodeRevision, version: LookupControllerSoftwareVersion) -> bool:
        first, last = revision.applies_from_version, revision.applies_to_version
        if first is not None and version.sort_order < first.sort_order:
            return False
        if last is not None and version.sort_order > last.sort_order:
            return False
        return True

    @staticmethod
    def applicable_revisions(version_code: str) -> list[StatusCodeRevision]:
        version = SoftwareVersionService.get_by_code(version_code)
        released = SoftwareVersionService._repo.list_latest_released()
        return [r for r in released if SoftwareVersionService.applies(r, version)]

    @staticmethod
    def matrix(version_code: str) -> dict:
        revisions = SoftwareVersionService.applicable_revisions(version_code)
        return {
            "software_version": version_code,
            "count": len(revisions),
            "items": [_row(r) for r in revisions],
        }

    @staticmethod
    def changes_between(from_code: str, to_code: str) -> dict:
        """Codes added, removed and changed when moving from one version to another."""
        from app.services.revision_diff_service import RevisionDiffService

        before = {
            r.status_code_id: r for r in SoftwareVersionService.applicable_revisions(from_code)
        }
        after = {r.status_code_id: r for r in SoftwareVersionService.applicable_revisions(to_code)}
        added = [_row(after[i]) for i in sorted(after.keys() - before.keys())]
        removed = [_row(before[i]) for i in sorted(before.keys() - after.keys())]
        changed = []
        for status_code_id in sorted(after.keys() & before.keys()):
            old, new = before[status_code_id], after[status_code_id]
            if old.id != new.id:
                changed.append(
                    {**_row(new), "changes": RevisionDiffService.field_changes(old, new)}
                )
        return {
            "from": from_code,
            "to": to_code,
            "added": added,
            "removed": removed,
            "changed": changed,
        }


def _row(revision: StatusCodeRevision) -> dict:
    return {
        "status_code_id": revision.status_code_id,
        "status_code_identifier": revision.status_code.status_code_identifier,
        "title": revision.title,
        "revision_number": revision.revision_number,
        "applies_from": (
            revision.applies_from_version.code if revision.applies_from_version else None
        ),
        "applies_to": revision.applies_to_version.code if revision.applies_to_version else None,
    }

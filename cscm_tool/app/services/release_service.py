"""Release Management. FR-040-FR-048, BR-006-BR-008."""

import json

from app.domain.errors import DomainError, InvalidTransitionError
from app.extensions import db
from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup
from app.models.release import Release, ReleaseItem
from app.models.status_code import StatusCode, StatusCodeRevision
from app.repositories.release_repository import ReleaseRepository
from app.services.audit_service import AuditService
from app.services.lookup_service import LookupService
from app.utils import utcnow_iso


class ReleaseService:
    """BR-008: create/publish/pre-publish-delete are Administrator-only,
    enforced by the route decorator (SEC-010 also requires this to hold
    even if a route were ever misconfigured — every method here assumes
    the caller already passed that check, matching the pattern used by
    every other service in this codebase)."""

    _repo = ReleaseRepository()

    @staticmethod
    def create(data: dict, actor) -> Release:
        """FR-040."""
        release = Release(
            name=data["name"],
            version_label=data["version_label"],
            description=data.get("description"),
            scope_filter=json.dumps(data.get("scope_filter") or {}),
            status="BUILDING",
            created_by=actor.id,
            created_at=utcnow_iso(),
        )
        db.session.add(release)
        db.session.flush()
        AuditService.log(
            "Release",
            release.id,
            "RELEASE_CREATE",
            actor=actor,
            after={
                "name": release.name,
                "version_label": release.version_label,
                "scope_filter": data.get("scope_filter") or {},
            },
        )
        db.session.commit()
        return release

    @staticmethod
    def list_all() -> list[Release]:
        return ReleaseService._repo.list()

    @staticmethod
    def get(release_id: int) -> Release:
        return ReleaseService._repo.get_or_404(release_id)

    @staticmethod
    def list_candidates(release_id: int) -> list[StatusCodeRevision]:
        """FR-041: non-sandbox Approved revisions matching the Release's
        scope_filter, excluding any revision already claimed by a
        *different* Release (release_item.status_code_revision_id is
        globally unique)."""
        release = ReleaseService._repo.get_or_404(release_id)
        scope = json.loads(release.scope_filter or "{}")

        query = (
            db.session.query(StatusCodeRevision)
            .join(StatusCode, StatusCode.id == StatusCodeRevision.status_code_id)
            .filter(StatusCodeRevision.lifecycle_status == "APPROVED", StatusCode.is_sandbox == 0)
        )
        group_code = scope.get("functional_system_group")
        if group_code:
            group = LookupService.get_by_code(LookupFunctionalSystemGroup, group_code)
            query = query.filter(StatusCode.functional_system_group_id == group.id)
        subgroup_code = scope.get("functional_subgroup")
        if subgroup_code:
            subgroup = LookupService.get_by_code(LookupFunctionalSubgroup, subgroup_code)
            query = query.filter(StatusCode.functional_subgroup_id == subgroup.id)

        claimed_elsewhere = {
            item.status_code_revision_id
            for item in db.session.query(ReleaseItem).filter(ReleaseItem.release_id != release_id)
        }
        return [r for r in query.all() if r.id not in claimed_elsewhere]

    @staticmethod
    def set_items(release_id: int, revision_ids: list[int], actor) -> Release:
        """FR-042: pre-publish only. Sandbox/non-Approved revisions are
        rejected here (service layer) and, for sandbox specifically, also
        by trg_prevent_sandbox_release (defense in depth)."""
        release = ReleaseService._repo.get_or_404(release_id)
        if release.status != "BUILDING":
            raise InvalidTransitionError("Cannot change items on a published Release (BR-007).")

        before_ids = sorted(item.status_code_revision_id for item in release.items)

        db.session.query(ReleaseItem).filter(ReleaseItem.release_id == release.id).delete()
        db.session.flush()
        for revision_id in revision_ids:
            revision = db.session.get(StatusCodeRevision, revision_id)
            if revision is None:
                raise ValueError(f"Revision {revision_id} not found")
            if revision.status_code.is_sandbox:
                raise DomainError("Sandbox revisions can never be added to a Release (FR-048).")
            if revision.lifecycle_status != "APPROVED":
                raise DomainError(f"Revision {revision_id} is not in Approved state.")
            db.session.add(ReleaseItem(release_id=release.id, status_code_revision_id=revision_id))

        AuditService.log(
            "Release",
            release.id,
            "RELEASE_ITEMS_SET",
            actor=actor,
            before={"status_code_revision_ids": before_ids},
            after={"status_code_revision_ids": sorted(revision_ids)},
        )
        db.session.commit()
        return release

    @staticmethod
    def publish(release_id: int, actor) -> Release:
        """FR-043: atomically transitions every included revision
        Approved -> Released, stamps effective_date, marks the Release
        immutable. FR-044/BR-007: a published Release can never be
        unpublished or have its items changed (trg_prevent_release_item_delete
        is defense in depth for the latter)."""
        release = ReleaseService._repo.get_or_404(release_id)
        if release.status != "BUILDING":
            raise InvalidTransitionError("Release is already published.")
        if not release.items:
            raise DomainError("Cannot publish a Release with no items.")

        now = utcnow_iso()
        for item in release.items:
            revision = item.revision
            AuditService.log(
                "StatusCodeRevision",
                revision.id,
                "RELEASE_PUBLISH",
                actor=actor,
                before={"lifecycle_status": "APPROVED"},
                after={"lifecycle_status": "RELEASED"},
            )
            revision.lifecycle_status = "RELEASED"
            revision.effective_date = now

        release.status = "PUBLISHED"
        release.published_by = actor.id
        release.published_at = now

        db.session.commit()
        return release

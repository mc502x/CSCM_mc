"""Release Management. FR-040-FR-048, BR-006-BR-008."""

import json

from app.domain.authz import require_roles
from app.domain.errors import DomainError, InvalidTransitionError, NotFoundError
from app.extensions import db
from app.models.export_job import ExportJob
from app.models.lookup import (
    LookupControllerSoftwareVersion,
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
)
from app.models.release import Release, ReleaseItem, ReleaseTargetVersion
from app.models.status_code import StatusCode, StatusCodeRevision
from app.repositories.release_repository import ReleaseRepository
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.lookup_service import LookupService
from app.utils import utcnow_iso


def require_released_or_owner(release: Release, actor) -> None:
    """FR-175: the files of a Release are for everybody once it is published; before that only the
    StCd Owner and the Administrator may take them."""
    if release.status != "PUBLISHED" and actor.role_code not in ("STCD_OWNER", "ADMINISTRATOR"):
        raise NotFoundError("Release not found")


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
        require_roles(actor, "ADMINISTRATOR")
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
        if data.get("target_software_versions"):
            ReleaseService.set_target_versions(release.id, data["target_software_versions"], actor)
        return release

    @staticmethod
    def target_versions(release: Release) -> list[LookupControllerSoftwareVersion]:
        """I-07: the controller software versions this Release is published for."""
        return (
            db.session.query(LookupControllerSoftwareVersion)
            .join(
                ReleaseTargetVersion,
                ReleaseTargetVersion.software_version_id == LookupControllerSoftwareVersion.id,
            )
            .filter(ReleaseTargetVersion.release_id == release.id)
            .order_by(LookupControllerSoftwareVersion.sort_order)
            .all()
        )

    @staticmethod
    def set_target_versions(release_id: int, version_codes: list[str], actor) -> Release:
        """I-07: pre-publish only; a published Release's targets are as immutable as its items."""
        require_roles(actor, "ADMINISTRATOR")
        release = ReleaseService._repo.get_or_404(release_id)
        if release.status != "BUILDING":
            raise InvalidTransitionError(
                "Cannot change the targets of a published Release (BR-007)."
            )
        versions = []
        for code in dict.fromkeys(version_codes):  # de-duplicated, order kept
            version = (
                db.session.query(LookupControllerSoftwareVersion)
                .filter(
                    LookupControllerSoftwareVersion.code == code,
                    LookupControllerSoftwareVersion.is_active == 1,
                )
                .first()
            )
            if version is None:
                raise ValueError(f"Unknown controller software version '{code}'.")
            versions.append(version)
        before = [v.code for v in ReleaseService.target_versions(release)]
        db.session.query(ReleaseTargetVersion).filter(
            ReleaseTargetVersion.release_id == release.id
        ).delete()
        for version in versions:
            db.session.add(
                ReleaseTargetVersion(release_id=release.id, software_version_id=version.id)
            )
        AuditService.log(
            "Release",
            release.id,
            "RELEASE_TARGETS_SET",
            actor=actor,
            before={"software_versions": before},
            after={"software_versions": [v.code for v in versions]},
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
        # v3: scoped by surrogate id, not `code` — see
        # app/services/lookup_service.py module docstring for why a
        # Functional System Group's code alone is no longer unambiguous.
        group_id = scope.get("functional_system_group")
        if group_id:
            group = LookupService.get_by_id(LookupFunctionalSystemGroup, group_id)
            query = query.filter(StatusCode.functional_system_group_id == group.id)
        subgroup_id = scope.get("functional_subgroup")
        if subgroup_id:
            subgroup = LookupService.get_by_id(LookupFunctionalSubgroup, subgroup_id)
            query = query.filter(StatusCode.functional_subgroup_id == subgroup.id)

        targets = ReleaseService.target_versions(release)
        if targets:
            from app.services.software_version_service import SoftwareVersionService

            # Only revisions that apply to at least one of the Release's target versions.
            candidates = [
                r for r in query.all() if any(SoftwareVersionService.applies(r, v) for v in targets)
            ]
        else:
            candidates = query.all()

        claimed_elsewhere = {
            item.status_code_revision_id
            for item in db.session.query(ReleaseItem).filter(ReleaseItem.release_id != release_id)
        }
        return [r for r in candidates if r.id not in claimed_elsewhere]

    @staticmethod
    def set_items(release_id: int, revision_ids: list[int], actor) -> Release:
        """FR-042: pre-publish only. Sandbox/non-Approved revisions are
        rejected here (service layer) and, for sandbox specifically, also
        by trg_prevent_sandbox_release (defense in depth)."""
        require_roles(actor, "ADMINISTRATOR")
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
    def delete(release_id: int, actor) -> None:
        """BR-008: an Administrator may delete a Release only before it is
        published; its candidate revisions are untouched (still Approved)."""
        require_roles(actor, "ADMINISTRATOR")
        release = ReleaseService._repo.get_or_404(release_id)
        if release.status != "BUILDING":
            raise InvalidTransitionError("A published Release can never be deleted (BR-007).")
        AuditService.log(
            "Release",
            release.id,
            "RELEASE_DELETE",
            actor=actor,
            before={
                "name": release.name,
                "version_label": release.version_label,
                "status_code_revision_ids": sorted(
                    item.status_code_revision_id for item in release.items
                ),
            },
        )
        db.session.query(ExportJob).filter(ExportJob.release_id == release.id).update(
            {ExportJob.release_id: None}
        )
        db.session.query(ReleaseItem).filter(ReleaseItem.release_id == release.id).delete()
        db.session.delete(release)
        db.session.commit()

    @staticmethod
    def future_dated_items(release: Release, today: str | None = None) -> list[dict]:
        """I-27: items whose planned effective date is still in the future. A warning for
        the Administrator, never a block - the date is a plan, not a gate."""
        from datetime import UTC, datetime

        today = today or datetime.now(UTC).date().isoformat()
        return [
            {
                "revision_id": item.revision.id,
                "status_code_identifier": item.revision.status_code.status_code_identifier,
                "planned_effective_date": item.revision.planned_effective_date,
            }
            for item in release.items
            if item.revision.planned_effective_date and item.revision.planned_effective_date > today
        ]

    @staticmethod
    def publish(release_id: int, actor, reauth_password: str | None = None) -> Release:
        """FR-043: atomically transitions every included revision
        Approved -> Released, stamps effective_date, marks the Release
        immutable. FR-044/BR-007: a published Release can never be
        unpublished or have its items changed (trg_prevent_release_item_delete
        is defense in depth for the latter). I-17: needs the actor's password again."""
        require_roles(actor, "ADMINISTRATOR")
        AuthService.step_up(actor, reauth_password, "RELEASE_PUBLISH")
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

        # I-29: tell internal subscribers. Best effort - a failing webhook never undoes a publish.
        from app.services.integration_service import WebhookService

        WebhookService.dispatch(
            "release.published",
            {
                "release_id": release.id,
                "name": release.name,
                "version_label": release.version_label,
                "published_at": release.published_at,
                "item_count": len(release.items),
            },
        )
        return release

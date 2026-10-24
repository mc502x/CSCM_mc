"""The baseline of a Release (FR-173): every status code that is valid as of that Release.

A Release only *carries* the revisions that changed (release_item, BR-007), so exporting its
items gives a delta, not a manual. Technical Publications needs the complete set - roughly 900
codes for the main controller and 350 for the hub controller - so the baseline of Release N is
the latest revision of every code that was published in Release N or in any Release before it.
It is derived, not stored: a published Release is immutable, hence so is its baseline.

An unpublished Release has a baseline too (everything published so far plus its own items), the
preview of what its manual will contain."""

from sqlalchemy import and_, func, or_

from app.extensions import db
from app.models.lookup import (
    LookupFunctionalSystemGroup,
    LookupLanguage,
    LookupTurbinePlatform,
)
from app.models.release import Release, ReleaseItem
from app.models.status_code import (
    StatusCode,
    StatusCodeRevision,
    StatusCodeRevisionPlatform,
)
from app.repositories.status_code_repository import export_eager_options

# the hub controller (HC) and the main controller (MC) as people call them -> controller_type
CONTROLLERS = {"MC": "MAIN", "HC": "HUB"}


def validate_controller(controller: str | None) -> str | None:
    if controller in (None, ""):
        return None
    if controller not in CONTROLLERS:
        raise ValueError(f"Unknown controller '{controller}'. Use one of: MC, HC.")
    return controller


def validate_platform(platform: str | None) -> str | None:
    if platform in (None, ""):
        return None
    known = [row[0] for row in db.session.query(LookupTurbinePlatform.code).all()]
    if platform not in known:
        raise ValueError(f"Unknown platform '{platform}'. Use one of: {', '.join(sorted(known))}.")
    return platform


class BaselineService:
    @staticmethod
    def _member_filter(release: Release):
        """The Releases whose items make up the baseline of `release`."""
        if release.status == "PUBLISHED" and release.published_at:
            earlier_or_same = or_(
                Release.published_at < release.published_at,
                and_(Release.published_at == release.published_at, Release.id <= release.id),
            )
            return and_(Release.status == "PUBLISHED", earlier_or_same)
        return or_(Release.status == "PUBLISHED", Release.id == release.id)

    @staticmethod
    def _query(
        release: Release, entity, *, platform: str | None = None, controller: str | None = None
    ):
        """The baseline as a query over `entity` (the revisions themselves or just their ids)."""
        controller = validate_controller(controller)
        platform = validate_platform(platform)
        latest = (
            db.session.query(
                StatusCodeRevision.status_code_id.label("status_code_id"),
                func.max(StatusCodeRevision.revision_number).label("n"),
            )
            .join(ReleaseItem, ReleaseItem.status_code_revision_id == StatusCodeRevision.id)
            .join(Release, Release.id == ReleaseItem.release_id)
            .filter(BaselineService._member_filter(release))
            .group_by(StatusCodeRevision.status_code_id)
            .subquery()
        )
        query = (
            db.session.query(entity)
            .select_from(StatusCodeRevision)
            .join(
                latest,
                and_(
                    latest.c.status_code_id == StatusCodeRevision.status_code_id,
                    latest.c.n == StatusCodeRevision.revision_number,
                ),
            )
            .join(StatusCode, StatusCode.id == StatusCodeRevision.status_code_id)
            .filter(StatusCode.is_sandbox == 0, StatusCode.deleted_at.is_(None))
        )
        if controller:
            query = query.join(
                LookupFunctionalSystemGroup,
                LookupFunctionalSystemGroup.id == StatusCode.functional_system_group_id,
            ).filter(LookupFunctionalSystemGroup.controller_type == CONTROLLERS[controller])
        if platform:
            query = (
                query.join(
                    StatusCodeRevisionPlatform,
                    StatusCodeRevisionPlatform.status_code_revision_id == StatusCodeRevision.id,
                )
                .join(
                    LookupTurbinePlatform,
                    LookupTurbinePlatform.id == StatusCodeRevisionPlatform.turbine_platform_id,
                )
                .filter(LookupTurbinePlatform.code == platform)
            )
        return query

    @staticmethod
    def revisions(
        release: Release, *, platform: str | None = None, controller: str | None = None
    ) -> list[StatusCodeRevision]:
        """Latest revision per code as of `release`, optionally narrowed to one turbine platform
        (2XM / 3XM / 4XM) and / or one controller (MC / HC), ordered by status code."""
        return (
            BaselineService._query(
                release, StatusCodeRevision, platform=platform, controller=controller
            )
            .options(*export_eager_options())
            .order_by(StatusCode.status_code_identifier.asc())
            .all()
        )

    @staticmethod
    def revision_ids(release: Release) -> list[int]:
        return [row[0] for row in BaselineService._query(release, StatusCodeRevision.id).all()]

    @staticmethod
    def summary(release: Release) -> dict:
        """Counts for the Release page: the baseline, what this Release changed, and the split
        by controller and platform (plain counts - no revision is loaded)."""
        ids = BaselineService.revision_ids(release)
        by_controller = {"MC": 0, "HC": 0}
        by_platform: dict[str, int] = {}
        if ids:
            for kind, count in (
                db.session.query(LookupFunctionalSystemGroup.controller_type, func.count())
                .select_from(StatusCodeRevision)
                .join(StatusCode, StatusCode.id == StatusCodeRevision.status_code_id)
                .join(
                    LookupFunctionalSystemGroup,
                    LookupFunctionalSystemGroup.id == StatusCode.functional_system_group_id,
                )
                .filter(StatusCodeRevision.id.in_(ids))
                .group_by(LookupFunctionalSystemGroup.controller_type)
            ):
                by_controller["HC" if kind == "HUB" else "MC"] += count
            for code, count in (
                db.session.query(LookupTurbinePlatform.code, func.count())
                .select_from(StatusCodeRevisionPlatform)
                .join(
                    LookupTurbinePlatform,
                    LookupTurbinePlatform.id == StatusCodeRevisionPlatform.turbine_platform_id,
                )
                .filter(StatusCodeRevisionPlatform.status_code_revision_id.in_(ids))
                .group_by(LookupTurbinePlatform.code)
            ):
                by_platform[code] = count
        return {
            "baseline": len(ids),
            "in_release": len(release.items),
            "by_controller": by_controller,
            "by_platform": dict(sorted(by_platform.items())),
        }

    @staticmethod
    def readiness(release: Release) -> dict:
        """What is still missing before the documents of this Release are complete (FR-173):
        languages in which not every code of the baseline has an approved translation, and codes
        whose access levels nobody confirmed (they are left out of every audience file).
        Information for the Administrator, never a block."""
        from app.services.translation_service import TranslationService, source_language

        ids = BaselineService.revision_ids(release)
        source = source_language().code
        coverage = {}
        for language in db.session.query(LookupLanguage).order_by(LookupLanguage.sort_order):
            if language.code == source or not language.is_active:
                continue
            translated = len(TranslationService.approved_for(ids, language.code))
            coverage[language.code] = {"translated": translated, "of": len(ids)}
        unconfirmed = (
            [
                identifier or f"#{code_id}"
                for identifier, code_id in db.session.query(
                    StatusCode.status_code_identifier, StatusCode.id
                )
                .join(StatusCodeRevision, StatusCodeRevision.status_code_id == StatusCode.id)
                .filter(
                    StatusCodeRevision.id.in_(ids), StatusCodeRevision.admin_signoff_at.is_(None)
                )
                .order_by(StatusCode.status_code_identifier)
            ]
            if ids
            else []
        )
        return {
            "baseline": len(ids),
            "translation_coverage": coverage,
            "unconfirmed_access": {"count": len(unconfirmed), "examples": unconfirmed[:10]},
        }

"""Status Code search/filter/list (FR-060-FR-064) and current/open revision
resolution (BR-002/BR-003)."""

from sqlalchemy import or_

from app.extensions import db
from app.models.lookup import (
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
    LookupTurbinePlatform,
)
from app.models.status_code import StatusCode, StatusCodeRevision, StatusCodeRevisionPlatform
from app.repositories.base import BaseRepository

OPEN_LIFECYCLE_STATES = ("DRAFT", "REVIEW", "PENDING_APPROVAL")


class StatusCodeRepository(BaseRepository[StatusCode]):
    model = StatusCode

    def get_current_revision(self, status_code_id: int) -> StatusCodeRevision | None:
        return (
            db.session.query(StatusCodeRevision)
            .filter(
                StatusCodeRevision.status_code_id == status_code_id,
                StatusCodeRevision.is_current == 1,
            )
            .first()
        )

    def get_open_revision(self, status_code_id: int) -> StatusCodeRevision | None:
        return (
            db.session.query(StatusCodeRevision)
            .filter(
                StatusCodeRevision.status_code_id == status_code_id,
                StatusCodeRevision.lifecycle_status.in_(OPEN_LIFECYCLE_STATES),
            )
            .first()
        )

    def search_current_revisions(
        self,
        *,
        q: str | None = None,
        functional_system_group_code: str | None = None,
        functional_subgroup_code: str | None = None,
        turbine_platform_code: str | None = None,
        lifecycle_status: str | None = None,
        is_sandbox: bool = False,
        owner_id: int | None = None,
        visible_lifecycle_statuses: tuple[str, ...] | None = None,
        page: int = 1,
        page_size: int = 50,
        sort: str | None = None,
    ) -> tuple[list[StatusCodeRevision], int]:
        query = (
            db.session.query(StatusCodeRevision)
            .join(StatusCode, StatusCode.id == StatusCodeRevision.status_code_id)
            .filter(
                StatusCodeRevision.is_current == 1,
                StatusCode.is_sandbox == (1 if is_sandbox else 0),
            )
        )

        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    StatusCode.status_code_identifier.ilike(like),
                    StatusCodeRevision.title.ilike(like),
                    StatusCodeRevision.description.ilike(like),
                )
            )
        if functional_system_group_code:
            query = query.join(
                LookupFunctionalSystemGroup,
                LookupFunctionalSystemGroup.id == StatusCode.functional_system_group_id,
            ).filter(LookupFunctionalSystemGroup.code == functional_system_group_code)
        if functional_subgroup_code:
            query = query.join(
                LookupFunctionalSubgroup,
                LookupFunctionalSubgroup.id == StatusCode.functional_subgroup_id,
            ).filter(LookupFunctionalSubgroup.code == functional_subgroup_code)
        if turbine_platform_code:
            query = (
                query.join(
                    StatusCodeRevisionPlatform,
                    StatusCodeRevisionPlatform.status_code_revision_id == StatusCodeRevision.id,
                )
                .join(
                    LookupTurbinePlatform,
                    LookupTurbinePlatform.id == StatusCodeRevisionPlatform.turbine_platform_id,
                )
                .filter(LookupTurbinePlatform.code == turbine_platform_code)
            )
        if lifecycle_status:
            query = query.filter(StatusCodeRevision.lifecycle_status == lifecycle_status)
        if owner_id is not None:
            query = query.filter(StatusCodeRevision.owner_id == owner_id)
        if visible_lifecycle_statuses is not None:
            query = query.filter(
                StatusCodeRevision.lifecycle_status.in_(visible_lifecycle_statuses)
            )

        total = query.count()

        column = getattr(StatusCodeRevision, (sort or "").lstrip("-"), None)
        if column is not None:
            query = query.order_by(column.desc() if sort.startswith("-") else column.asc())  # type: ignore[union-attr]
        else:
            query = query.order_by(StatusCodeRevision.id.asc())

        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

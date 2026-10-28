"""Status Code search/filter/list (FR-060-FR-064) and current/open revision
resolution (BR-002/BR-003)."""

from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.models.lookup import LookupTurbinePlatform
from app.models.status_code import StatusCode, StatusCodeRevision, StatusCodeRevisionPlatform
from app.repositories import fts
from app.repositories.base import BaseRepository
from app.utils import split_multi

OPEN_LIFECYCLE_STATES = ("DRAFT", "REVIEW", "PENDING_APPROVAL")


_ACCESS_RELATIONSHIPS = (
    "development_access",
    "sales_access",
    "tcc_access",
    "service_access",
    "turbine_operator_package_access",
    "grid_operator_access",
    "service_partner_access",
    "customer_access",
)


def export_eager_options():
    """Loader options for everything `flatten_revision` reads, so exporting N
    revisions costs a handful of queries instead of ~13 per row. (The
    relationship attributes are looked up by name because the models declare
    them through cast(), which the type checker cannot see through.)"""
    revision: Any = StatusCodeRevision
    status_code: Any = StatusCode
    platform_link: Any = StatusCodeRevisionPlatform
    return (
        joinedload(revision.status_code).joinedload(status_code.functional_system_group),
        joinedload(revision.status_code).joinedload(status_code.functional_subgroup),
        selectinload(revision.platforms).joinedload(platform_link.turbine_platform),
        *(joinedload(getattr(revision, name)) for name in _ACCESS_RELATIONSHIPS),
        joinedload(revision.applies_from_version),
        joinedload(revision.applies_to_version),
    )


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

    def get_latest_revision_in_states(
        self, status_code_id: int, lifecycle_statuses: tuple[str, ...]
    ) -> StatusCodeRevision | None:
        """Highest-numbered revision whose state is in `lifecycle_statuses` —
        what a Viewer sees while a newer Draft of the same code is open (BR-009)."""
        return (
            db.session.query(StatusCodeRevision)
            .filter(
                StatusCodeRevision.status_code_id == status_code_id,
                StatusCodeRevision.lifecycle_status.in_(lifecycle_statuses),
            )
            .order_by(StatusCodeRevision.revision_number.desc())
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
        functional_system_group_id: int | None = None,
        functional_subgroup_id: int | None = None,
        turbine_platform_code: str | list[str] | None = None,
        lifecycle_status: str | list[str] | None = None,
        status_category: str | list[str] | None = None,
        is_sandbox: bool = False,
        owner_id: int | None = None,
        visible_lifecycle_statuses: tuple[str, ...] | None = None,
        page: int = 1,
        page_size: int = 50,
        sort: str | None = None,
        eager: bool = False,
    ) -> tuple[list[StatusCodeRevision], int]:
        use_fts = bool(q) and fts.available()
        # a filter may name several values (a comma-joined string or a list): any of them matches
        platform_codes = split_multi(turbine_platform_code)
        lifecycle_values = split_multi(lifecycle_status)
        category_values = split_multi(status_category)

        def build(expression: str | None):
            query = db.session.query(StatusCodeRevision).join(
                StatusCode, StatusCode.id == StatusCodeRevision.status_code_id
            )
            query = query.filter(StatusCode.is_sandbox == (1 if is_sandbox else 0))
            if visible_lifecycle_statuses is None:
                query = query.filter(StatusCodeRevision.is_current == 1)
            else:
                # Restricted audience (Viewer, BR-009): per code, the latest revision they
                # may see - NOT the current one, which may be an open Draft they must not
                # see while the previously Released revision stays authoritative.
                latest = (
                    db.session.query(
                        StatusCodeRevision.status_code_id.label("sc_id"),
                        func.max(StatusCodeRevision.revision_number).label("n"),
                    )
                    .filter(StatusCodeRevision.lifecycle_status.in_(visible_lifecycle_statuses))
                    .group_by(StatusCodeRevision.status_code_id)
                    .subquery()
                )
                query = query.join(
                    latest,
                    (latest.c.sc_id == StatusCodeRevision.status_code_id)
                    & (latest.c.n == StatusCodeRevision.revision_number),
                )

            ranking = None
            if q:
                like = f"%{q}%"
                substring = or_(
                    StatusCode.status_code_identifier.ilike(like),
                    StatusCodeRevision.title.ilike(like),
                    StatusCodeRevision.description.ilike(like),
                )
                if expression:
                    # I-31: substring matches stay (so "verter" still finds "converter"); the
                    # FTS index adds relevance order and typo tolerance on top.
                    ranking = fts.ranked(expression)
                    query = query.outerjoin(ranking, ranking.c.rid == StatusCodeRevision.id)
                    query = query.filter(or_(substring, ranking.c.rid.isnot(None)))
                else:
                    query = query.filter(substring)
            # v3: filtered by surrogate id, not `code` - a Functional System
            # Group's code is no longer unique (WTUR/WROT are each reused for a
            # second, numerically distinct Hub Controller group), so filtering
            # by bare code would silently blend two unrelated ranges together.
            if functional_system_group_id is not None:
                query = query.filter(
                    StatusCode.functional_system_group_id == functional_system_group_id
                )
            if functional_subgroup_id is not None:
                query = query.filter(StatusCode.functional_subgroup_id == functional_subgroup_id)
            if platform_codes:
                # a subquery, not a join: a revision on two chosen platforms is still one row
                on_platform = (
                    db.session.query(StatusCodeRevisionPlatform.status_code_revision_id)
                    .join(
                        LookupTurbinePlatform,
                        LookupTurbinePlatform.id == StatusCodeRevisionPlatform.turbine_platform_id,
                    )
                    .filter(LookupTurbinePlatform.code.in_(platform_codes))
                )
                query = query.filter(StatusCodeRevision.id.in_(on_platform))
            if lifecycle_values:
                query = query.filter(StatusCodeRevision.lifecycle_status.in_(lifecycle_values))
            if category_values:
                query = query.filter(StatusCodeRevision.status_category.in_(category_values))
            if owner_id is not None:
                query = query.filter(StatusCodeRevision.owner_id == owner_id)
            return query, ranking

        expression = fts.match_expression(q) if use_fts and q else None
        query, ranking = build(expression)
        total = query.count()
        if use_fts and q and total == 0:
            fuzzy = fts.fuzzy_expression(q)
            if fuzzy and fuzzy != expression:
                query, ranking = build(fuzzy)
                total = query.count()

        column = getattr(StatusCodeRevision, (sort or "").lstrip("-"), None)
        if column is not None:
            query = query.order_by(column.desc() if sort.startswith("-") else column.asc())  # type: ignore[union-attr]
        elif ranking is not None:
            query = query.order_by(
                ranking.c.score.is_(None), ranking.c.score, StatusCodeRevision.id
            )
        else:
            query = query.order_by(StatusCodeRevision.id.asc())

        if eager:
            query = query.options(*export_eager_options())
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def list_latest_released(
        self,
        *,
        functional_system_group_id: int | None = None,
        functional_subgroup_id: int | None = None,
        turbine_platform_code: str | None = None,
    ) -> list[StatusCodeRevision]:
        """The highest-numbered RELEASED revision of each non-sandbox code
        (FR-045: "the current set of all Released status codes")."""
        latest = (
            db.session.query(
                StatusCodeRevision.status_code_id,
                func.max(StatusCodeRevision.revision_number).label("n"),
            )
            .filter(StatusCodeRevision.lifecycle_status == "RELEASED")
            .group_by(StatusCodeRevision.status_code_id)
            .subquery()
        )
        query = (
            db.session.query(StatusCodeRevision)
            .join(
                latest,
                (latest.c.status_code_id == StatusCodeRevision.status_code_id)
                & (latest.c.n == StatusCodeRevision.revision_number),
            )
            .join(StatusCode, StatusCode.id == StatusCodeRevision.status_code_id)
            .filter(StatusCode.is_sandbox == 0)
        )
        if functional_system_group_id is not None:
            query = query.filter(
                StatusCode.functional_system_group_id == functional_system_group_id
            )
        if functional_subgroup_id is not None:
            query = query.filter(StatusCode.functional_subgroup_id == functional_subgroup_id)
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
        return (
            query.options(*export_eager_options())
            .order_by(StatusCode.status_code_identifier.asc())
            .all()
        )

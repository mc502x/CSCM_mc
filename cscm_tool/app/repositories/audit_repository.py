from app.extensions import db
from app.models.audit import AuditLogEntry
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLogEntry]):
    model = AuditLogEntry

    def search(
        self,
        *,
        entity_type: str | None = None,
        entity_id: int | None = None,
        actor_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLogEntry], int]:
        query = db.session.query(AuditLogEntry)
        if entity_type:
            query = query.filter(AuditLogEntry.entity_type == entity_type)
        if entity_id is not None:
            query = query.filter(AuditLogEntry.entity_id == entity_id)
        if actor_id is not None:
            query = query.filter(AuditLogEntry.actor_id == actor_id)
        if date_from:
            query = query.filter(AuditLogEntry.occurred_at >= date_from)
        if date_to:
            query = query.filter(AuditLogEntry.occurred_at <= date_to)

        total = query.count()
        items = (
            query.order_by(AuditLogEntry.occurred_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

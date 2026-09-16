from app.models.audit import AuditLogEntry
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[AuditLogEntry]):
    model = AuditLogEntry

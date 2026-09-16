"""Central audit-log writer used by every other service. See
docs/12-audit-compliance.md §2 for the action catalogue and FR-070–FR-073.
No endpoint ever updates or deletes an audit_log_entry row (AUD-072)."""

import json
import uuid
from typing import Any

from flask import g, has_request_context, request

from app.models.audit import AuditLogEntry
from app.repositories.audit_repository import AuditRepository
from app.utils import utcnow_iso


class AuditService:
    _repo = AuditRepository()

    @staticmethod
    def log(
        entity_type: str,
        entity_id: int,
        action: str,
        actor: Any = None,
        before: dict | None = None,
        after: dict | None = None,
    ) -> AuditLogEntry:
        """Writes one immutable audit_log_entry row. `actor` may be a User,
        an AuthenticatedUser, or None (system-initiated action)."""
        entry = AuditLogEntry(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_id=getattr(actor, "id", None),
            occurred_at=utcnow_iso(),
            before_value=json.dumps(before, default=str) if before is not None else None,
            after_value=json.dumps(after, default=str) if after is not None else None,
            ip_address=request.remote_addr if has_request_context() else None,
            request_id=_current_request_id(),
        )
        AuditService._repo.add(entry)
        return entry


def _current_request_id() -> str:
    if has_request_context():
        return str(g.get("request_id", uuid.uuid4()))
    return str(uuid.uuid4())

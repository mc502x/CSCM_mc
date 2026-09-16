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
    def search(
        actor_user,
        *,
        entity_type: str | None = None,
        entity_id: int | None = None,
        actor_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLogEntry], int]:
        """FR-071: Administrator has full access. Reviewer/Chief Engineer
        get the "scoped" subset per 11-security-architecture.md §3 — this
        codebase reads that as their own actions only (actor_id forced to
        themselves), since the docs do not further define the scope and
        this is the narrowest, most defensible reading: they can always see
        what they personally did, never another actor's entries."""
        if actor_user.role_code in ("REVIEWER", "CHIEF_ENGINEER"):
            actor_id = actor_user.id
        return AuditService._repo.search(
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

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

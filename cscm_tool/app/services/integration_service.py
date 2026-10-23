"""Machine access for internal consumers (I-29): scoped API tokens, the "changes since"
feed, and webhooks on Release publish. Everything stays inside the network
(docs/11-security-architecture.md §12).

* **Tokens** are random, stored only as a SHA-256 hash, shown once, expiring (max 365 days),
  revocable, and *scoped*: a token can only call the GET endpoints that declare its scope
  (`allow_token` in app/auth/decorators.py), and then acts with the least privilege of all - a
  Viewer, i.e. Released data only (BR-009). A token can never write.
* **Change feed** - `GET /changes?since_id=...`: releases, deprecations, reinstatements and
  archivals in audit order, with an ETag, so a consumer polls cheaply.
* **Webhooks** - POSTed on `release.published` with an HMAC-SHA-256 signature
  (`X-CSCM-Signature: sha256=...`). Targets must resolve to loopback/private addresses, redirects
  are not followed, a failure is recorded and never affects the publish."""

import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from flask import current_app

from app.domain.authz import require_roles
from app.domain.errors import NotFoundError
from app.extensions import db
from app.models.audit import AuditLogEntry
from app.models.operations import ApiToken, Webhook, WebhookDelivery
from app.models.release import ReleaseItem
from app.models.status_code import StatusCodeRevision
from app.services.audit_service import AuditService
from app.utils import format_iso, parse_iso, utcnow_iso

TOKEN_SCOPES = {
    "catalogue:read": "Released catalogue, releases and exports (read-only)",
    "changes:read": "The change feed (read-only)",
}
MAX_TOKEN_DAYS = 365
WEBHOOK_EVENTS = ("release.published",)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class ApiTokenService:
    @staticmethod
    def create(actor, name: str, scopes: list[str], expires_in_days: int = 90):
        """Returns (row, plaintext). The plaintext is not recoverable afterwards."""
        require_roles(actor, "ADMINISTRATOR")
        name = (name or "").strip()
        if not 1 <= len(name) <= 80:
            raise ValueError("A token needs a name of 1-80 characters.")
        scopes = sorted(set(scopes or []))
        unknown = [s for s in scopes if s not in TOKEN_SCOPES]
        if not scopes or unknown:
            raise ValueError(
                f"Choose at least one valid scope ({', '.join(TOKEN_SCOPES)}); unknown: {unknown}"
            )
        if not 1 <= int(expires_in_days) <= MAX_TOKEN_DAYS:
            raise ValueError(f"expires_in_days must be between 1 and {MAX_TOKEN_DAYS}.")
        plaintext = "cscm_" + secrets.token_urlsafe(32)
        row = ApiToken(
            user_id=actor.id,
            name=name,
            token_prefix=plaintext[:12],
            token_hash=_hash(plaintext),
            scopes=" ".join(scopes),
            expires_at=format_iso(datetime.now(UTC) + timedelta(days=int(expires_in_days))),
            created_at=utcnow_iso(),
        )
        db.session.add(row)
        db.session.flush()
        AuditService.log(
            "ApiToken",
            row.id,
            "API_TOKEN_CREATE",
            actor=actor,
            after={"name": name, "scopes": scopes, "expires_at": row.expires_at},
        )
        db.session.commit()
        return row, plaintext

    @staticmethod
    def list_all(actor) -> list[ApiToken]:
        require_roles(actor, "ADMINISTRATOR")
        return db.session.query(ApiToken).order_by(ApiToken.id.desc()).all()

    @staticmethod
    def revoke(token_id: int, actor) -> ApiToken:
        require_roles(actor, "ADMINISTRATOR")
        row = db.session.get(ApiToken, token_id)
        if row is None:
            raise NotFoundError("Token not found")
        if row.revoked_at is None:
            row.revoked_at = utcnow_iso()
            AuditService.log("ApiToken", row.id, "API_TOKEN_REVOKE", actor=actor)
            db.session.commit()
        return row

    @staticmethod
    def authenticate(plaintext: str, required_scope: str):
        """The principal for a valid, unexpired, unrevoked token holding `required_scope`
        (None otherwise). Always a Viewer-level identity, whoever owns the token."""
        from app.auth.providers import AuthenticatedUser
        from app.models.user import User

        row = db.session.query(ApiToken).filter(ApiToken.token_hash == _hash(plaintext)).first()
        if row is None or row.revoked_at is not None:
            return None
        if parse_iso(row.expires_at) <= datetime.now(UTC):
            return None
        if required_scope not in row.scopes.split():
            return None
        owner = db.session.get(User, row.user_id)
        if owner is None or not owner.is_active:
            return None
        now = utcnow_iso()
        if row.last_used_at is None or parse_iso(row.last_used_at) < datetime.now(UTC) - timedelta(
            minutes=1
        ):
            row.last_used_at = now
            db.session.commit()
        return AuthenticatedUser(
            id=owner.id,
            username=owner.username,
            email=owner.email,
            full_name=f"{owner.full_name} (API token {row.token_prefix}...)",
            role_code="VIEWER",
        )


# ------------------------------------------------------------------ change feed
_FEED_EVENTS = {
    "RELEASE_PUBLISH": "code.released",
    "DEPRECATE": "code.deprecated",
    "REINSTATE": "code.reinstated",
    "ARCHIVE": "code.archived",
}


class ChangeFeedService:
    @staticmethod
    def since(since_id: int = 0, limit: int = 100) -> dict:
        limit = max(1, min(int(limit), 500))
        entries = (
            db.session.query(AuditLogEntry)
            .filter(
                AuditLogEntry.id > since_id,
                AuditLogEntry.entity_type == "StatusCodeRevision",
                AuditLogEntry.action.in_(tuple(_FEED_EVENTS)),
            )
            .order_by(AuditLogEntry.id)
            .limit(limit + 1)
            .all()
        )
        has_more = len(entries) > limit
        entries = entries[:limit]
        items = []
        for entry in entries:
            revision = db.session.get(StatusCodeRevision, entry.entity_id)
            if revision is None or revision.status_code.is_sandbox:
                continue
            release = None
            if entry.action == "RELEASE_PUBLISH":
                item = (
                    db.session.query(ReleaseItem)
                    .filter(ReleaseItem.status_code_revision_id == revision.id)
                    .first()
                )
                if item is not None:
                    release = {
                        "id": item.release.id,
                        "name": item.release.name,
                        "version_label": item.release.version_label,
                    }
            items.append(
                {
                    "id": entry.id,
                    "event": _FEED_EVENTS[entry.action],
                    "occurred_at": entry.occurred_at,
                    "status_code_identifier": revision.status_code.status_code_identifier,
                    "title": revision.title,
                    "revision_number": revision.revision_number,
                    "release": release,
                }
            )
        next_id = entries[-1].id if entries else since_id
        return {"items": items, "next_since_id": next_id, "has_more": has_more}


# ------------------------------------------------------------------ webhooks
def _is_private_host(host: str) -> bool:
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    addresses = {info[4][0] for info in infos}
    if not addresses:
        return False
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%")[0])
        if not (ip.is_private or ip.is_loopback or ip.is_link_local):
            return False
    return True


def validate_webhook_url(url: str) -> str:
    parsed = urlparse(url or "")
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("The webhook URL must be an http(s) URL.")
    if not current_app.config.get("WEBHOOK_ALLOW_PUBLIC_TARGETS") and not _is_private_host(
        parsed.hostname
    ):
        raise ValueError(
            "The webhook target must be on the internal network (a private or loopback address)."
        )
    return url


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # a redirect could leave the internal network
        return None


class WebhookService:
    @staticmethod
    def create(actor, name: str, url: str, events: list[str] | None = None):
        """Returns (row, secret); the secret is shown once."""
        require_roles(actor, "ADMINISTRATOR")
        name = (name or "").strip()
        if not 1 <= len(name) <= 80:
            raise ValueError("A webhook needs a name of 1-80 characters.")
        events = events or list(WEBHOOK_EVENTS)
        if any(e not in WEBHOOK_EVENTS for e in events):
            raise ValueError(f"Supported events: {', '.join(WEBHOOK_EVENTS)}")
        validate_webhook_url(url)
        secret = secrets.token_hex(24)
        row = Webhook(
            name=name,
            url=url,
            secret=secret,
            events=",".join(events),
            created_by=actor.id,
            created_at=utcnow_iso(),
        )
        db.session.add(row)
        db.session.flush()
        AuditService.log(
            "Webhook",
            row.id,
            "WEBHOOK_CREATE",
            actor=actor,
            after={"name": name, "url": url, "events": events},
        )
        db.session.commit()
        return row, secret

    @staticmethod
    def list_all(actor) -> list[Webhook]:
        require_roles(actor, "ADMINISTRATOR")
        return db.session.query(Webhook).order_by(Webhook.id).all()

    @staticmethod
    def set_active(webhook_id: int, active: bool, actor) -> Webhook:
        require_roles(actor, "ADMINISTRATOR")
        row = db.session.get(Webhook, webhook_id)
        if row is None:
            raise NotFoundError("Webhook not found")
        row.is_active = 1 if active else 0
        AuditService.log(
            "Webhook", row.id, "WEBHOOK_UPDATE", actor=actor, after={"is_active": bool(active)}
        )
        db.session.commit()
        return row

    @staticmethod
    def deliveries(webhook_id: int, actor, limit: int = 50) -> list[WebhookDelivery]:
        require_roles(actor, "ADMINISTRATOR")
        return (
            db.session.query(WebhookDelivery)
            .filter(WebhookDelivery.webhook_id == webhook_id)
            .order_by(WebhookDelivery.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def dispatch(event: str, payload: dict) -> int:
        """Deliver `event` to every active subscriber; never raises. Returns deliveries made."""
        delivered = 0
        try:
            hooks = (
                db.session.query(Webhook)
                .filter(Webhook.is_active == 1, Webhook.events.like(f"%{event}%"))
                .all()
            )
            for hook in hooks:
                WebhookService._deliver(hook, event, payload)
                delivered += 1
        except Exception:  # noqa: BLE001  (a webhook problem must never break the caller)
            current_app.logger.exception("webhook dispatch failed")
            db.session.rollback()
        return delivered

    @staticmethod
    def _deliver(hook: Webhook, event: str, payload: dict) -> None:
        body = json.dumps({"event": event, "data": payload}, sort_keys=True).encode("utf-8")
        signature = hmac.new(hook.secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        status: int | None = None
        error: str | None = None
        try:
            validate_webhook_url(hook.url)
            request = urllib.request.Request(  # noqa: S310  # nosec B310 - scheme and host validated above
                hook.url,
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "X-CSCM-Event": event,
                    "X-CSCM-Signature": f"sha256={signature}",
                },
            )
            opener = urllib.request.build_opener(_NoRedirect)
            with opener.open(
                request, timeout=current_app.config["WEBHOOK_TIMEOUT_SECONDS"]
            ) as response:  # noqa: S310  # nosec B310
                status = response.status
        except urllib.error.HTTPError as exc:
            status, error = exc.code, f"HTTP {exc.code}"
        except (urllib.error.URLError, OSError, ValueError) as exc:
            error = str(exc)[:300]
        ok = status is not None and 200 <= status < 300
        db.session.add(
            WebhookDelivery(
                webhook_id=hook.id,
                event=event,
                payload=body.decode("utf-8"),
                http_status=status,
                ok=1 if ok else 0,
                error=error,
                delivered_at=utcnow_iso(),
            )
        )
        hook.last_delivery_at = utcnow_iso()
        hook.last_status = "ok" if ok else (error or f"HTTP {status}")
        db.session.commit()

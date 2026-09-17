"""Login/logout/session lifecycle. Implements FR-001-FR-004 and SEC-001-
SEC-004. Lockout/rate-limit bookkeeping lives here (not in AuthProvider)
because it is provider-agnostic account-management policy that must keep
applying once an on-premises AD/ADFS provider replaces
SessionPasswordAuthProvider (08-system-architecture.md §7)."""

import hashlib
from datetime import UTC, datetime, timedelta

from flask import session

from app.auth.providers import AuthenticatedUser, SessionPasswordAuthProvider
from app.auth.rate_limit import check_and_record_login_attempt
from app.domain.errors import AccountLockedError, InvalidCredentialsError, RateLimitedError
from app.extensions import db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.utils import format_iso, parse_iso, utcnow_iso

FAILED_LOGIN_LOCKOUT_THRESHOLD = 5
FAILED_LOGIN_LOCKOUT_MINUTES = 15

_auth_provider = SessionPasswordAuthProvider()


class AuthService:
    _repo = UserRepository()

    @staticmethod
    def login(username: str, password: str, ip_address: str | None) -> AuthenticatedUser:
        if not check_and_record_login_attempt(ip_address or "unknown", username):
            raise RateLimitedError("Too many login attempts; try again later.")

        user = AuthService._repo.get_by_identifier(username)

        if user is not None and user.locked_until is not None:
            if parse_iso(user.locked_until) > datetime.now(UTC):
                AuditService.log("User", user.id, "LOGIN_FAILURE", actor=user)
                db.session.commit()
                raise AccountLockedError("Account is locked. Try again later.")
            user.locked_until = None  # lock has expired; allow a fresh attempt below

        if user is None or not user.is_active:
            AuditService.log("User", user.id if user else 0, "LOGIN_FAILURE", actor=user)
            db.session.commit()
            raise InvalidCredentialsError("Invalid username or password.")

        authenticated = _auth_provider.authenticate({"user": user, "password": password})

        if authenticated is None:
            user.failed_login_count += 1
            locked = user.failed_login_count >= FAILED_LOGIN_LOCKOUT_THRESHOLD
            if locked:
                user.locked_until = format_iso(
                    datetime.now(UTC) + timedelta(minutes=FAILED_LOGIN_LOCKOUT_MINUTES)
                )
            AuditService.log(
                "User", user.id, "ACCOUNT_LOCKED" if locked else "LOGIN_FAILURE", actor=user
            )
            db.session.commit()
            if locked:
                raise AccountLockedError("Account is locked. Try again later.")
            raise InvalidCredentialsError("Invalid username or password.")

        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = utcnow_iso()
        AuditService.log("User", user.id, "LOGIN_SUCCESS", actor=user)
        db.session.commit()

        _establish_session(user)
        return authenticated

    @staticmethod
    def logout(actor_id: int | None) -> None:
        """Clears the signed session cookie immediately (FR-003). There is no
        server-side session row to revoke separately — see app/auth/decorators.py
        for how deactivation/forced-reset are made to take effect immediately
        despite the client-side session store."""
        if actor_id is not None:
            AuditService.log("User", actor_id, "LOGOUT", actor=None)
            db.session.commit()
        session.clear()


def _establish_session(user: User) -> None:
    session.clear()
    session.permanent = True
    now_iso = utcnow_iso()
    session["user_id"] = user.id
    session["login_at"] = now_iso
    session["last_activity_at"] = now_iso
    # A fingerprint of password_hash (not the hash itself) so a forced
    # password reset invalidates every existing session on its very next
    # request, without needing a separate server-side session table.
    session["pw_fingerprint"] = hashlib.sha256(user.password_hash.encode()).hexdigest()

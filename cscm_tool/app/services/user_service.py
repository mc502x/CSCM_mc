"""User & RBAC administration. FR-010-FR-014, SEC-012, US-009/US-011/US-012."""

import re

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import text

from app.auth.password import hash_password, validate_password_policy, verify_password
from app.auth.roles import OWNER_ASSIGNABLE, may_change_role
from app.domain.authz import require_roles
from app.domain.errors import (
    ForbiddenError,
    InvalidTransitionError,
    LastAdministratorError,
    PasswordPolicyError,
)
from app.extensions import db
from app.models.lookup import Role
from app.models.user import User, UserPasswordHistory
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.utils import utcnow_iso

PASSWORD_HISTORY_DEPTH = 5  # 11-security-architecture.md §4

EMAIL_FIXED = (
    "The e-mail address cannot be changed: it identifies the person, also for the Windows sign-in "
    "(FR-162). Deactivate the account or, if it was never used, delete it and create it again."
)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalise_email(value: str) -> str:
    """The form an address is stored in: trimmed and lower-case (a Windows user name is not case
    sensitive, so the match with it must not be either)."""
    email = (value or "").strip().lower()
    if not _EMAIL_RE.match(email):
        raise ValueError("Enter a valid e-mail address (name@domain).")
    return email


# Rows that belong to the user alone and go with the account (BR-025). Anything else that points at
# the user - a change request, a review, a release, an audit entry - is history that must stay
# attributable, so a user with such rows is deactivated, never deleted.
OWN_TABLES: tuple[tuple[str, str], ...] = (
    ("user_engineering_domain", "user_id"),
    ("user_password_history", "user_id"),
    ("saved_search", "user_id"),
    ("notification", "user_id"),
)


class UserService:
    """Every public method enforces FR-012 (last active Administrator
    cannot be deactivated or reassigned away from ADMINISTRATOR) and writes
    the corresponding docs/12-audit-compliance.md §2 action code."""

    _repo = UserRepository()

    @staticmethod
    def list_users() -> list[User]:
        return UserService._repo.list()

    @staticmethod
    def get_user(user_id: int) -> User:
        return UserService._repo.get_or_404(user_id)

    @staticmethod
    def create_user(
        *,
        username: str,
        email: str,
        full_name: str,
        role_code: str,
        password: str,
        engineering_domain_codes: list[str] | None = None,
        actor,
    ) -> User:
        violations = validate_password_policy(password)
        if violations:
            raise PasswordPolicyError(violations)

        email = normalise_email(email)
        taken = db.session.execute(
            text("SELECT 1 FROM user WHERE lower(email) = :e OR lower(username) = :u"),
            {"e": email, "u": username.strip().lower()},
        ).first()
        if taken is not None:
            raise ValueError("That e-mail address or username is already in use.")

        role = (
            db.session.query(Role).filter(Role.code == role_code).first()
            if isinstance(role_code, str)
            else None
        )
        if role is None:
            raise ValueError(f"Unknown role code: {role_code}")

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role_id=role.id,
            created_at=utcnow_iso(),
        )
        UserService._repo.add(user)
        db.session.flush()  # assigns user.id before setting domains/audit

        UserService._repo.set_engineering_domains(user, engineering_domain_codes or [])

        AuditService.log(
            "User",
            user.id,
            "USER_CREATE",
            actor=actor,
            after={
                "username": username,
                "email": email,
                "role": role_code,
                "engineering_domains": sorted(engineering_domain_codes or []),
            },
        )
        db.session.commit()
        return user

    @staticmethod
    def update_user(
        user_id: int,
        *,
        full_name: str | None = None,
        role_code: str | None = None,
        engineering_domain_codes: list[str] | None = None,
        is_active: bool | None = None,
        email: str | None = None,
        actor,
    ) -> User:
        require_roles(actor, "ADMINISTRATOR", "STCD_OWNER")
        if email is not None:
            raise ValueError(EMAIL_FIXED)
        if actor.role_code == "STCD_OWNER" and (
            full_name is not None or engineering_domain_codes is not None or is_active is not None
        ):
            # BR-024: the owner changes roles, nothing else about a person.
            raise ForbiddenError(
                "BR-024: an StCd Owner may only change the role of a user, between "
                + ", ".join(OWNER_ASSIGNABLE)
                + "."
            )
        user = UserService._repo.get_or_404(user_id)

        if full_name is not None and full_name != user.full_name:
            before_name = user.full_name
            user.full_name = full_name
            AuditService.log(
                "User",
                user.id,
                "USER_UPDATE",
                actor=actor,
                before={"full_name": before_name},
                after={"full_name": full_name},
            )

        if role_code is not None and role_code != user.role.code:
            role = (
                db.session.query(Role).filter(Role.code == role_code).first()
                if isinstance(role_code, str)
                else None
            )
            if role is None:
                raise ValueError(f"Unknown role code: {role_code}")
            if not may_change_role(actor.role_code, user.role.code, role_code):
                raise ForbiddenError(
                    f"BR-024: a role change from {user.role.code} to {role_code} needs an "
                    "Administrator; an StCd Owner may only move users between "
                    + ", ".join(OWNER_ASSIGNABLE)
                    + "."
                )
            if (
                user.role.code == "ADMINISTRATOR"
                and UserService._repo.count_active_administrators(exclude_user_id=user.id) == 0
            ):
                raise LastAdministratorError(
                    "Cannot change the role of the last active Administrator."
                )
            before_role = user.role.code
            user.role = role
            AuditService.log(
                "User",
                user.id,
                "ROLE_CHANGE",
                actor=actor,
                before={"role": before_role},
                after={"role": role_code},
            )

        if engineering_domain_codes is not None:
            before_domains = sorted(ued.engineering_domain.code for ued in user.engineering_domains)
            after_domains = sorted(engineering_domain_codes)
            if before_domains != after_domains:
                UserService._repo.set_engineering_domains(user, engineering_domain_codes)
                AuditService.log(
                    "User",
                    user.id,
                    "DOMAIN_TAG_CHANGE",
                    actor=actor,
                    before={"engineering_domains": before_domains},
                    after={"engineering_domains": after_domains},
                )

        if is_active is not None and bool(is_active) != bool(user.is_active):
            if not is_active:
                if (
                    user.role.code == "ADMINISTRATOR"
                    and UserService._repo.count_active_administrators(exclude_user_id=user.id) == 0
                ):
                    raise LastAdministratorError("Cannot deactivate the last active Administrator.")
            before_active = bool(user.is_active)
            user.is_active = 1 if is_active else 0
            AuditService.log(
                "User",
                user.id,
                "USER_DEACTIVATE" if not is_active else "USER_UPDATE",
                actor=actor,
                before={"is_active": before_active},
                after={"is_active": bool(is_active)},
            )

        db.session.commit()
        return user

    @staticmethod
    def usage(user_id: int) -> dict:
        """What the user has done in the tool: the rows of every other table that point at them.
        `deletable` is true only when there is none (BR-025)."""
        user = UserService._repo.get_or_404(user_id)
        own = {t for t, _ in OWN_TABLES}
        references: dict[str, int] = {}
        inspector = sa_inspect(db.engine)
        for table in inspector.get_table_names():
            if table in own or table.startswith(("sqlite_", "status_code_fts", "alembic_")):
                continue
            for fk in inspector.get_foreign_keys(table):
                if fk["referred_table"] != "user":
                    continue
                for column in fk["constrained_columns"]:
                    count = db.session.execute(
                        text(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" = :i'),  # nosec B608
                        {"i": user.id},
                    ).scalar()
                    if count:
                        references[f"{table}.{column}"] = int(count)
        return {
            "user_id": user.id,
            "references": references,
            "reference_total": sum(references.values()),
            "deletable": not references,
        }

    @staticmethod
    def delete_user(user_id: int, actor, reauth_password: str | None = None) -> None:
        """Removes an account that was never used (BR-025). Only an Administrator, never the own
        account, never the last active Administrator, and only with the Administrator's password
        again (SEC-026). A user with history is refused with a pointer to deactivation."""
        require_roles(actor, "ADMINISTRATOR")
        user = UserService._repo.get_or_404(user_id)
        if user.id == actor.id:
            raise ForbiddenError("You cannot delete your own account.")
        AuthService.step_up(actor, reauth_password, "USER_DELETE")
        if (
            user.role.code == "ADMINISTRATOR"
            and user.is_active
            and UserService._repo.count_active_administrators(exclude_user_id=user.id) == 0
        ):
            raise LastAdministratorError("Cannot delete the last active Administrator.")
        report = UserService.usage(user.id)
        if not report["deletable"]:
            parts = ", ".join(f"{n} in {k}" for k, n in sorted(report["references"].items())[:4])
            raise InvalidTransitionError(
                f"{user.username} has history in the tool ({parts}) and cannot be deleted without "
                "breaking the audit trail (BR-025). Deactivate the account instead."
            )
        snapshot = {
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.code,
            "engineering_domains": sorted(
                d.engineering_domain.code for d in user.engineering_domains
            ),
        }
        for table, column in OWN_TABLES:
            statement = (
                f'DELETE FROM "{table}" WHERE "{column}" = :i'  # nosec B608 - fixed OWN_TABLES
            )
            db.session.execute(text(statement), {"i": user.id})
        db.session.expire(user)
        db.session.execute(text("DELETE FROM user WHERE id = :i"), {"i": user.id})
        AuditService.log("User", user_id, "USER_DELETE", actor=actor, before=snapshot)
        db.session.commit()

    @staticmethod
    def _check_not_reused(user: User, new_password: str) -> list[str]:
        """Policy: a new password may not repeat any of the last
        PASSWORD_HISTORY_DEPTH passwords (the current one plus the newest retired ones)."""
        retired = (
            db.session.query(UserPasswordHistory)
            .filter(UserPasswordHistory.user_id == user.id)
            .order_by(UserPasswordHistory.id.desc())
            .limit(PASSWORD_HISTORY_DEPTH - 1)
            .all()
        )
        previous = [user.password_hash, *(row.password_hash for row in retired)]
        if any(verify_password(new_password, h) for h in previous):
            return [f"Password must differ from your last {PASSWORD_HISTORY_DEPTH} passwords."]
        return []

    @staticmethod
    def _replace_password(user: User, new_password: str) -> None:
        """Retire the current hash into the history, then store the new one."""
        db.session.add(
            UserPasswordHistory(
                user_id=user.id, password_hash=user.password_hash, retired_at=utcnow_iso()
            )
        )
        user.password_hash = hash_password(new_password)

    @staticmethod
    def change_own_password(user: User, current_password: str, new_password: str) -> None:
        """FR-013: self password change, own password policy enforced."""
        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect.")
        violations = validate_password_policy(new_password) + UserService._check_not_reused(
            user, new_password
        )
        if violations:
            raise PasswordPolicyError(violations)
        UserService._replace_password(user, new_password)
        AuditService.log("User", user.id, "PASSWORD_CHANGE", actor=user)
        db.session.commit()

    @staticmethod
    def force_reset_password(user_id: int, new_password: str, actor) -> None:
        """FR-014: Administrator-forced reset for any user."""
        require_roles(actor, "ADMINISTRATOR")
        user = UserService._repo.get_or_404(user_id)
        violations = validate_password_policy(new_password) + UserService._check_not_reused(
            user, new_password
        )
        if violations:
            raise PasswordPolicyError(violations)
        UserService._replace_password(user, new_password)
        user.failed_login_count = 0
        user.locked_until = None
        AuditService.log("User", user.id, "PASSWORD_RESET", actor=actor)
        db.session.commit()

"""User & RBAC administration. FR-010-FR-014, SEC-012, US-009/US-011/US-012."""

from app.auth.password import hash_password, validate_password_policy, verify_password
from app.domain.errors import LastAdministratorError, PasswordPolicyError
from app.extensions import db
from app.models.lookup import Role
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.audit_service import AuditService
from app.utils import utcnow_iso


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

        role = db.session.query(Role).filter(Role.code == role_code).first()
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
        actor,
    ) -> User:
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
            role = db.session.query(Role).filter(Role.code == role_code).first()
            if role is None:
                raise ValueError(f"Unknown role code: {role_code}")
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
    def change_own_password(user: User, current_password: str, new_password: str) -> None:
        """FR-013: self password change, own password policy enforced."""
        if not verify_password(current_password, user.password_hash):
            raise ValueError("Current password is incorrect.")
        violations = validate_password_policy(new_password)
        if violations:
            raise PasswordPolicyError(violations)
        user.password_hash = hash_password(new_password)
        AuditService.log("User", user.id, "PASSWORD_CHANGE", actor=user)
        db.session.commit()

    @staticmethod
    def force_reset_password(user_id: int, new_password: str, actor) -> None:
        """FR-014: Administrator-forced reset for any user."""
        user = UserService._repo.get_or_404(user_id)
        violations = validate_password_policy(new_password)
        if violations:
            raise PasswordPolicyError(violations)
        user.password_hash = hash_password(new_password)
        user.failed_login_count = 0
        user.locked_until = None
        AuditService.log("User", user.id, "PASSWORD_RESET", actor=actor)
        db.session.commit()

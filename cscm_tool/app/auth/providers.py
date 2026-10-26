"""Pluggable auth provider seam. See docs/08-system-architecture.md §7: the
service layer and route handlers depend only on AuthenticatedUser, never on
which AuthProvider implementation is active, so a future on-premises AD/
ADFS provider (FR-005) is additive. Never a cloud identity provider (SEC-005)."""

from dataclasses import dataclass, field
from typing import Protocol

from app.auth.password import verify_password
from app.models.user import User


@dataclass(frozen=True)
class AuthenticatedUser:
    id: int
    username: str
    email: str
    full_name: str
    role_code: str
    engineering_domain_codes: frozenset[str] = field(default_factory=frozenset)
    # I-16: decision roles this user covers today for an absent colleague.
    delegated_role_codes: frozenset[str] = field(default_factory=frozenset)
    ui_language: str = "en"

    def can_act_as(self, role: str) -> bool:
        return self.role_code == role or role in self.delegated_role_codes

    @staticmethod
    def from_model(user: User) -> "AuthenticatedUser":
        from app.services.delegation_service import DelegationService

        return AuthenticatedUser(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role_code=user.role.code,
            engineering_domain_codes=frozenset(
                ued.engineering_domain.code for ued in user.engineering_domains
            ),
            delegated_role_codes=DelegationService.active_roles_for(user.id),
            ui_language=user.ui_language or "en",
        )


class AuthProvider(Protocol):
    def authenticate(self, credentials: dict) -> AuthenticatedUser | None: ...

    def get_login_url(self) -> str | None: ...


class SessionPasswordAuthProvider:
    """MVP-only provider (C-002): verifies credentials against
    user.password_hash. Does not itself apply lockout/rate-limit policy —
    that is provider-agnostic account-management logic owned by
    AuthService, since it must also apply once an AD/ADFS provider lands."""

    def authenticate(self, credentials: dict) -> AuthenticatedUser | None:
        user: User | None = credentials.get("user")
        password: str | None = credentials.get("password")
        if user is None or password is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return AuthenticatedUser.from_model(user)

    def get_login_url(self) -> str | None:
        return None

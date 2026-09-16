"""See docs/17-implementation-backlog.md US-009 (RBAC + Engineering Domain tags)."""

from sqlalchemy import func, or_

from app.extensions import db
from app.models.lookup import LookupEngineeringDomain, Role
from app.models.user import User, UserEngineeringDomain
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_identifier(self, identifier: str) -> User | None:
        """Looks up by username or email, per FR-001 ("username/email and password")."""
        return (
            db.session.query(User)
            .filter(or_(User.username == identifier, User.email == identifier))
            .first()
        )

    def count_active_administrators(self, exclude_user_id: int | None = None) -> int:
        """Backs FR-012: the last active Administrator cannot be deactivated."""
        query = (
            db.session.query(func.count(User.id))
            .join(Role, User.role_id == Role.id)
            .filter(Role.code == "ADMINISTRATOR", User.is_active == 1)
        )
        if exclude_user_id is not None:
            query = query.filter(User.id != exclude_user_id)
        return query.scalar() or 0

    def set_engineering_domains(self, user: User, domain_codes: list[str]) -> None:
        """Replaces the full set of Engineering Domain tags for a user (US-009)."""
        db.session.query(UserEngineeringDomain).filter(
            UserEngineeringDomain.user_id == user.id
        ).delete()
        if not domain_codes:
            return
        domains = (
            db.session.query(LookupEngineeringDomain)
            .filter(LookupEngineeringDomain.code.in_(domain_codes))
            .all()
        )
        found_codes = {d.code for d in domains}
        missing = set(domain_codes) - found_codes
        if missing:
            raise ValueError(f"Unknown engineering domain code(s): {sorted(missing)}")
        for domain in domains:
            db.session.add(UserEngineeringDomain(user_id=user.id, engineering_domain_id=domain.id))

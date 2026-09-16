"""Identity & access. See docs/11-security-architecture.md SEC-001/SEC-004."""

from typing import cast

from app.extensions import Base, db
from app.models.lookup import LookupEngineeringDomain, Role


class User(Base):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, nullable=False, unique=True)
    email = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    full_name = db.Column(db.Text, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("role.id"), nullable=False)
    is_active = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.Text, nullable=False)
    last_login_at = db.Column(db.Text)
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.Text)

    # cast(...) rather than a bare `: Role = db.relationship(...)` annotation:
    # db.relationship()'s declared return type is RelationshipProperty[Any],
    # which mypy won't accept as assignable to a narrower annotation without
    # the full SQLAlchemy 2.0 Mapped[]/mapped_column() declarative style
    # (a larger rewrite than this project's models otherwise use). cast()
    # tells mypy the runtime-accurate type wherever code dots into it.
    role: Role = cast(Role, db.relationship("Role"))
    engineering_domains: list["UserEngineeringDomain"] = cast(
        "list[UserEngineeringDomain]", db.relationship("UserEngineeringDomain", backref="user")
    )


class UserEngineeringDomain(Base):
    __tablename__ = "user_engineering_domain"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    engineering_domain_id = db.Column(
        db.Integer, db.ForeignKey("lookup_engineering_domain.id"), nullable=False
    )

    engineering_domain: LookupEngineeringDomain = cast(
        LookupEngineeringDomain, db.relationship("LookupEngineeringDomain")
    )

    __table_args__ = (db.UniqueConstraint("user_id", "engineering_domain_id"),)

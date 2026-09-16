"""Identity & access. See docs/11-security-architecture.md SEC-001/SEC-004."""

from app.extensions import Base, db


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

    role = db.relationship("Role")
    engineering_domains = db.relationship("UserEngineeringDomain", backref="user")


class UserEngineeringDomain(Base):
    __tablename__ = "user_engineering_domain"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    engineering_domain_id = db.Column(
        db.Integer, db.ForeignKey("lookup_engineering_domain.id"), nullable=False
    )

    engineering_domain = db.relationship("LookupEngineeringDomain")

    __table_args__ = (db.UniqueConstraint("user_id", "engineering_domain_id"),)

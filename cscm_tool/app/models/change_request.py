"""Change Request workflow: submission, dual review, Chief Engineer approval,
Cross-Domain Sign-Off. See docs/05-governance-handbook.md §7-8."""

from app.extensions import Base, db


class ChangeRequest(Base):
    __tablename__ = "change_request"

    id = db.Column(db.Integer, primary_key=True)
    status_code_revision_id = db.Column(
        db.Integer, db.ForeignKey("status_code_revision.id"), nullable=False, unique=True
    )
    cr_type = db.Column(db.Text, nullable=False)  # NEW | REVISION | DEPRECATION
    requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    justification = db.Column(db.Text)
    state = db.Column(db.Text, nullable=False, default="DRAFT")
    submitted_at = db.Column(db.Text)
    chief_engineer_decided_at = db.Column(db.Text)
    chief_engineer_decided_by = db.Column(db.Integer, db.ForeignKey("user.id"))

    revision = db.relationship(
        "StatusCodeRevision", backref=db.backref("change_request", uselist=False)
    )
    requester = db.relationship("User", foreign_keys=[requested_by])
    comments = db.relationship(
        "ReviewComment", backref="change_request", order_by="ReviewComment.created_at"
    )
    domain_signoffs = db.relationship("DomainSignoff", backref="change_request")


class ReviewComment(Base):
    __tablename__ = "review_comment"

    id = db.Column(db.Integer, primary_key=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_request.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    decision = db.Column(db.Text)  # REVIEWER_APPROVE | REVIEWER_REJECT | ADMIN_APPROVE | ...
    created_at = db.Column(db.Text, nullable=False)

    author = db.relationship("User")


class DomainSignoff(Base):
    __tablename__ = "domain_signoff"

    id = db.Column(db.Integer, primary_key=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_request.id"), nullable=False)
    engineering_domain_id = db.Column(
        db.Integer, db.ForeignKey("lookup_engineering_domain.id"), nullable=False
    )
    signed_off_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    signed_off_at = db.Column(db.Text, nullable=False)

    engineering_domain = db.relationship("LookupEngineeringDomain")
    signed_off_by_user = db.relationship("User")

    __table_args__ = (db.UniqueConstraint("change_request_id", "engineering_domain_id"),)

"""Change Request workflow: submission, dual review, Chief Engineer approval,
Cross-Domain Sign-Off. See docs/05-governance-handbook.md §7-8."""

from typing import cast

from app.extensions import Base, db
from app.models.lookup import LookupEngineeringDomain
from app.models.status_code import StatusCodeRevision
from app.models.user import User


class ChangeRequest(Base):
    __tablename__ = "change_request"

    id = db.Column(db.Integer, primary_key=True)
    status_code_revision_id = db.Column(
        db.Integer, db.ForeignKey("status_code_revision.id"), nullable=False, unique=True
    )
    cr_type = db.Column(db.Text, nullable=False)  # NEW | REVISION | DEPRECATION | IMPORT
    requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    justification = db.Column(db.Text)
    import_job_id = db.Column(db.Integer, db.ForeignKey("import_job.id"))
    state = db.Column(db.Text, nullable=False, default="DRAFT")
    submitted_at = db.Column(db.Text)
    chief_engineer_decided_at = db.Column(db.Text)
    chief_engineer_decided_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    assigned_reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"))  # FR-039
    change_set_id = db.Column(db.Integer, db.ForeignKey("change_set.id"))  # I-11

    revision: StatusCodeRevision = cast(
        StatusCodeRevision,
        db.relationship("StatusCodeRevision", backref=db.backref("change_request", uselist=False)),
    )
    requester: User = cast(User, db.relationship("User", foreign_keys=[requested_by]))
    assigned_reviewer: User | None = cast(
        "User | None", db.relationship("User", foreign_keys=[assigned_reviewer_id])
    )
    change_set: "ChangeSet | None" = cast(
        "ChangeSet | None", db.relationship("ChangeSet", back_populates="change_requests")
    )
    comments: list["ReviewComment"] = cast(
        "list[ReviewComment]",
        db.relationship(
            "ReviewComment", back_populates="change_request", order_by="ReviewComment.created_at"
        ),
    )
    domain_signoffs: list["DomainSignoff"] = cast(
        "list[DomainSignoff]",
        db.relationship("DomainSignoff", back_populates="change_request"),
    )


class ReviewComment(Base):
    __tablename__ = "review_comment"

    id = db.Column(db.Integer, primary_key=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_request.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    decision = db.Column(db.Text)  # REVIEWER_APPROVE | REVIEWER_REJECT | ADMIN_APPROVE | ...
    created_at = db.Column(db.Text, nullable=False)

    author: User = cast(User, db.relationship("User"))
    change_request: ChangeRequest = cast(
        ChangeRequest, db.relationship("ChangeRequest", back_populates="comments")
    )


class DomainSignoff(Base):
    __tablename__ = "domain_signoff"

    id = db.Column(db.Integer, primary_key=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_request.id"), nullable=False)
    engineering_domain_id = db.Column(
        db.Integer, db.ForeignKey("lookup_engineering_domain.id"), nullable=False
    )
    signed_off_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    signed_off_at = db.Column(db.Text, nullable=False)

    engineering_domain: LookupEngineeringDomain = cast(
        LookupEngineeringDomain, db.relationship("LookupEngineeringDomain")
    )
    signed_off_by_user: User = cast(User, db.relationship("User"))
    change_request: ChangeRequest = cast(
        ChangeRequest, db.relationship("ChangeRequest", back_populates="domain_signoffs")
    )

    __table_args__ = (db.UniqueConstraint("change_request_id", "engineering_domain_id"),)


class DomainSignoffRequest(Base):
    """FR-028: the originating Engineer's request for a domain sign-off."""

    __tablename__ = "domain_signoff_request"

    id = db.Column(db.Integer, primary_key=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_request.id"), nullable=False)
    engineering_domain_id = db.Column(
        db.Integer, db.ForeignKey("lookup_engineering_domain.id"), nullable=False
    )
    requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.Text, nullable=False)

    engineering_domain: LookupEngineeringDomain = cast(
        LookupEngineeringDomain, db.relationship("LookupEngineeringDomain")
    )
    change_request: ChangeRequest = cast(ChangeRequest, db.relationship("ChangeRequest"))
    target_user: User | None = cast(
        "User | None", db.relationship("User", foreign_keys=[target_user_id])
    )

    __table_args__ = (db.UniqueConstraint("change_request_id", "engineering_domain_id"),)


class ChangeSet(Base):
    """I-11: groups the CRs that ship with one controller software release.
    Presentation and queueing only - each CR keeps its own three decisions."""

    __tablename__ = "change_set"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False, unique=True)
    description = db.Column(db.Text)
    target_software_version_id = db.Column(
        db.Integer, db.ForeignKey("lookup_controller_software_version.id")
    )
    status = db.Column(db.Text, nullable=False, default="OPEN")  # OPEN | CLOSED
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.Text, nullable=False)
    closed_at = db.Column(db.Text)

    target_software_version = db.relationship("LookupControllerSoftwareVersion")
    change_requests: list[ChangeRequest] = cast(
        "list[ChangeRequest]",
        db.relationship("ChangeRequest", back_populates="change_set", order_by="ChangeRequest.id"),
    )


class CrAttachment(Base):
    """I-13: evidence on a change request. The bytes live outside the web root
    (instance/attachments); this row is the metadata and the SHA-256."""

    __tablename__ = "cr_attachment"

    id = db.Column(db.Integer, primary_key=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_request.id"), nullable=False)
    filename = db.Column(db.Text, nullable=False)
    content_type = db.Column(db.Text, nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    sha256 = db.Column(db.Text, nullable=False)
    storage_path = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    uploaded_at = db.Column(db.Text, nullable=False)

    uploader: User = cast(User, db.relationship("User"))


class FieldComment(Base):
    """I-23: a review comment attached to one field of the revision."""

    __tablename__ = "field_comment"

    id = db.Column(db.Integer, primary_key=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_request.id"), nullable=False)
    field_name = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.Text, nullable=False)
    resolved_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    resolved_at = db.Column(db.Text)

    author: User = cast(User, db.relationship("User", foreign_keys=[author_id]))


class ReviewChecklistItem(Base):
    """I-23: one line of the review checklist, for one Functional System Group or all."""

    __tablename__ = "review_checklist_item"

    id = db.Column(db.Integer, primary_key=True)
    functional_system_group_id = db.Column(
        db.Integer, db.ForeignKey("lookup_functional_system_group.id")
    )
    text = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.Text, nullable=False)


class CrChecklistConfirmation(Base):
    __tablename__ = "cr_checklist_confirmation"

    id = db.Column(db.Integer, primary_key=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_request.id"), nullable=False)
    checklist_item_id = db.Column(
        db.Integer, db.ForeignKey("review_checklist_item.id"), nullable=False
    )
    item_text = db.Column(db.Text, nullable=False)
    confirmed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    confirmed_at = db.Column(db.Text, nullable=False)

    __table_args__ = (db.UniqueConstraint("change_request_id", "checklist_item_id"),)

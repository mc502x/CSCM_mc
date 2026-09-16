"""Core governed entities. See docs/04-domain-model.md and docs/07-database-design.md.
CHECK constraints and triggers enforcing lifecycle/sandbox rules live in
docs/artifacts/schema.sql and are applied by the schema migration, not
duplicated here (defense-in-depth is DB-layer + service-layer, not ORM-layer).

Relationships use explicit cast(...) annotations (see app/models/user.py for
why) wherever service/route code dots into them."""

from typing import cast

from app.extensions import Base, db
from app.models.lookup import (
    LookupAccessRights,
    LookupAlarmBehaviour,
    LookupAvailabilityGroup,
    LookupBrakeProgram,
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
    LookupOperationalState,
    LookupResetProgram,
    LookupStatusCategory,
    LookupTurbinePlatform,
)
from app.models.user import User


class StatusCode(Base):
    __tablename__ = "status_code"

    id = db.Column(db.Integer, primary_key=True)
    status_code_identifier = db.Column(db.Text, unique=True)  # NULL until Draft->Review
    functional_system_group_id = db.Column(
        db.Integer, db.ForeignKey("lookup_functional_system_group.id"), nullable=False
    )
    functional_subgroup_id = db.Column(db.Integer, db.ForeignKey("lookup_functional_subgroup.id"))
    is_sandbox = db.Column(db.Integer, nullable=False, default=0)
    platform_variant_of_status_code_id = db.Column(db.Integer, db.ForeignKey("status_code.id"))
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.Text, nullable=False)

    functional_system_group: LookupFunctionalSystemGroup = cast(
        LookupFunctionalSystemGroup, db.relationship("LookupFunctionalSystemGroup")
    )
    functional_subgroup: LookupFunctionalSubgroup | None = cast(
        "LookupFunctionalSubgroup | None", db.relationship("LookupFunctionalSubgroup")
    )
    owner: User = cast(User, db.relationship("User"))
    revisions: list["StatusCodeRevision"] = cast(
        "list[StatusCodeRevision]",
        db.relationship(
            "StatusCodeRevision",
            back_populates="status_code",
            foreign_keys="StatusCodeRevision.status_code_id",
            order_by="StatusCodeRevision.revision_number",
        ),
    )


class StatusCodeRevision(Base):
    __tablename__ = "status_code_revision"

    id = db.Column(db.Integer, primary_key=True)
    status_code_id = db.Column(db.Integer, db.ForeignKey("status_code.id"), nullable=False)
    revision_number = db.Column(db.Integer, nullable=False)
    is_current = db.Column(db.Integer, nullable=False, default=1)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    status_category_id = db.Column(
        db.Integer, db.ForeignKey("lookup_status_category.id"), nullable=False
    )
    availability_group_id = db.Column(
        db.Integer, db.ForeignKey("lookup_availability_group.id"), nullable=False
    )
    brake_program_id = db.Column(
        db.Integer, db.ForeignKey("lookup_brake_program.id"), nullable=False
    )
    reset_program_id = db.Column(
        db.Integer, db.ForeignKey("lookup_reset_program.id"), nullable=False
    )
    software_version = db.Column(db.Text, nullable=False)
    operational_state_id = db.Column(
        db.Integer, db.ForeignKey("lookup_operational_state.id"), nullable=False
    )
    access_rights_id = db.Column(
        db.Integer, db.ForeignKey("lookup_access_rights.id"), nullable=False
    )
    delay_before_alarm_seconds = db.Column(db.Integer, nullable=False, default=0)
    delay_before_reset_seconds = db.Column(db.Integer, nullable=False, default=0)
    alarm_behaviour_id = db.Column(
        db.Integer, db.ForeignKey("lookup_alarm_behaviour.id"), nullable=False
    )
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    lifecycle_status = db.Column(db.Text, nullable=False, default="DRAFT")
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.Text, nullable=False)
    reviewer_signoff_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    reviewer_signoff_at = db.Column(db.Text)
    admin_signoff_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    admin_signoff_at = db.Column(db.Text)
    chief_engineer_approved_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    chief_engineer_approval_date = db.Column(db.Text)
    effective_date = db.Column(db.Text)
    deprecated_reason = db.Column(db.Text)
    superseded_by_status_code_id = db.Column(db.Integer, db.ForeignKey("status_code.id"))

    status_code: StatusCode = cast(
        StatusCode,
        db.relationship("StatusCode", back_populates="revisions", foreign_keys=[status_code_id]),
    )
    status_category: LookupStatusCategory = cast(
        LookupStatusCategory, db.relationship("LookupStatusCategory")
    )
    availability_group: LookupAvailabilityGroup = cast(
        LookupAvailabilityGroup, db.relationship("LookupAvailabilityGroup")
    )
    brake_program: LookupBrakeProgram = cast(
        LookupBrakeProgram, db.relationship("LookupBrakeProgram")
    )
    reset_program: LookupResetProgram = cast(
        LookupResetProgram, db.relationship("LookupResetProgram")
    )
    operational_state: LookupOperationalState = cast(
        LookupOperationalState, db.relationship("LookupOperationalState")
    )
    access_rights: LookupAccessRights = cast(
        LookupAccessRights, db.relationship("LookupAccessRights")
    )
    alarm_behaviour: LookupAlarmBehaviour = cast(
        LookupAlarmBehaviour, db.relationship("LookupAlarmBehaviour")
    )
    platforms: list["StatusCodeRevisionPlatform"] = cast(
        "list[StatusCodeRevisionPlatform]",
        db.relationship("StatusCodeRevisionPlatform", back_populates="revision"),
    )

    __table_args__ = (db.UniqueConstraint("status_code_id", "revision_number"),)


class StatusCodeRevisionPlatform(Base):
    __tablename__ = "status_code_revision_platform"

    id = db.Column(db.Integer, primary_key=True)
    status_code_revision_id = db.Column(
        db.Integer, db.ForeignKey("status_code_revision.id"), nullable=False
    )
    turbine_platform_id = db.Column(
        db.Integer, db.ForeignKey("lookup_turbine_platform.id"), nullable=False
    )

    revision: StatusCodeRevision = cast(
        StatusCodeRevision,
        db.relationship("StatusCodeRevision", back_populates="platforms"),
    )
    turbine_platform: LookupTurbinePlatform = cast(
        LookupTurbinePlatform, db.relationship("LookupTurbinePlatform")
    )

    __table_args__ = (db.UniqueConstraint("status_code_revision_id", "turbine_platform_id"),)

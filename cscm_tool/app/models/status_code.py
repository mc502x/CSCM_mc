"""Core governed entities. See docs/04-domain-model.md and docs/07-database-design.md.
CHECK constraints and triggers enforcing lifecycle/sandbox rules live in
docs/artifacts/schema.sql and are applied by the schema migration, not
duplicated here (defense-in-depth is DB-layer + service-layer, not ORM-layer).

v3 (2026-09-17): the field set is grounded in a real export of the live
status code library (docs/06-data-dictionary.md provenance note). Note that
`status_category`, `available_group`, and the eight "program reference"
fields are plain columns, not lookup-table foreign keys — the real data
either uses a closed 3-value enum (status_category) or numeric ranges that
are only soft-validated against a currently-observed set (available_group,
program references), not hard-enforced closed vocabularies.

Relationships use explicit cast(...) annotations (see app/models/user.py for
why) wherever service/route code dots into them."""

from typing import cast

from app.extensions import Base, db
from app.models.lookup import (
    LookupControllerSoftwareVersion,
    LookupCustomerAccess,
    LookupDevelopmentAccess,
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
    LookupGridOperatorAccess,
    LookupSalesAccess,
    LookupServiceAccess,
    LookupServicePartnerAccess,
    LookupTccAccess,
    LookupTopAccess,
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
    functional_subgroup_id = db.Column(
        db.Integer, db.ForeignKey("lookup_functional_subgroup.id"), nullable=False
    )
    is_sandbox = db.Column(db.Integer, nullable=False, default=0)
    platform_variant_of_status_code_id = db.Column(db.Integer, db.ForeignKey("status_code.id"))
    legacy_reference_number = db.Column(db.Text)
    # v4.2: the number an imported StCd_<n>.st program carries; issued unchanged at Submit
    reserved_identifier = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.Text, nullable=False)
    withdrawn_at = db.Column(db.Text)  # v4.9: the last revision was withdrawn (BR-026)

    functional_system_group: LookupFunctionalSystemGroup = cast(
        LookupFunctionalSystemGroup, db.relationship("LookupFunctionalSystemGroup")
    )
    functional_subgroup: LookupFunctionalSubgroup = cast(
        LookupFunctionalSubgroup, db.relationship("LookupFunctionalSubgroup")
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
    software_version = db.Column(db.Text)  # nullable — open item, see 06-data-dictionary.md
    status_category = db.Column(db.Text, nullable=False)  # ERROR | WARNING | INFO
    available_group = db.Column(db.Integer, nullable=False)  # soft-validated, not an FK
    alarm_flag = db.Column(db.Integer, nullable=False, default=0)
    set_delay = db.Column(db.Text, nullable=False)
    reset_delay = db.Column(db.Text, nullable=False)
    up_down_counter = db.Column(db.Integer, nullable=False, default=0)
    trigger_snapshot = db.Column(db.Integer, nullable=False, default=0)
    loadless_spinning_permitted = db.Column(db.Integer, nullable=False, default=0)

    number_of_times_repeated = db.Column(db.Integer)
    repeated_over_the_course = db.Column(db.Text)
    status_code_for_repeated_error = db.Column(db.Integer)  # opaque, NOT a FK

    yaw_program = db.Column(db.Integer, nullable=False, default=0)
    manual_reset_program = db.Column(db.Integer, nullable=False, default=0)
    auto_reset_program = db.Column(db.Integer, nullable=False, default=0)
    converter_reactive_power_program = db.Column(db.Integer, nullable=False, default=0)
    brake_program = db.Column(db.Integer, nullable=False, default=0)
    umrichterprogramm_gsc = db.Column(db.Integer, nullable=False, default=0)
    umrichterprogramm_msc = db.Column(db.Integer, nullable=False, default=0)
    yaw_bearing_lubrication_program = db.Column(db.Integer, nullable=False, default=0)

    development_access_id = db.Column(
        "development_access", db.Integer, db.ForeignKey("lookup_development_access.id")
    )
    sales_access_id = db.Column("sales_access", db.Integer, db.ForeignKey("lookup_sales_access.id"))
    tcc_access_id = db.Column("tcc_access", db.Integer, db.ForeignKey("lookup_tcc_access.id"))
    service_access_id = db.Column(
        "service_access", db.Integer, db.ForeignKey("lookup_service_access.id")
    )
    turbine_operator_package_access_id = db.Column(
        "turbine_operator_package_access", db.Integer, db.ForeignKey("lookup_top_access.id")
    )
    grid_operator_access_id = db.Column(
        "grid_operator_access", db.Integer, db.ForeignKey("lookup_grid_operator_access.id")
    )
    service_partner_access_id = db.Column(
        "service_partner_access", db.Integer, db.ForeignKey("lookup_service_partner_access.id")
    )
    customer_access_id = db.Column(
        "customer_access", db.Integer, db.ForeignKey("lookup_customer_access.id")
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

    row_version = db.Column(db.Integer, nullable=False, default=1)  # I-01
    updated_at = db.Column(db.Text)  # I-01
    remedy_text = db.Column(db.Text)  # I-14
    affected_component = db.Column(db.Text)  # I-14
    related_status_codes = db.Column(db.Text)  # I-14, comma separated identifiers
    standard_references = db.Column(db.Text)  # I-14
    applies_from_version_id = db.Column(
        db.Integer, db.ForeignKey("lookup_controller_software_version.id")
    )  # I-07
    applies_to_version_id = db.Column(
        db.Integer, db.ForeignKey("lookup_controller_software_version.id")
    )  # I-07
    planned_effective_date = db.Column(db.Text)  # I-27
    planned_deprecation_date = db.Column(db.Text)  # I-27

    status_code: StatusCode = cast(
        StatusCode,
        db.relationship("StatusCode", back_populates="revisions", foreign_keys=[status_code_id]),
    )
    development_access: LookupDevelopmentAccess | None = cast(
        "LookupDevelopmentAccess | None", db.relationship("LookupDevelopmentAccess")
    )
    sales_access: LookupSalesAccess | None = cast(
        "LookupSalesAccess | None", db.relationship("LookupSalesAccess")
    )
    tcc_access: LookupTccAccess | None = cast(
        "LookupTccAccess | None", db.relationship("LookupTccAccess")
    )
    service_access: LookupServiceAccess | None = cast(
        "LookupServiceAccess | None", db.relationship("LookupServiceAccess")
    )
    turbine_operator_package_access: LookupTopAccess | None = cast(
        "LookupTopAccess | None", db.relationship("LookupTopAccess")
    )
    grid_operator_access: LookupGridOperatorAccess | None = cast(
        "LookupGridOperatorAccess | None", db.relationship("LookupGridOperatorAccess")
    )
    service_partner_access: LookupServicePartnerAccess | None = cast(
        "LookupServicePartnerAccess | None", db.relationship("LookupServicePartnerAccess")
    )
    customer_access: LookupCustomerAccess | None = cast(
        "LookupCustomerAccess | None", db.relationship("LookupCustomerAccess")
    )
    applies_from_version: LookupControllerSoftwareVersion | None = cast(
        "LookupControllerSoftwareVersion | None",
        db.relationship("LookupControllerSoftwareVersion", foreign_keys=[applies_from_version_id]),
    )
    applies_to_version: LookupControllerSoftwareVersion | None = cast(
        "LookupControllerSoftwareVersion | None",
        db.relationship("LookupControllerSoftwareVersion", foreign_keys=[applies_to_version_id]),
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

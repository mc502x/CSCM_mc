"""The legacy -> new status code mapping and the requests to change it (FR-191..FR-198).
Shapes mirror docs/artifacts/schema.sql (v4.17)."""

from typing import cast

from app.extensions import Base, db
from app.models.user import User

ACCESS_COLUMNS = (
    "development_access",
    "sales_access",
    "tcc_access",
    "service_access",
    "turbine_operator_package_access",
    "grid_operator_access",
    "service_partner_access",
    "customer_access",
)


class StatusCodeMapping(Base):
    """One row of the mapping: only what the generated programs do not carry."""

    __tablename__ = "status_code_mapping"

    id = db.Column(db.Integer, primary_key=True)
    family = db.Column(db.Text, nullable=False)  # MC | HC
    legacy_number = db.Column(db.Integer)
    new_number = db.Column(db.Integer, nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)  # the English title
    functional_group = db.Column(db.Text)
    logical_node = db.Column(db.Text)
    status_type = db.Column(db.Text)  # ERROR | WARNING | INFO
    up_down_counter = db.Column(db.Integer)
    parameter_set_delay = db.Column(db.Text)
    parameter_reset_delay = db.Column(db.Text)
    development_access = db.Column(db.Text)
    sales_access = db.Column(db.Text)
    tcc_access = db.Column(db.Text)
    service_access = db.Column(db.Text)
    turbine_operator_package_access = db.Column(db.Text)
    grid_operator_access = db.Column(db.Text)
    service_partner_access = db.Column(db.Text)
    customer_access = db.Column(db.Text)
    cause = db.Column(db.Text)
    directive = db.Column(db.Text)
    note = db.Column(db.Text)
    status = db.Column(db.Text, nullable=False, default="PROPOSED")
    source = db.Column(db.Text)
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.Text, nullable=False)

    __table_args__ = (db.UniqueConstraint("family", "legacy_number"),)


class MappingChange(Base):
    """A request to change the mapping, decided as a whole by the three roles."""

    __tablename__ = "mapping_change"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    origin = db.Column(db.Text, nullable=False, default="FORM")  # FORM | WORKBOOK | SELECTION
    requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    requested_at = db.Column(db.Text, nullable=False)
    state = db.Column(
        db.Text, nullable=False, default="OPEN"
    )  # OPEN | APPLIED | REJECTED | WITHDRAWN
    closed_at = db.Column(db.Text)

    requester: User = cast(User, db.relationship("User", foreign_keys=[requested_by]))
    items: list["MappingChangeItem"] = cast(
        "list[MappingChangeItem]",
        db.relationship(
            "MappingChangeItem", back_populates="change", order_by="MappingChangeItem.id"
        ),
    )
    approvals: list["MappingApproval"] = cast(
        "list[MappingApproval]",
        db.relationship("MappingApproval", back_populates="change", order_by="MappingApproval.id"),
    )


class MappingChangeItem(Base):
    __tablename__ = "mapping_change_item"

    id = db.Column(db.Integer, primary_key=True)
    change_id = db.Column(db.Integer, db.ForeignKey("mapping_change.id"), nullable=False)
    mapping_id = db.Column(db.Integer, db.ForeignKey("status_code_mapping.id"))
    action = db.Column(db.Text, nullable=False)  # ADD | CHANGE | CONFIRM | REJECT
    base_version = db.Column(db.Integer)
    before_json = db.Column(db.Text)
    after_json = db.Column(db.Text, nullable=False)

    change: MappingChange = cast(
        MappingChange, db.relationship("MappingChange", back_populates="items")
    )


class MappingApproval(Base):
    __tablename__ = "mapping_approval"

    id = db.Column(db.Integer, primary_key=True)
    change_id = db.Column(db.Integer, db.ForeignKey("mapping_change.id"), nullable=False)
    role_code = db.Column(db.Text, nullable=False)  # STCD_OWNER | CHIEF_ENGINEER | ADMINISTRATOR
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    decision = db.Column(db.Text, nullable=False)  # APPROVE | REJECT
    comment = db.Column(db.Text)
    decided_at = db.Column(db.Text, nullable=False)

    change: MappingChange = cast(
        MappingChange, db.relationship("MappingChange", back_populates="approvals")
    )
    user: User = cast(User, db.relationship("User"))

    __table_args__ = (
        db.UniqueConstraint("change_id", "role_code"),
        db.UniqueConstraint("change_id", "user_id"),
    )

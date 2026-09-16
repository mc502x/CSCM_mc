"""Reference/lookup vocabularies. Table shapes mirror docs/artifacts/schema.sql exactly."""

from typing import cast

from app.extensions import Base, db


class Role(Base):
    __tablename__ = "role"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False, unique=True)
    label = db.Column(db.Text, nullable=False)


class LookupEngineeringDomain(Base):
    __tablename__ = "lookup_engineering_domain"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False, unique=True)
    label = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class LookupFunctionalSystemGroup(Base):
    __tablename__ = "lookup_functional_system_group"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False, unique=True)
    label = db.Column(db.Text, nullable=False)
    range_start = db.Column(db.Integer, nullable=False)
    range_end = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    subgroups: list["LookupFunctionalSubgroup"] = cast(
        "list[LookupFunctionalSubgroup]",
        db.relationship("LookupFunctionalSubgroup", back_populates="functional_system_group"),
    )


class LookupFunctionalSubgroup(Base):
    """Placeholder taxonomy pending Controls Engineering's real list — see
    docs/06-data-dictionary.md §9a. Replacing the data is a seed update, not
    a schema change."""

    __tablename__ = "lookup_functional_subgroup"

    id = db.Column(db.Integer, primary_key=True)
    functional_system_group_id = db.Column(
        db.Integer, db.ForeignKey("lookup_functional_system_group.id"), nullable=False
    )
    code = db.Column(db.Text, nullable=False)
    label = db.Column(db.Text, nullable=False)
    sub_range_start = db.Column(db.Integer, nullable=False)
    sub_range_end = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    functional_system_group: "LookupFunctionalSystemGroup" = cast(
        "LookupFunctionalSystemGroup",
        db.relationship("LookupFunctionalSystemGroup", back_populates="subgroups"),
    )

    __table_args__ = (db.UniqueConstraint("functional_system_group_id", "code"),)


class LookupTurbinePlatform(Base):
    __tablename__ = "lookup_turbine_platform"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False, unique=True)
    label = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class _CodedLookup:
    """Shared column shape for the single-table vocabularies below."""

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False, unique=True)
    label = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class LookupStatusCategory(_CodedLookup, Base):
    __tablename__ = "lookup_status_category"


class LookupAvailabilityGroup(_CodedLookup, Base):
    __tablename__ = "lookup_availability_group"


class LookupBrakeProgram(_CodedLookup, Base):
    __tablename__ = "lookup_brake_program"


class LookupResetProgram(_CodedLookup, Base):
    __tablename__ = "lookup_reset_program"


class LookupOperationalState(_CodedLookup, Base):
    __tablename__ = "lookup_operational_state"


class LookupAccessRights(_CodedLookup, Base):
    __tablename__ = "lookup_access_rights"


class LookupAlarmBehaviour(_CodedLookup, Base):
    __tablename__ = "lookup_alarm_behaviour"

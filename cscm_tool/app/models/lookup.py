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
    description = db.Column(db.Text)  # NFR-007b inline help; NULL until supplied
    is_active = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class LookupFunctionalSystemGroup(Base):
    """v3 (2026-09-17): `code` is NOT unique on its own — WTUR and WROT are
    each reused for a second, numerically distinct group (Hub Controller).
    Uniqueness is on (code, range_start); always resolve a group by its
    numeric range/id, never by prefix alone (docs/06-data-dictionary.md §9)."""

    __tablename__ = "lookup_functional_system_group"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False)
    label = db.Column(db.Text, nullable=False)
    range_start = db.Column(db.Integer, nullable=False)
    range_end = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)  # NFR-007b inline help; NULL until supplied
    is_active = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    subgroups: list["LookupFunctionalSubgroup"] = cast(
        "list[LookupFunctionalSubgroup]",
        db.relationship("LookupFunctionalSubgroup", back_populates="functional_system_group"),
    )

    __table_args__ = (db.UniqueConstraint("code", "range_start"),)


class LookupFunctionalSubgroup(Base):
    """Real taxonomy seeded from the live library export — see
    docs/06-data-dictionary.md §9a. Every Status Code must belong to exactly
    one (mandatory, never optional, v3)."""

    __tablename__ = "lookup_functional_subgroup"

    id = db.Column(db.Integer, primary_key=True)
    functional_system_group_id = db.Column(
        db.Integer, db.ForeignKey("lookup_functional_system_group.id"), nullable=False
    )
    code = db.Column(db.Text, nullable=False)
    label = db.Column(db.Text, nullable=False)
    sub_range_start = db.Column(db.Integer, nullable=False)
    sub_range_end = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)  # NFR-007b inline help; NULL until supplied
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
    description = db.Column(db.Text)  # NFR-007b inline help; NULL until supplied
    is_active = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class LookupAvailableGroup(Base):
    """v3: numeric availability-accounting code: `code` is INTEGER, `label`
    is nullable — the source export carries only the code, no description
    (docs/06-data-dictionary.md §9c, labels TBD). Not referenced by a FK from
    status_code_revision (soft-validated only, per schema.sql)."""

    __tablename__ = "lookup_available_group"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Integer, nullable=False, unique=True)
    label = db.Column(db.Text)
    description = db.Column(db.Text)  # NFR-007b inline help; NULL until supplied
    is_active = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class _CodedLookup:
    """Shared column shape for the single-table vocabularies below.
    `description` is NULL until Controls Engineering supplies real text (an
    Administrator edits it in Lookup Administration); NFR-007b's inline help
    falls back to a "not yet available" message while it is empty
    (10-ui-ux-specification.md §5)."""

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False, unique=True)
    label = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)  # NFR-007b inline help; NULL until supplied
    is_active = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class LookupDevelopmentAccess(_CodedLookup, Base):
    __tablename__ = "lookup_development_access"


class LookupSalesAccess(_CodedLookup, Base):
    __tablename__ = "lookup_sales_access"


class LookupTccAccess(_CodedLookup, Base):
    __tablename__ = "lookup_tcc_access"


class LookupServiceAccess(_CodedLookup, Base):
    __tablename__ = "lookup_service_access"


class LookupTopAccess(_CodedLookup, Base):
    """Turbine Operator Package access (docs/06-data-dictionary.md §9d.5)."""

    __tablename__ = "lookup_top_access"


class LookupGridOperatorAccess(_CodedLookup, Base):
    __tablename__ = "lookup_grid_operator_access"


class LookupServicePartnerAccess(_CodedLookup, Base):
    __tablename__ = "lookup_service_partner_access"


class LookupCustomerAccess(_CodedLookup, Base):
    __tablename__ = "lookup_customer_access"

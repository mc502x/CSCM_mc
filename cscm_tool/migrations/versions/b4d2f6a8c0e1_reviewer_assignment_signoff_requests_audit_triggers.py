"""reviewer assignment, domain sign-off requests, audit append-only, lookup descriptions

Brings a database created from the earlier baseline up to the 2026-10-21
schema (docs/artifacts/schema.sql): FR-039 `change_request.assigned_reviewer_id`,
FR-028 `domain_signoff_request`, FR-072 `trg_audit_no_update/delete`, and the
NFR-007b `description` column on every lookup table.

A fresh database already gets all of this from the baseline (which applies
schema.sql verbatim), so every step here is guarded and a no-op when the
object exists. That keeps `flask db upgrade` correct for both a new install
and an existing 9dc07a07a48b database.

Revision ID: b4d2f6a8c0e1
Revises: 9dc07a07a48b
Create Date: 2026-10-21 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "b4d2f6a8c0e1"
down_revision = "9dc07a07a48b"
branch_labels = None
depends_on = None

LOOKUP_TABLES = [
    "lookup_engineering_domain",
    "lookup_functional_system_group",
    "lookup_functional_subgroup",
    "lookup_turbine_platform",
    "lookup_available_group",
    "lookup_development_access",
    "lookup_sales_access",
    "lookup_tcc_access",
    "lookup_service_access",
    "lookup_top_access",
    "lookup_grid_operator_access",
    "lookup_service_partner_access",
    "lookup_customer_access",
]


def _columns(inspector, table: str) -> set[str]:
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "assigned_reviewer_id" not in _columns(inspector, "change_request"):
        op.execute(
            "ALTER TABLE change_request ADD COLUMN assigned_reviewer_id INTEGER REFERENCES user(id)"
        )

    for table in LOOKUP_TABLES:
        if "description" not in _columns(inspector, table):
            op.execute(f"ALTER TABLE {table} ADD COLUMN description TEXT")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS domain_signoff_request (
            id                          INTEGER PRIMARY KEY,
            change_request_id           INTEGER NOT NULL REFERENCES change_request(id),
            engineering_domain_id       INTEGER NOT NULL REFERENCES lookup_engineering_domain(id),
            requested_by                INTEGER NOT NULL REFERENCES user(id),
            target_user_id              INTEGER REFERENCES user(id),
            created_at                  TEXT NOT NULL
                                         DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            UNIQUE (change_request_id, engineering_domain_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dsr_target ON domain_signoff_request (target_user_id)"
    )

    for name, event in (("trg_audit_no_update", "UPDATE"), ("trg_audit_no_delete", "DELETE")):
        op.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS {name}
            BEFORE {event} ON audit_log_entry
            BEGIN
                SELECT RAISE(ABORT, 'audit_log_entry is append-only');
            END
            """
        )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_audit_no_delete")
    op.execute("DROP TRIGGER IF EXISTS trg_audit_no_update")
    op.execute("DROP TABLE IF EXISTS domain_signoff_request")

    inspector = sa.inspect(op.get_bind())
    for table in LOOKUP_TABLES:
        if "description" in _columns(inspector, table):
            op.execute(f"ALTER TABLE {table} DROP COLUMN description")
    # change_request.assigned_reviewer_id is left in place: SQLite cannot drop a
    # column that carries a foreign key, and an unused nullable column is harmless.

"""initial schema (v2, from docs/artifacts/schema.sql)

This migration applies docs/artifacts/schema.sql verbatim rather than relying
on Alembic autogenerate: that file is the hand-reviewed source of truth for
CHECK constraints, partial indexes, and triggers that SQLite's DDL dialect
expresses in ways autogenerate does not reproduce reliably (see
docs/18-claude-code-implementation-guide.md §6). Any future schema change
must still go through its own reversible Alembic migration on top of this
baseline, and be reflected in the same PR in docs/06-data-dictionary.md,
docs/07-database-design.md, and docs/artifacts/schema.sql (docs/15-development-standards.md §5).

Revision ID: 9dc07a07a48b
Revises:
Create Date: 2026-09-16 07:27:16.483174

"""

from pathlib import Path

from alembic import op

# revision identifiers, used by Alembic.
revision = "9dc07a07a48b"
down_revision = None
branch_labels = None
depends_on = None

# migrations/versions/ -> migrations/ -> cscm_tool/ -> repo root -> docs/artifacts/schema.sql
SCHEMA_SQL_PATH = Path(__file__).resolve().parents[3] / "docs" / "artifacts" / "schema.sql"

# Reverse-dependency order for a clean downgrade (triggers/indexes drop with their table).
_TABLES_NEWEST_FIRST = [
    "export_job",
    "audit_log_entry",
    "release_item",
    "release",
    "domain_signoff",
    "review_comment",
    "change_request",
    "status_code_revision_platform",
    "status_code_revision",
    "status_code",
    "user_engineering_domain",
    "user",
    "lookup_alarm_behaviour",
    "lookup_access_rights",
    "lookup_operational_state",
    "lookup_reset_program",
    "lookup_brake_program",
    "lookup_availability_group",
    "lookup_status_category",
    "lookup_turbine_platform",
    "lookup_functional_subgroup",
    "lookup_functional_system_group",
    "lookup_engineering_domain",
    "role",
]


def upgrade():
    connection = op.get_bind()
    raw_connection = connection.connection.dbapi_connection
    schema_sql = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    raw_connection.executescript(schema_sql)


def downgrade():
    connection = op.get_bind()
    raw_connection = connection.connection.dbapi_connection
    raw_connection.executescript(
        "PRAGMA foreign_keys = OFF;\n"
        + "\n".join(f"DROP TABLE IF EXISTS {table};" for table in _TABLES_NEWEST_FIRST)
        + "\nPRAGMA foreign_keys = ON;"
    )

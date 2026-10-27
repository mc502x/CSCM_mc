# ruff: noqa: E501  (docstring lines)
"""the legacy -> new status code mapping with three approvals (schema v4.17)

Adds status_code_mapping, mapping_change, mapping_change_item and mapping_approval (docs/03-srs.md
FR-191..FR-198). The tables start empty: the initial content is loaded from seed_data/legacy_mapping.xlsx by
`flask mapping-seed` (the installer and first_start.py run it), so a test database or a new database is not
filled with 1,165 rows by every upgrade. The DDL comes from docs/artifacts/schema.sql (app/schema_sql.py); a
table is created only when it is missing.

Revision ID: i5f7a9c1e348
Revises: h4e6c8d0f237
Create Date: 2026-10-27 19:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.schema_sql import schema_statements, table_statements

revision = "i5f7a9c1e348"
down_revision = "h4e6c8d0f237"
branch_labels = None
depends_on = None

NEW_TABLES = ["status_code_mapping", "mapping_change", "mapping_change_item", "mapping_approval"]


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    statements = schema_statements()
    for table in NEW_TABLES:
        if table not in existing:
            for stmt in table_statements(table, statements):
                op.execute(stmt)


def downgrade():
    for table in reversed(NEW_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table}")

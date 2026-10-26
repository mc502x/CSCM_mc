# ruff: noqa: E501  (docstring lines)
"""the sample inspection of a bulk decision (schema v4.13)

Adds bulk_sample and bulk_sample_item (docs/03-srs.md FR-180): a decision on many change requests at once
needs a sample of them to have been looked at, and the sample, who drew it and the verdict per code are
kept. The DDL comes from docs/artifacts/schema.sql (app/schema_sql.py); a table is created only when it
is missing.

Revision ID: h4e6c8d0f237
Revises: g3d5b7c9e126
Create Date: 2026-10-25 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.schema_sql import schema_statements, table_statements

revision = "h4e6c8d0f237"
down_revision = "g3d5b7c9e126"
branch_labels = None
depends_on = None

NEW_TABLES = ["bulk_sample", "bulk_sample_item"]


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

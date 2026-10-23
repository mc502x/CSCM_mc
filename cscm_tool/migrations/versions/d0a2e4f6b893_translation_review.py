"""translation review in the application (schema v4.7)

Adds the four tables of the review section: language_reviewer, translation_review,
translation_review_item and translation_override (docs/03-srs.md FR-164). The DDL comes from
docs/artifacts/schema.sql (app/schema_sql.py); every table is created only when it is missing.

Revision ID: d0a2e4f6b893
Revises: c9f1d3e5a782
Create Date: 2026-10-24 13:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.schema_sql import schema_statements, table_statements

revision = "d0a2e4f6b893"
down_revision = "c9f1d3e5a782"
branch_labels = None
depends_on = None

NEW_TABLES = [
    "language_reviewer",
    "translation_review",
    "translation_review_item",
    "translation_override",
]


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    statements = schema_statements()
    for table in NEW_TABLES:
        if table in existing:
            continue
        for stmt in table_statements(table, statements):
            op.execute(stmt)


def downgrade():
    for table in reversed(NEW_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table}")

"""technical nomenclature (schema v4.8)

Adds terminology_term and terminology_translation (docs/03-srs.md FR-166) and loads the terms that
ship with the tool (app/terminology_seed.py) with their translations as DRAFT proposals. The DDL
comes from docs/artifacts/schema.sql (app/schema_sql.py); a table is created only when it is missing,
and a term is loaded only when its code is not there yet.

Revision ID: e1b3f5a7c904
Revises: d0a2e4f6b893
Create Date: 2026-10-24 17:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.schema_sql import schema_statements, table_statements

revision = "e1b3f5a7c904"
down_revision = "d0a2e4f6b893"
branch_labels = None
depends_on = None

NEW_TABLES = ["terminology_term", "terminology_translation"]


def upgrade():
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    statements = schema_statements()
    for table in NEW_TABLES:
        if table not in existing:
            for stmt in table_statements(table, statements):
                op.execute(stmt)

    from app.terminology_seed import terms

    known = {row[0] for row in bind.execute(sa.text("SELECT code FROM terminology_term"))}
    languages = {row[0] for row in bind.execute(sa.text("SELECT code FROM lookup_language"))}
    for term in terms():
        if term["code"] in known:
            continue
        bind.execute(
            sa.text(
                "INSERT INTO terminology_term (code, category, english, definition, keep_english) "
                "VALUES (:code, :category, :english, :definition, :keep)"
            ),
            {
                "code": term["code"],
                "category": term["category"],
                "english": term["english"],
                "definition": term["definition"],
                "keep": 1 if term["keep_english"] else 0,
            },
        )
        term_id = bind.execute(
            sa.text("SELECT id FROM terminology_term WHERE code = :c"), {"c": term["code"]}
        ).scalar()
        for language, text in term["translations"].items():
            if language not in languages:
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO terminology_translation (term_id, language_code, text, status) "
                    "VALUES (:t, :l, :x, 'DRAFT')"
                ),
                {"t": term_id, "l": language, "x": text},
            )


def downgrade():
    for table in reversed(NEW_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table}")

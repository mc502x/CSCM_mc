"""StCd Owner role, three more languages with flags (schema v4.3)

Brings a database up to docs/artifacts/schema.sql v4.3 (docs/06-data-dictionary.md sections 2 and
8): the role STCD_OWNER, the languages French, Hindi and Georgian, flags in the language names, and
user.ui_language accepting the five language codes.

A fresh database already gets all of it from the baseline (which executes schema.sql verbatim), so
every step is guarded. The seed rows are added only when missing and the two old language names are
changed only while they still carry their original text, so a name an Administrator has edited is
kept.

user.ui_language is a CHECK constraint, which SQLite cannot widen in place: the table is rebuilt.
Most tables reference user(id), so the rebuild runs with `legacy_alter_table` on - the rename then
leaves those foreign keys pointing at the name `user`, which the new table takes over (the same
technique as the import_job rebuild of revision b3f5a7c9d124).

Revision ID: d4a6c8e0f236
Revises: b3f5a7c9d124
Create Date: 2026-10-23 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.schema_sql import schema_statements, table_statements

revision = "d4a6c8e0f236"
down_revision = "b3f5a7c9d124"
branch_labels = None
depends_on = None

STCD_OWNER = (6, "STCD_OWNER", "StCd Owner (Owner of the Status Code Library)")
# code, new label, sort_order, is_source
LANGUAGES = [
    ("en", "\U0001f1ec\U0001f1e7 English", 1, 1),
    ("de", "\U0001f1e9\U0001f1ea Deutsch", 2, 0),
    ("fr", "\U0001f1eb\U0001f1f7 Français", 3, 0),
    ("hi", "\U0001f1ee\U0001f1f3 हिन्दी (Hindi)", 4, 0),
    (
        "ka",
        "\U0001f1ec\U0001f1ea ქართული (Georgian)",
        5,
        0,
    ),
]
OLD_LABELS = {"en": "English", "de": "Deutsch"}


def _user_accepts_new_languages(bind) -> bool:
    sql = bind.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'user'")
    ).scalar()
    # a fresh database has the generic CHECK of v4.5, which accepts every code
    return bool(sql) and ("'ka'" in sql or "length(ui_language) = 2" in sql)


def upgrade():
    bind = op.get_bind()

    bind.execute(
        sa.text("INSERT OR IGNORE INTO role (id, code, label) VALUES (:i, :c, :l)"),
        {"i": STCD_OWNER[0], "c": STCD_OWNER[1], "l": STCD_OWNER[2]},
    )

    for code, label, sort_order, is_source in LANGUAGES:
        exists = bind.execute(
            sa.text("SELECT label FROM lookup_language WHERE code = :c"), {"c": code}
        ).first()
        if exists is None:
            bind.execute(
                sa.text(
                    "INSERT INTO lookup_language (code, label, sort_order, is_source) "
                    "VALUES (:c, :l, :s, :src)"
                ),
                {"c": code, "l": label, "s": sort_order, "src": is_source},
            )
        elif exists[0] == OLD_LABELS.get(code):
            bind.execute(
                sa.text("UPDATE lookup_language SET label = :l WHERE code = :c"),
                {"c": code, "l": label},
            )

    if not _user_accepts_new_languages(bind):
        columns = ", ".join(
            c["name"] for c in sa.inspect(bind).get_columns("user")
        )  # every column of the old table exists in the new one
        statements = schema_statements()
        op.execute("PRAGMA legacy_alter_table = ON")
        try:
            op.execute('ALTER TABLE "user" RENAME TO user_old')
            for stmt in table_statements("user", statements):
                op.execute(stmt)
            op.execute(f'INSERT INTO "user" ({columns}) SELECT {columns} FROM user_old')
            op.execute("DROP TABLE user_old")
        finally:
            op.execute("PRAGMA legacy_alter_table = OFF")


def downgrade():
    # The role and the languages may already be in use (users, translations): they stay, and the
    # guarded upgrade re-uses them. user keeps its wider CHECK for the same reason.
    pass

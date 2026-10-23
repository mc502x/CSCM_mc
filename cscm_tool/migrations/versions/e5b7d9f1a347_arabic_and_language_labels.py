"""Arabic, and language names as "<country letters> <name> <flag>" (schema v4.4)

Brings a database up to docs/artifacts/schema.sql v4.4: the language Arabic, language names that
carry the two country letters on the left and the flag emoji on the right, and user.ui_language
accepting the six language codes.

Every step is guarded. A language name is rewritten only while it still has the text an earlier
revision wrote (a plain name or the flag-first name of revision d4a6c8e0f236), so a name an
Administrator has edited is kept. user.ui_language is a CHECK constraint, so the table is rebuilt
(create the new table, copy, drop the old one, rename); migrations/env.py runs the migration with
foreign keys off and checks them at the end, so the tables that reference user stay intact.

Revision ID: e5b7d9f1a347
Revises: d4a6c8e0f236
Create Date: 2026-10-23 20:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.schema_sql import schema_statements, table_statements

revision = "e5b7d9f1a347"
down_revision = "d4a6c8e0f236"
branch_labels = None
depends_on = None

# code -> (label now, labels an earlier revision wrote), sort_order, is_source
LANGUAGES = [
    ("en", "GB English \U0001f1ec\U0001f1e7", ("English", "\U0001f1ec\U0001f1e7 English"), 1, 1),
    ("de", "DE Deutsch \U0001f1e9\U0001f1ea", ("Deutsch", "\U0001f1e9\U0001f1ea Deutsch"), 2, 0),
    (
        "fr",
        "FR Français \U0001f1eb\U0001f1f7",
        ("\U0001f1eb\U0001f1f7 Français",),
        3,
        0,
    ),
    (
        "hi",
        "IN हिन्दी (Hindi) \U0001f1ee\U0001f1f3",
        ("\U0001f1ee\U0001f1f3 हिन्दी (Hindi)",),
        4,
        0,
    ),
    (
        "ka",
        "GE ქართული (Georgian) \U0001f1ec\U0001f1ea",
        ("\U0001f1ec\U0001f1ea ქართული (Georgian)",),
        5,
        0,
    ),
    (
        "ar",
        "SA العربية (Arabic) \U0001f1f8\U0001f1e6",
        (),
        6,
        0,
    ),
]


def _user_accepts_arabic(bind) -> bool:
    sql = bind.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'user'")
    ).scalar()
    # a fresh database has the generic CHECK of v4.5, which accepts every code
    return bool(sql) and ("'ar'" in sql or "length(ui_language) = 2" in sql)


def upgrade():
    bind = op.get_bind()

    for code, label, earlier, sort_order, is_source in LANGUAGES:
        found = bind.execute(
            sa.text("SELECT label FROM lookup_language WHERE code = :c"), {"c": code}
        ).first()
        if found is None:
            bind.execute(
                sa.text(
                    "INSERT INTO lookup_language (code, label, sort_order, is_source) "
                    "VALUES (:c, :l, :s, :src)"
                ),
                {"c": code, "l": label, "s": sort_order, "src": is_source},
            )
        elif found[0] in earlier:
            bind.execute(
                sa.text("UPDATE lookup_language SET label = :l WHERE code = :c"),
                {"c": code, "l": label},
            )

    if not _user_accepts_arabic(bind):
        columns = ", ".join(c["name"] for c in sa.inspect(bind).get_columns("user"))
        statements = schema_statements()
        # legacy_alter_table: the rename must not rewrite the foreign keys of the tables that
        # reference user, they have to keep pointing at the name `user` the new table takes over.
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
    # Arabic and the new names may already be in use; they stay, the guarded upgrade re-uses them.
    pass

"""ten more languages, and a user.ui_language that needs no list (schema v4.5)

Adds Bengali, Marathi, Telugu, Tamil, Gujarati, Urdu, Kannada, Odia, Malayalam and Punjabi to the
language lookup, after Arabic, each named "<country letters> <name> (<English name>) <flag>". The
CHECK of user.ui_language no longer lists the codes (a two-letter lower-case code is enough; the
application decides which exist), so this is the last time the table is rebuilt for a language.
A CHECK constraint cannot be changed in place in SQLite: the table is rebuilt with
`legacy_alter_table` on, so the foreign keys of the tables that reference user keep pointing at the
name `user` (migrations/env.py switches foreign keys off for the migration and checks them at the
end).

Revision ID: a7d9b1c3e560
Revises: f6c8e0a2b459
Create Date: 2026-10-23 23:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.schema_sql import schema_statements, table_statements

revision = "a7d9b1c3e560"
down_revision = "f6c8e0a2b459"
branch_labels = None
depends_on = None

# code, name, sort_order
LANGUAGES = [
    ("bn", "IN বাংলা (Bengali) 🇮🇳", 7),
    ("mr", "IN मराठी (Marathi) 🇮🇳", 8),
    ("te", "IN తెలుగు (Telugu) 🇮🇳", 9),
    ("ta", "IN தமிழ் (Tamil) 🇮🇳", 10),
    ("gu", "IN ગુજરાતી (Gujarati) 🇮🇳", 11),
    ("ur", "PK اردو (Urdu) 🇵🇰", 12),
    ("kn", "IN ಕನ್ನಡ (Kannada) 🇮🇳", 13),
    ("or", "IN ଓଡ଼ିଆ (Odia) 🇮🇳", 14),
    ("ml", "IN മലയാളം (Malayalam) 🇮🇳", 15),
    ("pa", "IN ਪੰਜਾਬੀ (Punjabi) 🇮🇳", 16),
]


def _user_check_is_generic(bind) -> bool:
    sql = bind.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'user'")
    ).scalar()
    return bool(sql) and "length(ui_language) = 2" in sql


def upgrade():
    bind = op.get_bind()
    for code, label, sort_order in LANGUAGES:
        found = bind.execute(
            sa.text("SELECT 1 FROM lookup_language WHERE code = :c"), {"c": code}
        ).first()
        if found is None:
            bind.execute(
                sa.text(
                    "INSERT INTO lookup_language (code, label, sort_order, is_source) "
                    "VALUES (:c, :l, :s, 0)"
                ),
                {"c": code, "l": label, "s": sort_order},
            )

    if not _user_check_is_generic(bind):
        columns = ", ".join(c["name"] for c in sa.inspect(bind).get_columns("user"))
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
    # The languages may already be in use; they stay and the guarded upgrade re-uses them.
    pass

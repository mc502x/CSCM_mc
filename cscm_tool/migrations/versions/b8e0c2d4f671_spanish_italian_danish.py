"""Spanish, Italian and Danish; Georgian last (schema v4.6)

Adds Spanish, Italian and Danish to the language lookup after Punjabi and moves Georgian to the end
of the list (sort order 20). A fresh database has this from the baseline; an upgrade inserts the
three rows when they are missing and moves Georgian only while it still has the sort order an
earlier revision gave it (5), so a different order an Administrator chose is kept.

Revision ID: b8e0c2d4f671
Revises: a7d9b1c3e560
Create Date: 2026-10-24 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "b8e0c2d4f671"
down_revision = "a7d9b1c3e560"
branch_labels = None
depends_on = None

# code, label, sort_order
NEW = [
    ("es", "ES Espa\u00f1ol \U0001f1ea\U0001f1f8", 17),
    ("it", "IT Italiano \U0001f1ee\U0001f1f9", 18),
    ("da", "DK Dansk \U0001f1e9\U0001f1f0", 19),
]


def upgrade():
    bind = op.get_bind()
    for code, label, sort_order in NEW:
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
    bind.execute(
        sa.text("UPDATE lookup_language SET sort_order = 20 WHERE code = 'ka' AND sort_order = 5")
    )


def downgrade():
    bind = op.get_bind()
    bind.execute(
        sa.text("UPDATE lookup_language SET sort_order = 5 WHERE code = 'ka' AND sort_order = 20")
    )

"""the e-mail address of a user is fixed (schema v4.7)

Adds trg_user_email_immutable. Before it is created the addresses are lower-cased, as the
application now stores them, but only when that cannot make two of them equal (an address is
unique); with such a clash nothing is changed and the Administrator resolves it by hand.

Revision ID: c9f1d3e5a782
Revises: b8e0c2d4f671
Create Date: 2026-10-24 11:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.schema_sql import schema_statements, trigger_statement

revision = "c9f1d3e5a782"
down_revision = "b8e0c2d4f671"
branch_labels = None
depends_on = None

TRIGGER = "trg_user_email_immutable"


def upgrade():
    bind = op.get_bind()
    clash = bind.execute(
        sa.text("SELECT 1 FROM user GROUP BY lower(email) HAVING COUNT(*) > 1 LIMIT 1")
    ).first()
    op.execute(f"DROP TRIGGER IF EXISTS {TRIGGER}")
    if clash is None:
        op.execute("UPDATE user SET email = lower(email) WHERE email <> lower(email)")
    op.execute(trigger_statement(TRIGGER, schema_statements()))


def downgrade():
    op.execute(f"DROP TRIGGER IF EXISTS {TRIGGER}")

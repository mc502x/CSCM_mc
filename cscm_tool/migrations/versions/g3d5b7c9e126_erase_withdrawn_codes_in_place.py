"""a withdrawn code is erased in place (schema v4.9.2)

`status_code.deleted_at`: deleting a withdrawn code no longer removes the row, so that no id is ever
reused (SQLite hands out the highest id again after a delete, and an audit entry would then point at
a different code); the code gives up its identifier, reserved number, legacy number and PrgIdx_GUi
instead. The delete trigger is strict again: no non-sandbox code row is ever deleted. The DDL comes
from docs/artifacts/schema.sql (app/schema_sql.py).

Revision ID: g3d5b7c9e126
Revises: f2c4a6b8d015
Create Date: 2026-10-25 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.schema_sql import schema_statements, trigger_statement

revision = "g3d5b7c9e126"
down_revision = "f2c4a6b8d015"
branch_labels = None
depends_on = None

TRIGGER = "trg_prevent_nonsandbox_delete"


def upgrade():
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("status_code")}
    if "deleted_at" not in columns:
        op.execute("ALTER TABLE status_code ADD COLUMN deleted_at TEXT")
    op.execute(f"DROP TRIGGER IF EXISTS {TRIGGER}")
    op.execute(trigger_statement(TRIGGER, schema_statements()))


def downgrade():
    op.execute(f"DROP TRIGGER IF EXISTS {TRIGGER}")
    op.execute("ALTER TABLE status_code DROP COLUMN deleted_at")
    op.execute(
        "CREATE TRIGGER trg_prevent_nonsandbox_delete BEFORE DELETE ON status_code "
        "WHEN OLD.is_sandbox = 0 AND (OLD.withdrawn_at IS NULL OR EXISTS "
        "(SELECT 1 FROM status_code_revision r WHERE r.status_code_id = OLD.id)) BEGIN "
        "SELECT RAISE(ABORT, 'Only sandbox (is_sandbox=1) status codes may be deleted'); END"
    )

"""delete users with history and withdrawn codes (schema v4.9)

`user.deleted_at`: an account with history is erased (name, address, password) instead of
refused, so nothing it did loses its author and the audit log is never touched (BR-025). The trigger
that fixes the e-mail address lets the erasure through. `status_code.withdrawn_at`: set when the
last revision of a code was withdrawn; only such a code can be deleted, and the delete trigger now
says so (BR-026). A code that is already an empty shell is marked now. The DDL of the triggers comes
from docs/artifacts/schema.sql (app/schema_sql.py).

Revision ID: f2c4a6b8d015
Revises: e1b3f5a7c904
Create Date: 2026-10-25 09:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.schema_sql import schema_statements, trigger_statement

revision = "f2c4a6b8d015"
down_revision = "e1b3f5a7c904"
branch_labels = None
depends_on = None

TRIGGERS = ["trg_user_email_immutable", "trg_prevent_nonsandbox_delete"]


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade():
    for name in TRIGGERS:
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
    if "deleted_at" not in _columns("user"):
        op.execute("ALTER TABLE user ADD COLUMN deleted_at TEXT")
    if "withdrawn_at" not in _columns("status_code"):
        op.execute("ALTER TABLE status_code ADD COLUMN withdrawn_at TEXT")
        op.execute(
            "UPDATE status_code SET withdrawn_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') "
            "WHERE is_sandbox = 0 AND NOT EXISTS "
            "(SELECT 1 FROM status_code_revision r WHERE r.status_code_id = status_code.id)"
        )
    statements = schema_statements()
    for name in TRIGGERS:
        op.execute(trigger_statement(name, statements))


def downgrade():
    for name in TRIGGERS:
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
    op.execute("ALTER TABLE status_code DROP COLUMN withdrawn_at")
    op.execute("ALTER TABLE user DROP COLUMN deleted_at")
    op.execute(
        "CREATE TRIGGER trg_user_email_immutable BEFORE UPDATE OF email ON user "
        "WHEN NEW.email <> OLD.email BEGIN "
        "SELECT RAISE(ABORT, 'The e-mail address of a user cannot be changed'); END"
    )
    op.execute(
        "CREATE TRIGGER trg_prevent_nonsandbox_delete BEFORE DELETE ON status_code "
        "WHEN OLD.is_sandbox = 0 BEGIN "
        "SELECT RAISE(ABORT, 'Only sandbox (is_sandbox=1) status codes may be deleted'); END"
    )

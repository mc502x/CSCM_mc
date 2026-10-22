"""password history for the last-5 reuse block

Adds `user_password_history` (docs/artifacts/schema.sql, 11-security-architecture.md §4).
A fresh database already has it from the baseline; the statement is guarded so
`flask db upgrade` is also correct for a database created before this change.

Revision ID: c5e7a9b1d3f2
Revises: b4d2f6a8c0e1
Create Date: 2026-10-21 17:00:00.000000

"""

from alembic import op

revision = "c5e7a9b1d3f2"
down_revision = "b4d2f6a8c0e1"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_password_history (
            id              INTEGER PRIMARY KEY,
            user_id         INTEGER NOT NULL REFERENCES user(id),
            password_hash   TEXT NOT NULL,
            retired_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_pwhist_user ON user_password_history (user_id, id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS user_password_history")

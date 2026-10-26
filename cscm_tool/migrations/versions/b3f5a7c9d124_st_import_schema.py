"""Status code import from the generated StCd programs (schema v4.2)

Brings a database up to docs/artifacts/schema.sql v4.2 (docs/06-data-dictionary.md section 5a):
status_code.reserved_identifier with its unique index and the three triggers that guard the
reservation, import_job.source_format widened to 'ST' plus import_job.change_set_id, and the
import_source_item provenance table.

A fresh database already gets all of it from the baseline (which executes schema.sql verbatim), so
every step is guarded and a no-op when the object is already there; the DDL is taken from
schema.sql itself (app/schema_sql.py): one copy only.

import_job has to be rebuilt because SQLite cannot widen a CHECK constraint. change_request
references it, so the rebuild runs with `legacy_alter_table` on: the rename then leaves the foreign
key of change_request pointing at the name `import_job`, which the new table takes over.

Revision ID: b3f5a7c9d124
Revises: c9e2a4b6d815
Create Date: 2026-10-23 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.schema_sql import schema_statements, table_statements, trigger_statement

# ruff: noqa: E501  (SQL kept readable on long lines)

revision = "b3f5a7c9d124"
down_revision = "c9e2a4b6d815"
branch_labels = None
depends_on = None

RESERVED_COLUMN = (
    "reserved_identifier TEXT CHECK (reserved_identifier IS NULL "
    "OR reserved_identifier GLOB 'StCd-[0-9][0-9][0-9][0-9][0-9]')"
)
RESERVED_INDEX = "ux_status_code_reserved_identifier"
NEW_TRIGGERS = [
    "trg_identifier_matches_reservation",
    "trg_reservation_not_issued_elsewhere",
    "trg_identifier_not_reserved_elsewhere",
]
IMPORT_JOB_COLUMNS = (
    "id, requested_by, source_format, source_file_reference, row_count, status, created_count, "
    "error_count, error_report_reference, created_at, completed_at, processed_count, "
    "warning_count, import_mode, error_report_xlsx_reference"
)


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _columns(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def _object_exists(bind, kind: str, name: str) -> bool:
    return (
        bind.execute(
            sa.text("SELECT 1 FROM sqlite_master WHERE type = :kind AND name = :name"),
            {"kind": kind, "name": name},
        ).first()
        is not None
    )


def _import_job_accepts_st(bind) -> bool:
    sql = bind.execute(
        sa.text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'import_job'")
    ).scalar()
    return bool(sql) and "'ST'" in sql and "change_set_id" in sql


def upgrade():
    bind = op.get_bind()
    statements = schema_statements()

    # 1. The reservation column, its unique index and the guarding triggers.
    if "reserved_identifier" not in _columns(bind, "status_code"):
        op.execute(f"ALTER TABLE status_code ADD COLUMN {RESERVED_COLUMN}")
    if not _object_exists(bind, "index", RESERVED_INDEX):
        for stmt in table_statements("status_code", statements):
            if RESERVED_INDEX in stmt:
                op.execute(stmt)
    for name in NEW_TRIGGERS:
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
        op.execute(trigger_statement(name, statements))

    # 2. import_job: 'ST' source format and the change set link (a rebuild, see the docstring).
    if not _import_job_accepts_st(bind):
        op.execute("PRAGMA legacy_alter_table = ON")
        try:
            op.execute("ALTER TABLE import_job RENAME TO import_job_old")
            for stmt in table_statements("import_job", statements):
                op.execute(stmt)
            op.execute(
                f"INSERT INTO import_job ({IMPORT_JOB_COLUMNS}) "
                f"SELECT {IMPORT_JOB_COLUMNS} FROM import_job_old"
            )
            op.execute("DROP TABLE import_job_old")
        finally:
            op.execute("PRAGMA legacy_alter_table = OFF")

    # 3. Provenance of the imported programs.
    if "import_source_item" not in _tables(bind):
        for stmt in table_statements("import_source_item", statements):
            op.execute(stmt)


def downgrade():
    bind = op.get_bind()
    op.execute("DROP TABLE IF EXISTS import_source_item")
    for name in NEW_TRIGGERS:
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
    op.execute(f"DROP INDEX IF EXISTS {RESERVED_INDEX}")
    # import_job keeps its wider shape: narrowing the CHECK could reject rows already written.
    # SQLite cannot drop a column that carries a CHECK; reserved_identifier stays (always NULL
    # once nothing writes it) and the guarded upgrade re-uses it.
    if "reserved_identifier" in _columns(bind, "status_code"):
        try:
            op.execute("ALTER TABLE status_code DROP COLUMN reserved_identifier")
        except sa.exc.OperationalError:
            pass

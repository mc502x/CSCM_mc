"""PrgIdx_GUi, controller-specific program fields and the user-group levels (schema v4.1)

Brings a database up to docs/artifacts/schema.sql v4.1 (docs/06-data-dictionary.md sections 1, 2c,
2d, 2f, 9d.9): status_code.prg_idx with its unique index and the "frozen after release" trigger,
the optional "required from Review" trigger, the further Main Controller / Hub Controller columns on
status_code_revision, the 16 user-group slots with the per-revision read/write levels, and the default
levels on the eight audience lookups. The locked-revision trigger is recreated so it also covers the
new content columns.

A fresh database already gets all of it from the baseline (which executes schema.sql verbatim), so
every step is guarded and a no-op when the object is already there. DDL for new tables, the index,
the triggers and the seed UPDATEs is taken from schema.sql itself (app/schema_sql.py): one copy only.

Existing rows keep prg_idx NULL (the numbers exist only in the generated programs) and get no
user-group rows: the numeric levels are not derivable from the named access values for every code.

Revision ID: c9e2a4b6d815
Revises: a1d4f6b8c203
Create Date: 2026-10-23 14:00:00.000000

"""

import re

import sqlalchemy as sa
from alembic import op

from app.schema_sql import schema_statements, table_statements, trigger_statement

# ruff: noqa: E501  (SQL kept readable on long lines)

revision = "c9e2a4b6d815"
down_revision = "a1d4f6b8c203"
branch_labels = None
depends_on = None

LEVEL_TABLES = [
    "lookup_development_access",
    "lookup_sales_access",
    "lookup_tcc_access",
    "lookup_service_access",
    "lookup_top_access",
    "lookup_grid_operator_access",
    "lookup_service_partner_access",
    "lookup_customer_access",
]

_PROGRAM = "INTEGER NOT NULL DEFAULT 0"
_FLAG = "INTEGER CHECK ({c} IS NULL OR {c} IN (0,1))"

# (table, column, definition). Definitions mirror schema.sql.
REVISION_COLUMNS = [
    ("converter_reset_program", _PROGRAM),
    ("hydraulic_pump_program", _PROGRAM),
    ("gearbox_oil_pump_program", _PROGRAM),
    ("gearbox_oil_fan_program", _PROGRAM),
    ("gearbox_oil_heating_program", _PROGRAM),
    ("generator_fan_program", _PROGRAM),
    ("generator_heating_program", _PROGRAM),
    ("generator_bearing_lubrication_program", _PROGRAM),
    ("rotor_bearing_lubrication_program", _PROGRAM),
    ("anemometer_heating_program", _PROGRAM),
    ("medium_voltage_cb_program", _PROGRAM),
    ("tower_fan_program", _PROGRAM),
    ("transformer_oil_pump_program", _PROGRAM),
    ("zero_load_operation", _FLAG.format(c="zero_load_operation")),
    ("pitch_error_program", _PROGRAM),
    ("pitch_warning_program", _PROGRAM),
    ("rotor_brake_program", _PROGRAM),
    ("stop_program_40_flag", _FLAG.format(c="stop_program_40_flag")),
    ("stop_program_80_flag", _FLAG.format(c="stop_program_80_flag")),
    ("manual_operation_flag", _FLAG.format(c="manual_operation_flag")),
    ("automatic_operation_flag", _FLAG.format(c="automatic_operation_flag")),
    ("vane_position_flag", _FLAG.format(c="vane_position_flag")),
    (
        "operating_mode_mask",
        "INTEGER CHECK (operating_mode_mask IS NULL OR operating_mode_mask BETWEEN 0 AND 1048575)",
    ),
    (
        "task_call_frequency",
        "INTEGER CHECK (task_call_frequency IS NULL OR task_call_frequency >= 1)",
    ),
    ("availability_calc", _FLAG.format(c="availability_calc")),
]

NEW_COLUMNS = [
    (
        "status_code",
        "prg_idx",
        "INTEGER CHECK (prg_idx IS NULL OR prg_idx BETWEEN 1 AND 65535)",
    ),
    *[("status_code_revision", name, definition) for name, definition in REVISION_COLUMNS],
    *[
        (
            table,
            column,
            f"INTEGER CHECK ({column} IS NULL OR {column} BETWEEN 0 AND 255)",
        )
        for table in LEVEL_TABLES
        for column in ("default_read_level", "default_write_level")
    ],
]

NEW_TABLES = ["lookup_user_group_slot", "status_code_revision_user_group"]
NEW_TRIGGERS = [
    "trg_prevent_prg_idx_change_after_release",
    "trg_require_prg_idx_for_review",
]
PRG_IDX_INDEX = "ux_status_code_prg_idx"

# The "locked revision" trigger as it was before this migration, for downgrade.
PREVIOUS_LOCK_TRIGGER = """
CREATE TRIGGER trg_prevent_edit_locked_revision
BEFORE UPDATE OF title, description, status_category, available_group, alarm_flag,
    set_delay, reset_delay, brake_program, manual_reset_program, auto_reset_program,
    development_access, sales_access, tcc_access, service_access,
    turbine_operator_package_access, grid_operator_access, service_partner_access, customer_access,
    remedy_text, affected_component, related_status_codes, standard_references,
    applies_from_version_id, applies_to_version_id
ON status_code_revision
WHEN OLD.lifecycle_status IN ('APPROVED','RELEASED','ARCHIVED')
BEGIN
    SELECT RAISE(ABORT, 'Cannot edit a revision in APPROVED, RELEASED or ARCHIVED state');
END
"""

_DEFAULT_LEVEL_UPDATE = re.compile(
    r"^UPDATE lookup_\w+_access\s+SET default_read_level", re.IGNORECASE
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


def upgrade():
    bind = op.get_bind()
    statements = schema_statements()

    # 1. New tables first (the slot lookup before the table that references it).
    existing = _tables(bind)
    for table in NEW_TABLES:
        if table in existing:
            continue
        for stmt in table_statements(table, statements):
            op.execute(stmt)

    # 2. New columns. The seed levels are applied only when the default-level columns are new,
    #    so a re-run never overwrites a value an Administrator has since edited.
    seed_levels = "default_read_level" not in _columns(bind, LEVEL_TABLES[0])
    for table, column, definition in NEW_COLUMNS:
        if column not in _columns(bind, table):
            op.execute(f'ALTER TABLE "{table}" ADD COLUMN {column} {definition}')
    if seed_levels:
        for stmt in statements:
            if _DEFAULT_LEVEL_UPDATE.match(stmt):
                op.execute(stmt)

    # 3. PrgIdx_GUi is unique among non-sandbox codes.
    if not _object_exists(bind, "index", PRG_IDX_INDEX):
        for stmt in table_statements("status_code", statements):
            if PRG_IDX_INDEX in stmt:
                op.execute(stmt)

    # 4. Triggers: the locked-revision trigger now also covers the new content columns.
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_edit_locked_revision")
    op.execute(trigger_statement("trg_prevent_edit_locked_revision", statements))
    for name in NEW_TRIGGERS:
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
        op.execute(trigger_statement(name, statements))


def downgrade():
    bind = op.get_bind()

    # A trigger that names a column blocks DROP COLUMN, so the triggers go first.
    for name in NEW_TRIGGERS:
        op.execute(f"DROP TRIGGER IF EXISTS {name}")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_edit_locked_revision")
    op.execute(PREVIOUS_LOCK_TRIGGER)

    op.execute(f"DROP INDEX IF EXISTS {PRG_IDX_INDEX}")
    for table in reversed(NEW_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table}")

    for table, column, _definition in reversed(NEW_COLUMNS):
        if column in _columns(bind, table):
            try:
                op.execute(f'ALTER TABLE "{table}" DROP COLUMN {column}')
            except sa.exc.OperationalError:
                pass  # stays (always NULL / default) and the guarded upgrade re-uses it

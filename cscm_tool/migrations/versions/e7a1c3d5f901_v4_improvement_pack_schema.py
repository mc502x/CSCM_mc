"""v4 schema: improvement pack I-01..I-36 (docs/21-improvement-ideas.md)

Brings a database created before 2026-10-22 up to docs/artifacts/schema.sql v4:
new columns on status_code_revision / import_job / change_request / user / the
audience lookups / the group lookup, the widened export_job, the recreated
"locked revision" trigger, and the new tables with their seed rows.

A fresh database already gets all of it from the baseline (which executes
schema.sql verbatim), so every step is guarded and a no-op when the object is
already there. The DDL for new tables is taken from schema.sql itself
(app/schema_sql.py) so there is exactly one copy of it.

Revision ID: e7a1c3d5f901
Revises: d6f8b0c2e4a3
Create Date: 2026-10-22 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.schema_sql import schema_statements, table_statements, trigger_statement

# ruff: noqa: E501  (SQL kept readable on long lines)

revision = "e7a1c3d5f901"
down_revision = "d6f8b0c2e4a3"
branch_labels = None
depends_on = None

ACCESS_TABLES = [
    "lookup_development_access",
    "lookup_sales_access",
    "lookup_tcc_access",
    "lookup_service_access",
    "lookup_top_access",
    "lookup_grid_operator_access",
    "lookup_service_partner_access",
    "lookup_customer_access",
]

# (table, column, definition). Definitions mirror schema.sql.
NEW_COLUMNS = [
    ("status_code_revision", "row_version", "INTEGER NOT NULL DEFAULT 1"),
    ("status_code_revision", "updated_at", "TEXT"),
    (
        "status_code_revision",
        "remedy_text",
        "TEXT CHECK (remedy_text IS NULL OR length(remedy_text) <= 4000)",
    ),
    (
        "status_code_revision",
        "affected_component",
        "TEXT CHECK (affected_component IS NULL OR length(affected_component) <= 200)",
    ),
    (
        "status_code_revision",
        "related_status_codes",
        "TEXT CHECK (related_status_codes IS NULL OR length(related_status_codes) <= 500)",
    ),
    (
        "status_code_revision",
        "standard_references",
        "TEXT CHECK (standard_references IS NULL OR length(standard_references) <= 1000)",
    ),
    (
        "status_code_revision",
        "applies_from_version_id",
        "INTEGER REFERENCES lookup_controller_software_version(id)",
    ),
    (
        "status_code_revision",
        "applies_to_version_id",
        "INTEGER REFERENCES lookup_controller_software_version(id)",
    ),
    ("status_code_revision", "planned_effective_date", "TEXT"),
    ("status_code_revision", "planned_deprecation_date", "TEXT"),
    (
        "lookup_functional_system_group",
        "controller_type",
        "TEXT NOT NULL DEFAULT 'MAIN' CHECK (controller_type IN ('MAIN','HUB'))",
    ),
    ("user", "ui_language", "TEXT NOT NULL DEFAULT 'en' CHECK (ui_language IN ('en','de'))"),
    ("import_job", "processed_count", "INTEGER NOT NULL DEFAULT 0"),
    ("import_job", "warning_count", "INTEGER NOT NULL DEFAULT 0"),
    (
        "import_job",
        "import_mode",
        "TEXT NOT NULL DEFAULT 'CREATE' CHECK (import_mode IN ('CREATE','UPDATE'))",
    ),
    ("import_job", "error_report_xlsx_reference", "TEXT"),
    ("change_request", "change_set_id", "INTEGER REFERENCES change_set(id)"),
    *[
        (t, "audience_visible", "INTEGER NOT NULL DEFAULT 1 CHECK (audience_visible IN (0,1))")
        for t in ACCESS_TABLES
    ],
]

# Created in dependency order; each gets its indexes and seed rows from schema.sql.
NEW_TABLES = [
    "lookup_controller_software_version",
    "lookup_language",
    "change_set",
    "release_target_version",
    "export_profile",
    "cr_attachment",
    "revision_translation",
    "delegation",
    "field_comment",
    "review_checklist_item",
    "cr_checklist_confirmation",
    "saved_search",
    "notification",
    "login_attempt",
    "app_setting",
    "occurrence_import",
    "code_occurrence",
    "api_token",
    "webhook",
    "webhook_delivery",
    "hub_mc_mapping",
]

# The "locked revision" trigger as it was before v4, for downgrade.
OLD_LOCK_TRIGGER = """
CREATE TRIGGER trg_prevent_edit_locked_revision
BEFORE UPDATE OF title, description, status_category, available_group, alarm_flag,
    set_delay, reset_delay, brake_program, manual_reset_program, auto_reset_program,
    development_access, sales_access, tcc_access, service_access,
    turbine_operator_package_access, grid_operator_access, service_partner_access, customer_access
ON status_code_revision
WHEN OLD.lifecycle_status IN ('APPROVED','RELEASED','ARCHIVED')
BEGIN
    SELECT RAISE(ABORT, 'Cannot edit a revision in APPROVED, RELEASED or ARCHIVED state');
END
"""


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _columns(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade():
    bind = op.get_bind()
    statements = schema_statements()

    # 1. New tables first, so the REFERENCES in the ALTERs below point at something real.
    existing = _tables(bind)
    for table in NEW_TABLES:
        if table in existing:
            continue
        for stmt in table_statements(table, statements):
            op.execute(stmt)

    # 2. New columns.
    for table, column, definition in NEW_COLUMNS:
        if column not in _columns(bind, table):
            op.execute(f'ALTER TABLE "{table}" ADD COLUMN {column} {definition}')

    # 3. Data defaults that cannot be expressed as a column default.
    op.execute("UPDATE status_code_revision SET updated_at = created_at WHERE updated_at IS NULL")
    for table in ACCESS_TABLES:
        op.execute(f"UPDATE {table} SET audience_visible = 0 WHERE code = 'COVERT'")
    op.execute(
        "UPDATE lookup_functional_system_group SET controller_type = 'HUB' "
        "WHERE range_start >= 11000 AND controller_type = 'MAIN'"
    )

    # 4. The locked-revision trigger now also covers the new content fields.
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_edit_locked_revision")
    op.execute(trigger_statement("trg_prevent_edit_locked_revision", statements))

    # 5. export_job: wider CHECKs + integrity columns (a table rebuild; nothing references it).
    if "sha256" not in _columns(bind, "export_job"):
        op.execute("ALTER TABLE export_job RENAME TO export_job_old")
        for stmt in table_statements("export_job", statements):
            op.execute(stmt)
        op.execute(
            "INSERT INTO export_job (id, requested_by, export_type, export_scope_type, scope, "
            "release_id, status, created_at, completed_at, file_reference) "
            "SELECT id, requested_by, export_type, export_scope_type, scope, release_id, status, "
            "created_at, completed_at, file_reference FROM export_job_old"
        )
        op.execute("DROP TABLE export_job_old")


def downgrade():
    bind = op.get_bind()

    # Restore the narrower trigger first: a trigger that names a column blocks DROP COLUMN.
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_edit_locked_revision")
    op.execute(OLD_LOCK_TRIGGER)

    for table in reversed(NEW_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table}")

    # SQLite cannot drop a column that carries a foreign key; those stay (always NULL
    # once their parent tables are gone) and the guarded upgrade re-uses them.
    for table, column, _definition in reversed(NEW_COLUMNS):
        if column in _columns(bind, table):
            try:
                op.execute(f'ALTER TABLE "{table}" DROP COLUMN {column}')
            except sa.exc.OperationalError:
                pass
    # export_job keeps its wider shape: narrowing the CHECKs could reject rows already written.

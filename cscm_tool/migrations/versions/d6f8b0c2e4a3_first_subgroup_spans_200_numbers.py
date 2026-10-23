"""first subgroup of each Main Controller group covers the first 200 numbers

Business rule (2026-10-22): e.g. Tower 5000-5199, Generator 2000-2199. The nine
first subgroups were seeded with 100 numbers; this widens them to 200. A fresh
database already gets the new ranges from the baseline (schema.sql), so the
update only touches rows that still have the old 100-number width, and never
widens one into a neighbouring subgroup.

Revision ID: d6f8b0c2e4a3
Revises: c5e7a9b1d3f2
Create Date: 2026-10-22 11:30:00.000000

"""

from alembic import op

# ruff: noqa: E501  (SQL kept readable on long lines)

revision = "d6f8b0c2e4a3"
down_revision = "c5e7a9b1d3f2"
branch_labels = None
depends_on = None

FIRST_SUBGROUP_CODES = (
    "010xx",
    "020xx",
    "030xx",
    "040xx",
    "050xx",
    "060xx",
    "070xx",
    "080xx",
    "090xx",
)


def _codes() -> str:
    return ", ".join(f"'{c}'" for c in FIRST_SUBGROUP_CODES)


def upgrade():
    op.execute(
        f"""
        UPDATE lookup_functional_subgroup
           SET sub_range_end = sub_range_start + 199
         WHERE code IN ({_codes()})
           AND sub_range_end = sub_range_start + 99
           AND NOT EXISTS (
                SELECT 1 FROM lookup_functional_subgroup other
                 WHERE other.functional_system_group_id = lookup_functional_subgroup.functional_system_group_id
                   AND other.id <> lookup_functional_subgroup.id
                   AND other.sub_range_start <= lookup_functional_subgroup.sub_range_start + 199
                   AND other.sub_range_end >= lookup_functional_subgroup.sub_range_start
           )
        """
    )


def downgrade():
    op.execute(
        f"""
        UPDATE lookup_functional_subgroup
           SET sub_range_end = sub_range_start + 99
         WHERE code IN ({_codes()})
           AND sub_range_end = sub_range_start + 199
        """
    )

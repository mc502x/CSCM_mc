"""align the Hub Controller sub-bands to the hundreds digit

Business rule (docs/05-governance-handbook.md section 2): sub-bands are aligned to the hundreds
digit, so `12-3xx` owns 12300-12399. The Hub subgroups were seeded from the legacy export, which
counted from x001 (Pitch Drivers 12301-12400, Control System 11000-11100 = 101 numbers). This shifts
each one down by one number. A fresh database already gets the aligned ranges from the baseline
(schema.sql); the update only touches rows that still have the old range, and refuses to run if a
status code has already been allocated in a number that would leave its subgroup (none exist yet).

Revision ID: a1d4f6b8c203
Revises: f8b2d4e6a012
Create Date: 2026-10-23 12:00:00.000000

"""

from alembic import op
from sqlalchemy import text

# ruff: noqa: E501  (SQL kept readable on long lines)

revision = "a1d4f6b8c203"
down_revision = "f8b2d4e6a012"
branch_labels = None
depends_on = None

# (group code, group range_start, subgroup code, old start, old end, new start, new end)
HUB = [
    ("WTUR", 11000, "11-0xx", 11000, 11100, 11000, 11099),
    ("WTUR", 11000, "11-1xxA", 11101, 11150, 11100, 11149),
    ("WTUR", 11000, "11-1xxB", 11151, 11200, 11150, 11199),
    ("WROT", 12000, "12-0xx", 12001, 12050, 12000, 12049),
    ("WROT", 12000, "12-0xxB", 12051, 12200, 12050, 12199),
    ("WROT", 12000, "12-2xx", 12201, 12250, 12200, 12249),
    ("WROT", 12000, "12-2xxB", 12251, 12300, 12250, 12299),
    ("WROT", 12000, "12-3xx", 12301, 12400, 12300, 12399),
    ("WROT", 12000, "12-4xx", 12401, 12500, 12400, 12499),
    ("WROT", 12000, "12-5xx", 12501, 12600, 12500, 12599),
    ("WPPD", 13000, "13-0xx", 13001, 13100, 13000, 13099),
]


def _shift(
    connection, old_start_index: int, old_end_index: int, new_start_index: int, new_end_index: int
):
    for row in HUB:
        group, group_start, code = row[0], row[1], row[2]
        old = (row[old_start_index], row[old_end_index])
        new = (row[new_start_index], row[new_end_index])
        found = connection.execute(
            text(
                "SELECT s.id FROM lookup_functional_subgroup s "
                "JOIN lookup_functional_system_group g ON g.id = s.functional_system_group_id "
                "WHERE g.code = :g AND g.range_start = :gs AND s.code = :c "
                "AND s.sub_range_start = :a AND s.sub_range_end = :b"
            ),
            {"g": group, "gs": group_start, "c": code, "a": old[0], "b": old[1]},
        ).first()
        if found is None:
            continue  # already aligned (fresh database) or changed by an Administrator
        stranded = connection.execute(
            text(
                "SELECT status_code_identifier FROM status_code sc "
                "WHERE sc.functional_subgroup_id = :s AND sc.status_code_identifier GLOB 'StCd-[0-9]*' "
                "AND (CAST(SUBSTR(sc.status_code_identifier, 6) AS INTEGER) < :na "
                "  OR CAST(SUBSTR(sc.status_code_identifier, 6) AS INTEGER) > :nb) LIMIT 1"
            ),
            {"s": found[0], "na": new[0], "nb": new[1]},
        ).first()
        if stranded is not None:
            raise RuntimeError(
                f"{stranded[0]} is allocated in subgroup {code} but outside its new band "
                f"{new[0]}-{new[1]}; resolve this before aligning the Hub bands."
            )
        connection.execute(
            text(
                "UPDATE lookup_functional_subgroup SET sub_range_start = :a, sub_range_end = :b WHERE id = :i"
            ),
            {"a": new[0], "b": new[1], "i": found[0]},
        )


def upgrade():
    _shift(op.get_bind(), 3, 4, 5, 6)


def downgrade():
    _shift(op.get_bind(), 5, 6, 3, 4)

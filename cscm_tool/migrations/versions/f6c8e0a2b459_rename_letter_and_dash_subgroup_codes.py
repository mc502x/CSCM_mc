"""rename the subgroup codes that carried a letter or an extra dash

The Main Controller sub-bands of the 099xx hundred were called `099xx-a` ... `099xx-f`, and the
Hub Controller subgroups `11-0xx`, `11-1xxA`, `12-0xxB` and so on. A letter after an x reads badly
and the Hub names carried a dash the Main names do not. The new code is the digits of the first
number of the band with `x` for the free positions: `110xx` owns 11000-11099 (like `010xx`), and a
band shorter than a hundred is named by its first ten with a digit in place of the second x, so
`0996x` is 9960-9969, `0990x` is 9900-9929 and `1110x` is 11100-11149. The range column always
shows the true band. Rows are matched on group, range and old code, so a subgroup an Administrator
has renamed or changed since is left alone; a fresh database has the new codes from the baseline.

Revision ID: f6c8e0a2b459
Revises: e5b7d9f1a347
Create Date: 2026-10-23 22:00:00.000000

"""

from alembic import op
from sqlalchemy import text

revision = "f6c8e0a2b459"
down_revision = "e5b7d9f1a347"
branch_labels = None
depends_on = None

# (group code, group range_start, old code, new code, sub_range_start, sub_range_end)
RENAMES = [
    ("WTUR", 9000, "099xx-a", "0990x", 9900, 9929),
    ("WTUR", 9000, "099xx-b", "0993x", 9930, 9959),
    ("WTUR", 9000, "099xx-c", "0996x", 9960, 9969),
    ("WTUR", 9000, "099xx-d", "0997x", 9970, 9979),
    ("WTUR", 9000, "099xx-e", "0998x", 9980, 9989),
    ("WTUR", 9000, "099xx-f", "0999x", 9990, 9999),
    ("WTUR", 11000, "11-0xx", "110xx", 11000, 11099),
    ("WTUR", 11000, "11-1xxA", "1110x", 11100, 11149),
    ("WTUR", 11000, "11-1xxB", "1115x", 11150, 11199),
    ("WROT", 12000, "12-0xx", "1200x", 12000, 12049),
    ("WROT", 12000, "12-0xxB", "1205x", 12050, 12199),
    ("WROT", 12000, "12-2xx", "1220x", 12200, 12249),
    ("WROT", 12000, "12-2xxB", "1225x", 12250, 12299),
    ("WROT", 12000, "12-3xx", "123xx", 12300, 12399),
    ("WROT", 12000, "12-4xx", "124xx", 12400, 12499),
    ("WROT", 12000, "12-5xx", "125xx", 12500, 12599),
    ("WPPD", 13000, "13-0xx", "130xx", 13000, 13099),
]


def _rename(old_index: int, new_index: int) -> None:
    connection = op.get_bind()
    for row in RENAMES:
        group, group_start = row[0], row[1]
        connection.execute(
            text(
                "UPDATE lookup_functional_subgroup SET code = :new "
                "WHERE code = :old AND sub_range_start = :a AND sub_range_end = :b "
                "AND functional_system_group_id IN (SELECT id FROM lookup_functional_system_group "
                "WHERE code = :g AND range_start = :gs)"
            ),
            {
                "new": row[new_index],
                "old": row[old_index],
                "a": row[4],
                "b": row[5],
                "g": group,
                "gs": group_start,
            },
        )


def upgrade():
    _rename(2, 3)


def downgrade():
    _rename(3, 2)

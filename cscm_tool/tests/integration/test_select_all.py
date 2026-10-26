"""A list with a checkbox per row has a checkbox in its header that ticks them all (the helper is
`data-check-all` in app/static/js/app.js). Requirements: FR-180, FR-159, NFR-007.

TC-070 (screens of the bulk work), TC-036.
"""

import re
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[2] / "app" / "templates"
ROW_BOXES = re.compile(r'<input type="checkbox"[^>]*name="(ids|cr_ids|revision_ids)"')


def test_every_list_with_a_checkbox_per_row_can_be_selected_as_a_whole():
    missing = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        if ROW_BOXES.search(text) and "data-check-all" not in text:
            missing.append(path.relative_to(TEMPLATES).as_posix())
    assert missing == []


def test_the_header_box_and_the_row_boxes_share_their_class():
    for name in (
        "admin/withdrawn_codes",
        "change_sets/detail",
        "change_sets/workbench",
        "releases/builder",
    ):
        text = (TEMPLATES / f"{name}.html").read_text(encoding="utf-8")
        cls = re.search(r'data-check-all="([\w-]+)"', text).group(1)
        assert re.search(rf'<input type="checkbox" class="{cls}" name="', text), name

"""Dark mode (docs/10-ui-ux-specification.md section 13, FR-183): the dark palette meets the same
contrast rules as the light one, no colour hides in a rule where the theme cannot reach it, the
print stays light, and the theme choice is on every page and works without inline script.

TC-049. Requirements: FR-183, FR-155, NFR-010, SEC-025.
"""

import re
from pathlib import Path

import pytest

from tests.helpers import login_as, make_cast
from tests.system.test_accessibility import CSS, contrast

STATIC = Path(__file__).resolve().parents[2] / "app" / "static"


def _block(start: str) -> str:
    begin = CSS.index(start)
    depth, i = 0, CSS.index("{", begin)
    for j in range(i, len(CSS)):
        depth += CSS[j] == "{"
        depth -= CSS[j] == "}"
        if depth == 0:
            return CSS[i + 1 : j]
    raise AssertionError(start)


def _tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", block))


@pytest.fixture(scope="module")
def light() -> dict[str, str]:
    return {**_tokens(_block(":root {")), **_tokens(_block(":root {\n  --sla-ok-bg"))}


@pytest.fixture(scope="module")
def dark(light) -> dict[str, str]:
    return {**light, **_tokens(_block(':root[data-theme="dark"] {'))}


def test_the_dark_palette_meets_aa_on_its_backgrounds(dark):
    t = dark
    pairs = {
        "text on background": (t["ot-text"], t["ot-background"]),
        "text on surface": (t["ot-text"], t["ot-surface-raised"]),
        "muted on surface": (t["ot-muted"], t["ot-surface-raised"]),
        "muted on background": (t["ot-muted"], t["ot-background"]),
        "primary (links) on surface": (t["ot-primary"], t["ot-surface-raised"]),
        "primary (links) on background": (t["ot-primary"], t["ot-background"]),
        "text on primary (buttons)": (t["on-primary"], t["ot-primary"]),
        "text on primary hover": (t["on-primary"], t["ot-primary-hover"]),
        "text on danger (button, bell)": (t["on-danger"], t["ot-error"]),
        "text on danger hover": (t["on-danger"], t["danger-hover"]),
        "error on surface": (t["ot-error"], t["ot-surface-raised"]),
        "error on its tint": (t["ot-error"], t["color-danger-bg"]),
        "success on surface": (t["ot-success"], t["ot-surface-raised"]),
        "success on its tint": (t["ot-success"], t["tint-success-bg"]),
        "info on its tint": (t["tint-info-fg"], t["tint-info-bg"]),
        "warning on its tint": (t["tint-warn-fg"], t["tint-warn-bg"]),
        "text on the done slot": (t["ot-text"], t["tint-done-bg"]),
        "text on the old side of a diff": (t["ot-text"], t["diff-old-bg"]),
        "text on the new side of a diff": (t["ot-text"], t["diff-new-bg"]),
        "text on code": (t["ot-text"], t["code-bg"]),
        "text on a Main Controller row": (t["ot-text"], t["controller-mc-row"]),
        "text on a Hub Controller row": (t["ot-text"], t["controller-hc-row"]),
        "text on a reviewed cell": (t["ot-text"], t["review-ok-bg"]),
        "text on a cell in progress": (t["ot-text"], t["review-progress-bg"]),
        "text on a changed cell": (t["ot-text"], t["review-changed-bg"]),
        "focus ring on surface": (t["focus-ring"], t["ot-surface-raised"]),
        "focus ring on background": (t["focus-ring"], t["ot-background"]),
    }
    failures = {n: round(contrast(*p), 2) for n, p in pairs.items() if contrast(*p) < 4.5}
    assert failures == {}


def test_every_badge_and_sla_pill_meets_aa_in_the_dark_theme(dark):
    pairs = {}
    for name in ("draft", "review", "pending", "approved", "released", "deprecated", "archived"):
        pairs[f"badge {name}"] = (dark[f"badge-{name}-fg"], dark[f"badge-{name}-bg"])
    for name in ("ok", "amber", "red"):
        pairs[f"sla {name}"] = (dark[f"sla-{name}-fg"], dark[f"sla-{name}-bg"])
    failures = {n: round(contrast(*p), 2) for n, p in pairs.items() if contrast(*p) < 4.5}
    assert failures == {}


def test_the_dark_theme_gives_every_light_tint_a_dark_value(light):
    """A token added to the light palette without a dark twin would stay light on a dark page."""
    dark_block = _block(':root[data-theme="dark"] {')
    dark_names = set(re.findall(r"--([\w-]+):", dark_block))
    # the focus-ring and the --ot-/--color- tokens of the base palette are themed too
    themed = {
        n for n in re.findall(r"--([\w-]+):", _block(":root {")) if not n.startswith("radius")
    }
    themed -= {"ot-font-heading", "ot-font-body", "color-primary", "color-primary-hover"}
    themed -= {"color-bg", "color-surface", "color-border", "color-text", "color-muted"}
    themed -= {"color-danger", "color-success", "color-scheme"}
    assert sorted(themed - dark_names) == []


def test_colours_are_only_written_out_where_the_dark_theme_cannot_matter():
    """Outside the token blocks a hex colour is allowed only for fills that carry their own text
    colour (roles, controller chips, confidence) and the white/dark text on them."""
    allowed = ("role-", "controller-chip", "controller-row--", ".conf", 'html[dir="rtl"] .role-row')
    outside = CSS
    for start in (":root {", ":root {\n  --sla-ok-bg", ':root[data-theme="dark"] {'):
        block = _block(start)
        outside = outside.replace(block, "")
    outside = re.sub(r"/\*.*?\*/", "", outside, flags=re.S)
    offenders = [
        line.strip()[:80]
        for line in outside.splitlines()
        if re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\((?!0, 0, 0)", line)  # a black shadow suits both
        and not any(a in line for a in allowed)
    ]
    assert offenders == []


def test_the_dark_theme_is_for_the_screen_only():
    before = CSS[: CSS.index(':root[data-theme="dark"] {')]
    assert before.rstrip().endswith("@media screen {")


def test_theme_js_is_a_plain_file_that_follows_the_system_and_remembers_the_choice():
    js = (STATIC / "js" / "theme.js").read_text(encoding="utf-8")
    assert "prefers-color-scheme: dark" in js and "localStorage" in js and "try" in js
    assert "data-theme" in js and "http" not in js and "eval(" not in js


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


def test_the_login_page_and_every_signed_in_page_offer_the_theme_choice(client, cast):
    guest = client.get("/login").get_data(as_text=True)
    assert guest.count("data-theme-select") == 1 and "js/theme.js" in guest
    assert guest.index("js/theme.js") < guest.index("css/app.css")  # coloured before it is painted
    for role in ("admin", "engineer", "viewer"):
        login_as(client, cast[role])
        page = client.get("/status-codes").get_data(as_text=True)
        assert page.count("data-theme-select") == 1 and "js/theme.js" in page
        for value, label in (("auto", "Automatic (system)"), ("light", "Light"), ("dark", "Dark")):
            assert f'<option value="{value}">{label}</option>' in page
        assert "<script>" not in page  # the strict Content-Security-Policy stays as it is
        client.post("/logout")


def test_the_theme_choice_is_translated(client, cast):
    login_as(client, cast["engineer"])
    client.post("/language", data={"lang": "de"})
    page = client.get("/status-codes").get_data(as_text=True)
    assert "Automatisch (System)" in page and ">Dunkel<" in page and ">Hell<" in page

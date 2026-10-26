"""I-22 accessibility (WCAG 2.1 AA, docs/10-ui-ux-specification.md §12): colour contrast of the
design tokens, and structural checks on the rendered pages (language, landmarks, skip link,
labelled controls, table header scope, no images without text alternative).

TC-049. Requirements: FR-155, NFR-010.
"""

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from tests.helpers import create_draft, login_as, make_cast

CSS = (Path(__file__).resolve().parents[2] / "app" / "static" / "css" / "app.css").read_text(
    encoding="utf-8"
)


def _tokens() -> dict[str, str]:
    root = CSS[CSS.index(":root") : CSS.index("}", CSS.index(":root"))]
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", root))


def _luminance(hex_color: str) -> float:
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    a, b = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def test_the_contrast_helper_matches_the_wcag_reference_values():
    assert contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast("#777777", "#ffffff") == pytest.approx(4.48, abs=0.02)


def test_text_tokens_meet_aa_on_their_backgrounds():
    t = _tokens()
    pairs = {
        "text on background": (t["ot-text"], t["ot-background"]),
        "text on surface": (t["ot-text"], t["ot-surface-raised"]),
        "muted on surface": (t["ot-muted"], t["ot-surface-raised"]),
        "muted on background": (t["ot-muted"], t["ot-background"]),
        "primary on surface": (t["ot-primary"], t["ot-surface-raised"]),
        "primary on background": (t["ot-primary"], t["ot-background"]),
        "white on primary (buttons)": ("#ffffff", t["ot-primary"]),
        "white on primary hover": ("#ffffff", t["ot-primary-hover"]),
        "error on surface": (t["ot-error"], t["ot-surface-raised"]),
        "error on its tint": (t["ot-error"], t["color-danger-bg"]),
        "success on surface": (t["ot-success"], t["ot-surface-raised"]),
    }
    failures = {n: round(contrast(*p), 2) for n, p in pairs.items() if contrast(*p) < 4.5}
    assert failures == {}


def test_every_state_badge_meets_aa():
    t = _tokens()
    badges = sorted(
        {k[len("badge-") : -len("-bg")] for k in t if k.startswith("badge-") and k.endswith("-bg")}
    )
    assert len(badges) >= 6
    failures = {
        name: round(contrast(t[f"badge-{name}-fg"], t[f"badge-{name}-bg"]), 2)
        for name in badges
        if contrast(t[f"badge-{name}-fg"], t[f"badge-{name}-bg"]) < 4.5
    }
    assert failures == {}


def test_the_stylesheet_honours_user_preferences():
    assert "prefers-reduced-motion" in CSS and ":focus-visible" in CSS
    assert ".skip-link" in CSS


class _Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = None
        self.mains = 0
        self.skip_link = False
        self.nav_labelled = []
        self.labels_for: set[str] = set()
        self.controls: list[dict] = []
        self.label_depth = 0
        self.images_without_alt = 0
        self.th_without_scope = 0
        self.buttons_without_name = 0
        self._button: dict | None = None
        self.headings: list[int] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "main":
            self.mains += 1
        elif tag == "a" and "skip-link" in (a.get("class") or ""):
            self.skip_link = a.get("href") == "#main"
        elif tag == "nav":
            self.nav_labelled.append(bool(a.get("aria-label") or a.get("aria-labelledby")))
        elif tag == "label":
            self.label_depth += 1
            if a.get("for"):
                self.labels_for.add(a["for"])
        elif tag in ("input", "select", "textarea"):
            if a.get("type") not in ("hidden", "submit", "button"):
                self.controls.append({**a, "tag": tag, "in_label": self.label_depth > 0})
        elif tag == "img" and a.get("alt") is None:
            self.images_without_alt += 1
        elif tag == "th" and not a.get("scope"):
            self.th_without_scope += 1
        elif tag == "button":
            self._button = {"named": bool(a.get("aria-label") or a.get("title")), "text": ""}
        elif tag in ("h1", "h2", "h3", "h4"):
            self.headings.append(int(tag[1]))

    def handle_endtag(self, tag):
        if tag == "label":
            self.label_depth = max(0, self.label_depth - 1)
        elif tag == "button" and self._button is not None:
            if not (self._button["named"] or self._button["text"].strip()):
                self.buttons_without_name += 1
            self._button = None

    def handle_data(self, data):
        if self._button is not None:
            self._button["text"] += data


def _audit_page(html: str) -> list[str]:
    page = _Page()
    page.feed(html)
    problems = []
    if page.lang not in ("en", "de"):
        problems.append(f"html lang is {page.lang!r}")
    if page.mains != 1:
        problems.append(f"{page.mains} <main> landmarks")
    if not page.skip_link:
        problems.append("no skip link to #main")
    if len(page.nav_labelled) > 1 and not all(page.nav_labelled):
        problems.append("several <nav> landmarks without an aria-label")
    for control in page.controls:
        named = (
            control["in_label"]
            or control.get("id") in page.labels_for
            or control.get("aria-label")
            or control.get("aria-labelledby")
            or control.get("title")
        )
        if not named:
            problems.append(f"unlabelled {control['tag']} name={control.get('name')!r}")
    if page.images_without_alt:
        problems.append(f"{page.images_without_alt} <img> without alt")
    if page.th_without_scope:
        problems.append(f"{page.th_without_scope} <th> without scope")
    if page.buttons_without_name:
        problems.append(f"{page.buttons_without_name} buttons without an accessible name")
    if page.headings and page.headings[0] != 1:
        problems.append(f"first heading is h{page.headings[0]}")
    for before, after in zip(page.headings, page.headings[1:], strict=False):
        if after - before > 1:
            problems.append(f"heading level jumps h{before} -> h{after}")
            break
    return problems


@pytest.fixture()
def pages(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, cr_id = create_draft(app, client, cast, wcnv_ids)
    login_as(client, cast["admin"])
    return client, revision["status_code_id"], cr_id


STATIC_PAGES = (
    "/",
    "/status-codes",
    "/status-codes/new",
    "/change-requests/mine",
    "/change-requests/review-queue",
    "/releases",
    "/releases/new",
    "/exports",
    "/imports/new",
    "/imports/reconciliation",
    "/notifications",
    "/delegation",
    "/help",
    "/account",
    "/software-versions",
    "/change-sets",
    "/hub-consolidation",
    "/admin/users",
    "/admin/lookups",
    "/admin/audit-log",
    "/admin/stalled",
    "/admin/settings",
    "/admin/integrations",
    "/admin/operations",
    "/admin/review-checklist",
    "/admin/export-profiles",
    "/reports/catalogue-health",
    "/reports/success-metrics",
    "/reports/fleet-feedback",
)


@pytest.mark.parametrize("lang", ["en", "de"])
def test_every_page_is_structurally_accessible(pages, lang):
    client, sc_id, cr_id = pages
    client.post("/language", data={"lang": lang})
    failures = {}
    for path in (
        *STATIC_PAGES,
        f"/status-codes/{sc_id}",
        f"/change-requests/{cr_id}",
        f"/status-codes/{sc_id}/translations",
    ):
        response = client.get(path)
        if response.status_code != 200:
            failures[path] = [f"HTTP {response.status_code}"]
            continue
        problems = _audit_page(response.get_data(as_text=True))
        if problems:
            failures[path] = problems
    assert failures == {}


def test_the_chief_engineers_queue_is_accessible(app, client, make_user):
    login_as(client, make_cast(make_user)["chief_engineer"])
    assert _audit_page(client.get("/change-requests/approval-queue").get_data(as_text=True)) == []


def test_the_login_page_is_accessible(client):
    assert _audit_page(client.get("/login").get_data(as_text=True)) == []


def test_status_is_never_conveyed_by_colour_alone(pages):
    """Every state badge carries the state as text, not only a colour."""
    client, sc_id, _ = pages
    html = client.get("/status-codes").get_data(as_text=True)
    badges = re.findall(r'class="badge[^"]*"[^>]*>([^<]*)<', html)
    assert badges and all(b.strip() for b in badges)

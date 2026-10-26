"""The content of the two decks of the design showcase (FR-186): a short one for management and a
walkthrough for the team. Numbers (version, tests, coverage, requirements, what was delivered) are
read from the repository at build time, so the decks follow every release."""

import re
from dataclasses import dataclass
from pathlib import Path

from app import branding

from .capture import Shot
from .deck import Para, Slide

REPO = Path(__file__).resolve().parents[3]
DOCS = REPO / "docs"

NAVY, INK, MUTED = "002E6D", "1A1D21", "5F6B7A"
TINT, PAGE, SKY, AMBER, GREEN, RED = "E8EEF6", "F7F9FB", "8AB4F8", "E8A317", "1E7F4C", "BA1A1A"
WHITE = "FFFFFF"
LEFT, TOP = 0.6, 1.3


# ----------------------------------------------------------------------------------------- facts
@dataclass
class Facts:
    version: str
    date: str
    tests: str = "n/a"
    coverage: str = "n/a"
    requirements: str = "n/a"
    operations: str = "n/a"
    tables: str = "n/a"
    languages: str = "19"
    delivered: tuple[tuple[str, str, str], ...] = ()


def gather(version: str, date: str) -> Facts:
    facts = Facts(version, date)
    report = (DOCS / "24-test-report.md").read_text(encoding="utf-8")
    if m := re.search(r"\| Tests \| \*\*(\d+)\*\* run — (\d+) passed, (\d+) failed", report):
        facts.tests = f"{int(m.group(2)):,}"
    if m := re.search(r"Line coverage \(`app/`\) \| \*\*(\d+)%\*\*", report):
        facts.coverage = m.group(1) + " %"
    srs = (DOCS / "03-srs.md").read_text(encoding="utf-8")
    ids = set(re.findall(r"^- \*\*((?:FR|NFR|BR|SEC)-[\w]+)\*\*", srs, re.M))
    security = (DOCS / "11-security-architecture.md").read_text(encoding="utf-8")
    ids |= set(re.findall(r"^- \*\*(SEC-[\w]+)\*\*", security, re.M))
    if ids:
        facts.requirements = f"{len(ids):,}"
    spec = (DOCS / "artifacts" / "openapi.yaml").read_text(encoding="utf-8")
    facts.operations = str(len(re.findall(r"^    (?:get|post|put|patch|delete):", spec, re.M)))
    schema = (DOCS / "artifacts" / "schema.sql").read_text(encoding="utf-8")
    facts.tables = str(len(re.findall(r"^CREATE TABLE", schema, re.M)))
    ideas = (DOCS / "21-improvement-ideas.md").read_text(encoding="utf-8").splitlines()
    rows = []
    for line in ideas:
        if m := re.match(
            r"^\| \*\*(.+?)\*\*[:\s]*(.*?)\| (v[\d.]+(?: / v[\d.]+)?) \| (.+?) \|$", line
        ):
            what = re.split(r"[:;(]", re.sub(r"\s+", " ", m.group(1)).replace("`", ""))[0].strip(
                " :—-"
            )
            rows.append((what[:70], m.group(3), m.group(4)))
    facts.delivered = tuple(rows[-6:])
    return facts


def shots(ids: dict) -> list[Shot]:
    """Every screenshot of both decks; `ids` are the keys of the demo data."""
    phone = (
        500,
        1000,
    )  # a browser window is never narrower than about 500 px; below 768 px the layout is the phone's
    tall = {
        "size": (1200, 1480),
        "skip": (170, 900),
        "crop_left": 256,
    }  # top of the page, then the table
    return [
        Shot("login", "/login", None),
        Shot("login_dark", "/login", None, dark=True),
        Shot("dashboard", "/", "engineer"),
        Shot("dashboard_dark", "/", "engineer", dark=True),
        Shot("dashboard_admin", "/", "admin"),
        Shot("list", "/status-codes", "admin", **tall),
        Shot("list_drafts", "/status-codes?lifecycle_status=DRAFT", "engineer", **tall),
        Shot("detail", f"/status-codes/{ids['released_code']}", "admin"),
        Shot("detail_dark", f"/status-codes/{ids['released_code']}", "admin", dark=True),
        Shot("new_form", "/status-codes/new", "engineer"),
        Shot("my_requests", "/change-requests/mine", "engineer"),
        Shot("review_queue", "/change-requests/review-queue", "reviewer"),
        Shot("approval_queue", "/change-requests/approval-queue", "chief"),
        Shot("cr_detail", f"/change-requests/{ids['pending_cr']}", "chief"),
        Shot("change_sets", "/change-sets", "engineer"),
        Shot("workbench", f"/change-sets/{ids['change_set']}/workbench", "engineer"),
        Shot(
            "workbench_dark", f"/change-sets/{ids['change_set']}/workbench", "engineer", dark=True
        ),
        Shot("st_form", "/imports/st", "engineer"),
        Shot("st_preview", "/_show/st-preview", "engineer"),
        Shot("connections", "/status-codes/connections", "admin"),
        Shot("releases", "/releases", "admin"),
        Shot("release_builder", f"/releases/{ids['open_release']}/builder", "admin"),
        Shot("exports", "/exports", "admin"),
        Shot("health", "/reports/catalogue-health", "admin"),
        Shot("translations", "/translations", "owner"),
        Shot("users", "/admin/users", "admin"),
        Shot("arabic", "/", "engineer_ar"),
        Shot("arabic_list", "/status-codes", "engineer_ar"),
        Shot("phone_dashboard", "/", "engineer", size=phone),
        Shot("phone_list", "/status-codes", "engineer", size=phone),
    ]


# ----------------------------------------------------------------------------------------- pieces
class Builder:
    """Builds the slides of one deck."""

    def __init__(self, label: str, facts: Facts, images: dict[str, Path]):
        self.label, self.facts, self.images = label, facts, images
        self.slides: list[Slide] = []

    # frames --------------------------------------------------------------------------------
    def content(self, title: str, notes: str = "", bg: str = WHITE) -> Slide:
        slide = Slide(title, bg=bg, notes=notes)
        slide.text(
            LEFT,
            0.38,
            12.1,
            0.7,
            [Para(title)],
            size=30,
            color=NAVY,
            bold=True,
            valign="m",
            name="Title",
        )
        self.slides.append(slide)
        return slide

    def dark(self, title: str, notes: str = "") -> Slide:
        slide = Slide(title, bg=NAVY, notes=notes)
        self.slides.append(slide)
        return slide

    def shot(self, slide: Slide, name: str, x: float, y: float, w: float, h: float, alt: str):
        return slide.picture(x, y, w, h, self.images[name], alt, name=f"Screenshot {name}")

    def shot_plain(self, slide: Slide, name: str, x: float, y: float, w: float, h: float, alt: str):
        return slide.picture(
            x, y, w, h, self.images[name], alt, frame=False, name=name.capitalize()
        )

    def callouts(
        self,
        slide: Slide,
        items: list[tuple[str, str]],
        x: float,
        y: float,
        w: float,
        h: float,
        color=NAVY,
        text_color=INK,
    ) -> None:
        """Numbered notes, spread evenly down a column."""
        gap = h / len(items)
        for number, (head, body) in enumerate(items, 1):
            top = y + (number - 1) * gap
            slide.ellipse(
                x,
                top + 0.02,
                0.42,
                0.42,
                color,
                str(number),
                color=WHITE,
                size=14,
                name=f"Note {number}",
            )
            slide.text(
                x + 0.6,
                top,
                w - 0.6,
                gap - 0.1,
                [
                    Para(head, size=16, bold=True, color=color, after=2),
                    Para(body, size=14, color=text_color),
                ],
                name=f"Note {number} text",
            )

    def shot_slide(
        self,
        title: str,
        name: str,
        items: list[tuple[str, str]],
        alt: str,
        notes: str = "",
        wide: float = 8.2,
    ) -> Slide:
        slide = self.content(title, notes)
        self.shot(slide, name, LEFT, TOP, wide, wide / 1.6, alt)
        self.callouts(
            slide, items, LEFT + wide + 0.45, TOP + 0.05, 12.73 - (LEFT + wide + 0.45), 4.9
        )
        return slide

    def two_shots(
        self, title: str, left: tuple[str, str, str], right: tuple[str, str, str], notes: str = ""
    ) -> Slide:
        """(image, caption, alt) twice, side by side."""
        slide = self.content(title, notes)
        w = 5.95
        for index, (name, caption, alt) in enumerate((left, right)):
            x = LEFT + index * (w + 0.23)
            self.shot(slide, name, x, TOP, w, w / 1.6, alt)
            slide.text(
                x,
                TOP + w / 1.6 + 0.2,
                w,
                1.0,
                [Para(caption)],
                size=14,
                color=INK,
                name=f"Caption {index + 1}",
            )
        return slide

    def stats(
        self, title: str, items: list[tuple[str, str]], notes: str = "", foot: str = ""
    ) -> Slide:
        slide = self.content(title, notes)
        w = (12.13 - 0.3 * (len(items) - 1)) / len(items)
        for index, (number, label) in enumerate(items):
            x = LEFT + index * (w + 0.3)
            slide.rect(
                x, 1.6, w, 3.2, fill=PAGE, line="DDE3EA", radius=0.12, name=f"Card {index + 1}"
            )
            slide.text(
                x + 0.2,
                1.95,
                w - 0.4,
                1.3,
                [Para(number)],
                size=60,
                color=NAVY,
                bold=True,
                align="c",
                valign="m",
                name=f"Figure {index + 1}",
            )
            slide.text(
                x + 0.25,
                3.45,
                w - 0.5,
                1.2,
                [Para(label)],
                size=16,
                color=INK,
                align="c",
                name=f"Label {index + 1}",
            )
        if foot:
            slide.text(LEFT, 5.25, 12.13, 1.0, [Para(foot)], size=16, color=MUTED, name="Note")
        return slide

    def finish(self) -> list[Slide]:
        total = len(self.slides)
        for number, slide in enumerate(self.slides, 1):
            on_dark = slide.bg == NAVY
            colour = SKY if on_dark else MUTED
            slide.text(
                LEFT,
                6.98,
                9.0,
                0.3,
                [Para(f"CSCM Tool v{self.facts.version}  ·  {self.label}")],
                size=10,
                color=colour,
                valign="m",
                name="Footer",
            )
            slide.text(
                11.6,
                6.98,
                1.13,
                0.3,
                [Para(f"{number} / {total}")],
                size=10,
                color=colour,
                align="r",
                valign="m",
                name="Page",
            )
        return self.slides


def title_slide(b: Builder, subtitle: str, picture: str) -> None:
    slide = b.dark(
        "CSCM Tool",
        notes=f"Version {b.facts.version}, {b.facts.date}. All screens in this deck are screenshots of the real application with fictitious data.",
    )
    slide.text(
        LEFT,
        0.3,
        12.1,
        0.4,
        [Para(branding.OWNER_LINE)],
        size=12,
        color=SKY,
        valign="m",
        name="Owner",
    )
    b.shot_plain(
        slide,
        "logo",
        LEFT,
        1.2,
        1.5,
        1.5,
        "Logo of the CSCM Tool: a wind turbine with a status ring between code brackets",
    )
    slide.text(
        LEFT + 1.8,
        1.15,
        4.7,
        1.0,
        [Para(branding.PRODUCT)],
        size=54,
        color=WHITE,
        bold=True,
        valign="m",
        name="Product",
    )
    slide.text(
        LEFT + 1.8, 2.2, 4.7, 0.9, [Para(branding.LONG_NAME)], size=20, color=SKY, name="Long name"
    )
    slide.text(LEFT, 3.55, 6.4, 1.3, [Para(subtitle)], size=28, color=WHITE, name="Subtitle")
    slide.text(
        LEFT,
        5.0,
        6.4,
        1.2,
        [
            Para(f"Version {b.facts.version}", size=18, color=WHITE, bold=True, after=4),
            Para(b.facts.date, size=16, color=SKY),
        ],
        name="Version",
    )
    b.shot(
        slide, picture, 7.35, 1.55, 5.4, 3.375, "The dashboard of the application in the dark theme"
    )
    slide.text(
        7.35,
        5.2,
        5.4,
        0.9,
        [Para("Main Controllers and Hub Controllers of wind turbines")],
        size=14,
        color=SKY,
        name="Tagline",
    )


# ----------------------------------------------------------------------------------------- management
def management(facts: Facts, images: dict[str, Path]) -> list[Slide]:
    b = Builder("Management overview", facts, images)
    title_slide(b, "Management overview", "dashboard_dark")

    s = b.dark(
        "One governed source of truth",
        "The core idea in one slide: a code is created, reviewed, approved, versioned and released in one place, and everything else is derived from it.",
    )
    s.text(
        LEFT,
        0.55,
        12.1,
        1.4,
        [Para("One governed source of truth for every status code")],
        size=40,
        color=WHITE,
        bold=True,
        name="Title",
    )
    cards = [
        ("Before", "Codes lived in documents. A change was hard to trace and hard to reuse."),
        (
            "With the tool",
            "A code is created, reviewed, approved, versioned and released in one place.",
        ),
        (
            "The result",
            "Manuals, specifications and SCADA lists are produced from approved codes only.",
        ),
    ]
    for i, (head, body) in enumerate(cards):
        x = LEFT + i * 4.1
        s.rect(x, 2.5, 3.9, 3.6, fill="0A3D82", radius=0.12, name=f"Card {i + 1}")
        s.text(
            x + 0.3,
            2.8,
            3.3,
            0.5,
            [Para(head)],
            size=20,
            color=SKY,
            bold=True,
            name=f"Card {i + 1} head",
        )
        s.text(
            x + 0.3, 3.5, 3.3, 2.4, [Para(body)], size=22, color=WHITE, name=f"Card {i + 1} text"
        )

    b.shot_slide(
        "Everything people need, in one place",
        "dashboard",
        [
            ("A menu for the role", "Each person sees only what their role may do."),
            (
                "Work that waits",
                "Counters and links lead straight to reviews, approvals and drafts.",
            ),
            (
                "Colour with meaning",
                "Roles and lifecycle states have fixed colours, never decoration.",
            ),
        ],
        "The dashboard with counters for the work that waits for the signed-in person",
        "The dashboard of an engineer. The menu on the left follows the role; the badge next to the name shows the role by colour.",
    )

    s = b.content(
        "Three independent decisions before a release",
        "No single person can release a code: the author, a reviewer, an administrator and the Chief Engineer all take part, and a domain engineer signs off first.",
    )
    steps = [
        ("Draft", "5B6B7F"),
        ("Review", "2E6BC6"),
        ("Pending", "B7791F"),
        ("Approved", "1E7F4C"),
        ("Released", NAVY),
    ]
    for i, (name, colour) in enumerate(steps):
        s.chevron(LEFT + i * 2.45, 1.55, 2.6, 0.95, colour, name, size=18, name=f"Step {name}")
    decisions = [
        ("Reviewer", "Checks content and wording, and signs off."),
        ("Administrator", "Confirms audience access and signs off."),
        ("Chief Engineer", "Approves. Nobody can approve their own work."),
    ]
    for i, (who, what) in enumerate(decisions):
        x = LEFT + i * 4.1
        s.rect(x, 3.1, 3.9, 2.2, fill=PAGE, line="DDE3EA", radius=0.12, name=f"Decision {i + 1}")
        s.ellipse(
            x + 0.3, 3.4, 0.5, 0.5, NAVY, str(i + 1), size=16, name=f"Decision {i + 1} number"
        )
        s.text(
            x + 1.0,
            3.38,
            2.7,
            0.55,
            [Para(who)],
            size=20,
            color=NAVY,
            bold=True,
            valign="m",
            name=f"Decision {i + 1} head",
        )
        s.text(
            x + 0.3, 4.15, 3.4, 1.0, [Para(what)], size=16, color=INK, name=f"Decision {i + 1} text"
        )
    s.text(
        LEFT,
        5.65,
        12.13,
        0.9,
        [
            Para(
                "Before the review, the engineering domains concerned sign off the content (cross-domain sign-off). Every step is recorded in an audit log that cannot be changed."
            )
        ],
        size=16,
        color=MUTED,
        name="Note",
    )

    b.two_shots(
        "The first migration: about 1,250 codes",
        (
            "st_preview",
            "Programs are read from the controller files and previewed. Nothing is created until a person has looked.",
            "The preview of an import from controller program files",
        ),
        (
            "workbench",
            "The workbench lets each step work on the whole batch, with a sample inspection that one defect can stop.",
            "The workbench of a change set with the readiness of every draft",
        ),
        "Roughly 900 Main Controller and 350 Hub Controller codes pass the same governance as a single code. The sample inspection keeps bulk decisions honest.",
    )

    b.stats(
        "Built to be trusted",
        [
            (facts.tests, "automated tests, all passing"),
            (facts.coverage, "of the application code covered"),
            (facts.requirements, "requirements, each traced to tests"),
            (facts.languages, "languages, including right to left"),
        ],
        "The numbers come from the latest test report and the requirement documents of this version.",
        f"The REST API has {facts.operations} operations, the database {facts.tables} tables. Every change of a code is kept with who, when and why.",
    )

    s = b.content(
        "Looks right in every language and light",
        "The interface follows the user's language, can switch between light and dark, and works on a phone.",
    )
    wide = 4.25
    items = [
        ("arabic", "Right to left for Arabic", "The dashboard in Arabic"),
        (
            "dashboard_dark",
            "Dark theme, set by the system or by choice",
            "The dashboard in the dark theme",
        ),
    ]
    for i, (name, caption, alt) in enumerate(items):
        x = LEFT + i * (wide + 0.3)
        b.shot(s, name, x, TOP, wide, wide / 1.6, alt)
        s.text(
            x, TOP + wide / 1.6 + 0.15, wide, 0.7, [Para(caption)], size=14, name=f"Caption {i + 1}"
        )
    px = LEFT + 2 * (wide + 0.3)
    b.shot(s, "phone_dashboard", px, TOP, 2.25, 4.87, "The dashboard on a phone")
    s.text(px, TOP + 4.95, 3.0, 0.5, [Para("And on a phone")], size=14, name="Caption 3")

    b.shot_slide(
        "Releases people can rely on",
        "release_builder",
        [
            ("A fixed baseline", "A release holds the latest published revision of every code."),
            (
                "A package for every audience",
                "All languages, access levels and formats in one download.",
            ),
            (
                "A clear download rule",
                "Everyone downloads what is released; the working set stays internal.",
            ),
        ],
        "The release builder with the approved codes of the next release",
        "Releases are immutable once published. The package is built in the background.",
    )

    b.two_shots(
        "Insight for engineering",
        (
            "health",
            "Catalogue health: how full each number range is, and what stalls.",
            "The catalogue health report",
        ),
        (
            "connections",
            "Connections: which code suppresses, requires or escalates to which.",
            "The connections between status codes",
        ),
        "The connections are read from the controller programs themselves, never invented.",
    )

    s = b.content(
        "Recently delivered", "Taken from the improvement list of this version. Newest last."
    )
    rows = list(facts.delivered) or [("This release", f"v{facts.version}", "")]
    for i, (what, version, reqs) in enumerate(rows):
        y = 1.45 + i * 0.83
        s.rect(LEFT, y, 12.13, 0.72, fill=PAGE, line="DDE3EA", radius=0.1, name=f"Row {i + 1}")
        s.text(
            LEFT + 0.25,
            y + 0.1,
            1.9,
            0.52,
            [Para(version)],
            size=14,
            color=NAVY,
            bold=True,
            valign="m",
            name=f"Row {i + 1} version",
        )
        s.text(
            LEFT + 2.3,
            y + 0.05,
            8.3,
            0.62,
            [Para(what)],
            size=16,
            color=INK,
            valign="m",
            name=f"Row {i + 1} text",
        )
        s.text(
            LEFT + 10.7,
            y + 0.1,
            1.2,
            0.52,
            [Para(reqs)],
            size=12,
            color=MUTED,
            align="r",
            valign="m",
            name=f"Row {i + 1} requirement",
        )

    s = b.dark("Closing", "Questions and next steps.")
    s.text(
        LEFT,
        1.2,
        12.1,
        1.6,
        [Para("Governed, traceable, ready for the first migration")],
        size=40,
        color=WHITE,
        bold=True,
        name="Title",
    )
    s.text(
        LEFT,
        3.1,
        7.2,
        2.8,
        [
            Para(
                "Every code created, reviewed, approved and released in one tool",
                bullet=True,
                after=8,
            ),
            Para(
                "Bulk work for the migration, kept honest by a sample inspection",
                bullet=True,
                after=8,
            ),
            Para("Languages, accessibility and a dark theme from the start", bullet=True, after=8),
        ],
        size=20,
        color=WHITE,
        name="Summary",
    )
    b.shot(s, "login_dark", 8.2, 2.9, 4.5, 2.8125, "The login page in the dark theme")
    return b.finish()


# ----------------------------------------------------------------------------------------- team
def team(facts: Facts, images: dict[str, Path]) -> list[Slide]:
    b = Builder("Design walkthrough", facts, images)
    title_slide(b, "Design walkthrough for the team", "login_dark")

    s = b.content(
        "Design principles",
        "The rules behind every screen. They are written down in docs/10-ui-ux-specification.md.",
    )
    cards = [
        (
            "Same shell everywhere",
            "Top bar, role-based menu and tokens of the OneTool design system. No CDN, no framework.",
        ),
        (
            "Colour means something",
            "Roles, lifecycle states and confidence have fixed colours. Every pair is checked for contrast.",
        ),
        (
            "Everyone can use it",
            "Keyboard operable, labelled controls, 19 languages, right to left, dark theme.",
        ),
        ("Nothing is lost", "A rejected form keeps what was typed. Every action is audited."),
    ]
    for i, (head, body) in enumerate(cards):
        x = LEFT + (i % 2) * 6.15
        y = 1.4 + (i // 2) * 2.7
        s.rect(x, y, 5.95, 2.45, fill=PAGE, line="DDE3EA", radius=0.12, name=f"Principle {i + 1}")
        s.ellipse(
            x + 0.3, y + 0.3, 0.5, 0.5, NAVY, str(i + 1), size=16, name=f"Principle {i + 1} number"
        )
        s.text(
            x + 1.0,
            y + 0.28,
            4.7,
            0.55,
            [Para(head)],
            size=20,
            color=NAVY,
            bold=True,
            valign="m",
            name=f"Principle {i + 1} head",
        )
        s.text(
            x + 0.3,
            y + 1.05,
            5.4,
            1.3,
            [Para(body)],
            size=16,
            color=INK,
            name=f"Principle {i + 1} text",
        )

    b.two_shots(
        "Login",
        (
            "login",
            "Password sign-in, with the language choice and the theme choice before anybody is signed in.",
            "The login page in the light theme",
        ),
        (
            "login_dark",
            "Where the organisation uses Windows accounts, one button signs in with the Windows identity.",
            "The login page in the dark theme",
        ),
        "In a deployment people sign in with their Windows account; the password form can be switched off.",
    )

    b.shot_slide(
        "The shell: top bar and menu",
        "dashboard_admin",
        [
            (
                "Top bar",
                "Notices, theme, language, the person and their role badge, account and log out.",
            ),
            ("Menu", "Groups open and close; the count beside a link is the work waiting there."),
            ("Role colours", "Red is the highest role. The colours repeat in lists and reports."),
        ],
        "The dashboard of an administrator with the full menu",
    )

    b.shot_slide(
        "Status Codes: find, filter, share",
        "list",
        [
            (
                "Filters",
                "Search tolerates typos; group, subgroup, platform, lifecycle and category narrow the list.",
            ),
            ("Columns and saved searches", "Choose the columns, save a view and share its link."),
            (
                "State badges",
                "Draft to Archived, always in the same colours and always with words.",
            ),
        ],
        "The status code list with filters, columns and saved searches",
    )

    b.shot_slide(
        "Select, select all, delete Drafts",
        "list_drafts",
        [
            (
                "Tick boxes for your own Drafts",
                "Only the author can delete a Draft, so only these rows have a box.",
            ),
            ("Select all", "The box in the header ticks every Draft on the page."),
            (
                "All Drafts of a filter",
                "When filtered to Draft, one button deletes your Drafts on every page.",
            ),
        ],
        "The list filtered to Drafts with tick boxes",
    )

    b.shot_slide(
        "A status code",
        "detail",
        [
            ("Identity and state", "The number, the state badge and the sign-offs at a glance."),
            ("Tabs", "Details, history, comparison, where used, translations."),
            ("One number, forever", "A number is issued once, at submit, and never reused."),
        ],
        "The detail page of a released status code",
    )

    b.shot_slide(
        "Writing a code",
        "new_form",
        [
            (
                "Help beside every field",
                "Each choice explains itself; subgroups follow the group chosen.",
            ),
            (
                "Soft checks",
                "Duplicates, similar titles and range capacity are shown while typing.",
            ),
            ("Nothing is lost", "A rejected save keeps every entry and says what to correct."),
        ],
        "The form for a new status code",
    )

    b.shot_slide(
        "My work and the queues",
        "my_requests",
        [
            ("My Change Requests", "Your own requests, their state, and who they wait for."),
            ("Select and withdraw", "Tick several and withdraw them at once; each is reported."),
            ("Queues for the roles", "Review and approval queues show the age of every request."),
        ],
        "The list of the engineer's own change requests",
    )

    b.shot_slide(
        "Review queue",
        "review_queue",
        [
            (
                "Waiting time as a pill",
                "Green, amber and red follow the service level of the step.",
            ),
            ("Open and decide", "One click to the request with its full history."),
            ("Separation of duties", "You cannot review your own work."),
        ],
        "The review queue of a reviewer",
    )

    b.shot_slide(
        "Sign-off and approval",
        "cr_detail",
        [
            (
                "The strip of sign-offs",
                "Domain, Reviewer, Administrator and Chief Engineer, each with name and time.",
            ),
            (
                "Comments and field notes",
                "Decisions, comments and notes on single fields stay with the request.",
            ),
            ("Password for decisions", "Sensitive steps ask for the password again."),
        ],
        "A change request waiting for the Chief Engineer",
    )

    b.shot_slide(
        "Change sets and the workbench",
        "workbench",
        [
            ("Readiness", "What still stops each Draft from being submitted."),
            (
                "Bulk edit and bulk steps",
                "Set one value, submit, sign off or decide for the whole batch.",
            ),
            ("Sample inspection", "Draw a sample, mark each code, and one defect stops the batch."),
        ],
        "The workbench of the migration change set",
    )

    b.two_shots(
        "Importing from controller programs",
        (
            "st_form",
            "Upload files, a folder or a ZIP. Choose a category for each alarm type.",
            "The upload form of the import",
        ),
        (
            "st_preview",
            "Every program is a row with its new number, alarm type and a category you can change.",
            "The preview of the import",
        ),
        "The import creates Drafts only. They still need every decision before release.",
    )

    b.shot_slide(
        "Connections",
        "connections",
        [
            ("Suppressed by", "A code that is silenced while its cause is active."),
            ("Escalates to", "Where a repeating code is replaced by its repeat code."),
            ("Read, not guessed", "Taken from the programs; loops and missing codes are named."),
        ],
        "The connections between status codes",
    )

    b.two_shots(
        "Releases and exports",
        (
            "release_builder",
            "The builder collects approved codes into an immutable release.",
            "The release builder",
        ),
        (
            "exports",
            "Exports and the package, with the download rule applied.",
            "The export center",
        ),
        "A package holds every language and access level in the formats chosen.",
    )

    b.shot_slide(
        "Catalogue health",
        "health",
        [
            ("Capacity of the ranges", "How full each number range is, and when it will run out."),
            (
                "Colour for the controller",
                "Main Controller rows blue, Hub Controller rows light blue.",
            ),
            ("Stalled work", "Requests that wait too long are listed for the administrator."),
        ],
        "The catalogue health report",
    )

    b.shot_slide(
        "Translations and confidence",
        "translations",
        [
            (
                "One row per language",
                "Coverage, native-speaker review and the confidence of the pre-check.",
            ),
            ("Confidence colours", "Red up to 50 %, green above 95 %."),
            ("New words are checked", "Changed or new texts are checked and approved separately."),
        ],
        "The overview of the translations",
    )

    b.two_shots(
        "Languages and right to left",
        (
            "arabic",
            "Arabic mirrors the whole layout: menu on the right, tables read from the right.",
            "The dashboard in Arabic",
        ),
        (
            "arabic_list",
            "Identifiers and numbers stay left to right inside the text.",
            "The status code list in Arabic",
        ),
        "19 languages; the language list shows the country letters and the flag.",
    )

    b.two_shots(
        "Light and dark",
        (
            "detail",
            "Light: ink on paper, for the office and for print.",
            "A status code in the light theme",
        ),
        (
            "detail_dark",
            "Dark: the same page, with every colour pair checked for contrast.",
            "A status code in the dark theme",
        ),
        "The choice is Automatic (system), Light or Dark and is kept on the device. Printouts and exports stay light.",
    )

    b.shot_slide(
        "People and roles",
        "users",
        [
            ("Six roles", "Viewer, Engineer, Reviewer, Chief Engineer, Administrator, StCd Owner."),
            ("Colour is the level", "The role badge colour is the same everywhere it appears."),
            ("Accounts by e-mail", "The e-mail address is fixed and links the Windows identity."),
        ],
        "The user administration",
    )

    s = b.content(
        "On a phone", "The menu folds away below 768 px and tables scroll inside their card."
    )
    for i, (name, caption) in enumerate(
        (("phone_dashboard", "Dashboard"), ("phone_list", "Status codes"))
    ):
        x = LEFT + i * 2.7
        b.shot(s, name, x, TOP, 2.4, 5.19, f"The {caption.lower()} on a phone")
        s.text(x, TOP + 5.3, 2.4, 0.4, [Para(caption)], size=14, align="c", name=f"Caption {i + 1}")
    b.callouts(
        s,
        [
            ("Menu on demand", "A button opens the menu; Esc closes it."),
            ("Touch-sized targets", "Buttons and links are at least 44 by 44 pixels."),
            ("No horizontal page scroll", "Wide tables scroll inside their card."),
        ],
        6.3,
        TOP + 0.1,
        6.4,
        4.8,
    )

    s = b.content(
        "Rules for every new screen",
        "From docs/10-ui-ux-specification.md section 13 and the accessibility tests.",
    )
    rules = [
        (
            "Use tokens, never colours",
            "var(--color-surface), var(--tint-warn-bg) ... A test fails on a hex colour outside the tokens.",
        ),
        (
            "Give a dark twin to a new token",
            "A light token without a dark value would stay light on a dark page.",
        ),
        (
            "Label every control",
            "A visible label or an accessible name; tables use scope on their headers.",
        ),
        ("Words for states, not only colour", "Badges carry the state as text."),
        (
            "Translate every text",
            "New words go through the confidence check and a separate approval.",
        ),
    ]
    for i, (head, body) in enumerate(rules):
        y = 1.4 + i * 1.08
        s.rect(LEFT, y, 12.13, 0.95, fill=PAGE, line="DDE3EA", radius=0.1, name=f"Rule {i + 1}")
        s.ellipse(
            LEFT + 0.25, y + 0.22, 0.5, 0.5, NAVY, str(i + 1), size=16, name=f"Rule {i + 1} number"
        )
        s.text(
            LEFT + 1.0,
            y + 0.1,
            3.7,
            0.75,
            [Para(head)],
            size=18,
            color=NAVY,
            bold=True,
            valign="m",
            name=f"Rule {i + 1} head",
        )
        s.text(
            LEFT + 4.9,
            y + 0.1,
            7.0,
            0.75,
            [Para(body)],
            size=14,
            color=INK,
            valign="m",
            name=f"Rule {i + 1} text",
        )

    s = b.dark("Closing", "")
    s.text(
        LEFT,
        1.4,
        12.1,
        1.2,
        [Para("The same rules, from login to release")],
        size=40,
        color=WHITE,
        bold=True,
        name="Title",
    )
    s.text(
        LEFT,
        3.1,
        7.2,
        2.8,
        [
            Para("One shell, tokens for every colour, both themes", bullet=True, after=8),
            Para("Governance visible in every screen", bullet=True, after=8),
            Para(
                f"Version {facts.version}: {facts.tests} tests, {facts.languages} languages",
                bullet=True,
                after=8,
            ),
        ],
        size=20,
        color=WHITE,
        name="Summary",
    )
    b.shot(s, "dashboard_dark", 8.2, 2.9, 4.5, 2.8125, "The dashboard in the dark theme")
    return b.finish()

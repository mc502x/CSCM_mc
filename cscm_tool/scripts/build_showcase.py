"""The design showcase of a release: two PowerPoint decks from real screenshots (FR-186).

    python scripts/build_showcase.py                  both decks, into releases/v<version>/
    python scripts/build_showcase.py --only team
    python scripts/build_showcase.py --pdf            also a PDF copy of each deck
    python scripts/build_showcase.py --reuse          take the screenshots of the last run

    CSCM-Tool_v<version>_Design-Showcase-Management.pptx   the short deck for management
    CSCM-Tool_v<version>_Design-Showcase-Team.pptx         the walkthrough from login to release

The screens are taken from a throw-away copy of the application with fictitious data (never a real
database), by the Edge or Chrome of the machine in headless mode (set CSCM_BROWSER to a specific
executable). The decks are English only. A text that does not fit its box stops the build; the
preview images (--previews) show every slide as the build sees it.

Needs python-pptx (requirements.txt). Docs: docs/14-deployment-architecture.md, docs/15 section 12."""

import argparse
import datetime
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(APP_DIR / "scripts"))

from app.version import VERSION  # noqa: E402
from showcase import capture, deck, decks, demo  # noqa: E402

REPO = APP_DIR.parent
DECKS = {
    "management": (
        "Design-Showcase-Management",
        "Design showcase for management",
        decks.management,
    ),
    "team": ("Design-Showcase-Team", "Design showcase for the team", decks.team),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The design showcase of a release.")
    parser.add_argument("--out", type=Path, default=REPO / "releases" / f"v{VERSION}")
    parser.add_argument(
        "--only", default=",".join(DECKS), help="comma separated: " + ", ".join(DECKS)
    )
    parser.add_argument("--pdf", action="store_true", help="also write a PDF copy of each deck")
    parser.add_argument("--previews", action="store_true", help="also write one PNG per slide")
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="use the screenshots of the last run (dist/showcase/v<version>/screens)",
    )
    args = parser.parse_args(argv)
    wanted = [k.strip() for k in args.only.split(",") if k.strip()]
    unknown = [k for k in wanted if k not in DECKS]
    if unknown:
        print("Unknown deck:", ", ".join(unknown), "- choose from", ", ".join(DECKS))
        return 2

    work = REPO / "dist" / "showcase" / f"v{VERSION}"  # screenshots and previews: not committed
    screens = work / "screens"
    today = datetime.date.today().isoformat()
    facts = decks.gather(VERSION, today)

    if args.reuse and screens.is_dir():
        images = {p.stem: p for p in screens.glob("*.png")}
        print(f"Using {len(images)} screenshots from {screens}")
    else:
        print("Building the demo (a temporary database with fictitious data) ...")
        instance = demo.build()
        try:
            base = demo.serve(instance)
            wanted_shots = decks.shots(instance.ids)
            print(f"Taking {len(wanted_shots)} screenshots with {capture.find_browser()} ...")
            images = capture.take_all(base, wanted_shots, screens)
        finally:
            instance.stop()

    images["logo"] = APP_DIR / "app" / "static" / "img" / "cscm-logo-512.png"
    for key in wanted:
        label, title, build = DECKS[key]
        slides = build(facts, images)
        base_name = f"CSCM-Tool_v{VERSION}_{label}"
        target = args.out / f"{base_name}.pptx"
        deck.to_pptx(slides, target, f"CSCM Tool - {title} - v{VERSION}", title)
        print(f"{target}  ({len(slides)} slides, {target.stat().st_size // 1024} KB)")
        if args.pdf:
            pdf = args.out / f"{base_name}.pdf"
            deck.to_pdf(slides, pdf)
            print(f"{pdf}  ({pdf.stat().st_size // 1024} KB)")
        if args.previews:
            folder = work / "previews" / key
            deck.to_previews(slides, folder)
            print(f"{folder}  (slide-01.png ...)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

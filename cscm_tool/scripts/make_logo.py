"""The logo of the CSCM Tool (FR-187): a wind turbine whose hub is a status ring, between code
brackets, above three status lights.

    python scripts/make_logo.py

writes app/static/img/cscm-logo.svg (the logo of the application: menu bar, login page, favicon) and
cscm-logo-512.png (the picture the PDFs and the slide decks embed). Both are committed; run this
script only to change the design. The tile is navy with light shapes, so it reads on the light and
on the dark theme alike."""

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "app" / "static" / "img"
NAVY, SKY, WHITE = "#002e6d", "#8ab4f8", "#ffffff"
GREEN, AMBER, RED = "#3ecf8e", "#f2b01e", "#ff6b5e"
HUB = (128.0, 98.0)
BLADE = 74.0


def blade(angle_deg: float) -> list[tuple[float, float]]:
    """A tapered blade from the hub: wide and slightly offset at the root, pointed at the tip."""
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)  # along the blade
    vx, vy = -uy, ux  # across it
    cx, cy = HUB
    root, tip = 13.0, BLADE
    points = [
        (cx + ux * root + vx * 8.5, cy + uy * root + vy * 8.5),
        (cx + ux * (root + 28) + vx * 7.5, cy + uy * (root + 28) + vy * 7.5),
        (cx + ux * tip + vx * 1.6, cy + uy * tip + vy * 1.6),
        (cx + ux * (root + 24) - vx * 5.0, cy + uy * (root + 24) - vy * 5.0),
        (cx + ux * root - vx * 6.5, cy + uy * root - vy * 6.5),
    ]
    return points


BLADES = [blade(-90 + 5), blade(30 + 5), blade(150 + 5)]
TOWER = [(124.0, 112.0), (132.0, 112.0), (138.0, 206.0), (118.0, 206.0)]
# the status ring around the hub: three arcs of 110 degrees, green, amber, red
RING_R, RING_W = 21.0, 6.5
ARCS = [(GREEN, -80, 30), (AMBER, 40, 150), (RED, 160, 270)]
LIGHTS = [(100.0, GREEN), (128.0, AMBER), (156.0, RED)]
LIGHT_Y, LIGHT_R = 228.0, 6.0


def _pts(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def _arc(start: float, end: float) -> str:
    cx, cy = HUB
    sx, sy = cx + RING_R * math.cos(math.radians(start)), cy + RING_R * math.sin(
        math.radians(start)
    )
    ex, ey = cx + RING_R * math.cos(math.radians(end)), cy + RING_R * math.sin(math.radians(end))
    return f"M {sx:.1f} {sy:.1f} A {RING_R} {RING_R} 0 0 1 {ex:.1f} {ey:.1f}"


def svg() -> str:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-label="CSCM Tool">',
        "<title>CSCM Tool - Controller Status Code Management Tool</title>",
        f'<rect x="6" y="6" width="244" height="244" rx="52" fill="{NAVY}"/>',
        # code brackets: the status codes
        f'<path d="M 46 70 L 30 70 L 30 168 L 46 168" fill="none" stroke="{SKY}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>',
        f'<path d="M 210 70 L 226 70 L 226 168 L 210 168" fill="none" stroke="{SKY}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>',
        f'<polygon points="{_pts(TOWER)}" fill="{WHITE}"/>',
        f'<rect x="96" y="204" width="64" height="7" rx="3.5" fill="{WHITE}"/>',
    ]
    parts += [f'<polygon points="{_pts(b)}" fill="{WHITE}"/>' for b in BLADES]
    cx, cy = HUB
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="{RING_R + 5}" fill="{NAVY}"/>')
    parts += [
        f'<path d="{_arc(s, e)}" fill="none" stroke="{color}" stroke-width="{RING_W}" stroke-linecap="round"/>'
        for color, s, e in ARCS
    ]
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="11" fill="{SKY}"/>')
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="{WHITE}"/>')
    parts += [f'<circle cx="{x}" cy="{LIGHT_Y}" r="{LIGHT_R}" fill="{c}"/>' for x, c in LIGHTS]
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def png(size: int = 512) -> Image.Image:
    """The same drawing with Pillow, four times as large and scaled down."""
    big = size * 4
    k = big / 256
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def p(points):
        return [(x * k, y * k) for x, y in points]

    draw.rounded_rectangle((6 * k, 6 * k, 250 * k, 250 * k), radius=52 * k, fill=NAVY)
    for path in (
        [(46, 70), (30, 70), (30, 168), (46, 168)],
        [(210, 70), (226, 70), (226, 168), (210, 168)],
    ):
        draw.line(p(path), fill=SKY, width=round(9 * k), joint="curve")
        for x, y in (path[0], path[-1]):
            draw.ellipse(((x - 4.5) * k, (y - 4.5) * k, (x + 4.5) * k, (y + 4.5) * k), fill=SKY)
    draw.polygon(p(TOWER), fill=WHITE)
    draw.rounded_rectangle((96 * k, 204 * k, 160 * k, 211 * k), radius=3.5 * k, fill=WHITE)
    for b in BLADES:
        draw.polygon(p(b), fill=WHITE)
    cx, cy = HUB
    r = (RING_R + 5) * k
    draw.ellipse((cx * k - r, cy * k - r, cx * k + r, cy * k + r), fill=NAVY)
    box = (cx * k - RING_R * k, cy * k - RING_R * k, cx * k + RING_R * k, cy * k + RING_R * k)
    for color, start, end in ARCS:
        draw.arc(box, start, end, fill=color, width=round(RING_W * k))
        for angle in (start, end):
            x = cx + RING_R * math.cos(math.radians(angle))
            y = cy + RING_R * math.sin(math.radians(angle))
            rr = RING_W / 2 * k
            draw.ellipse((x * k - rr, y * k - rr, x * k + rr, y * k + rr), fill=color)
    for x, y, rad, color in ((cx, cy, 11, SKY), (cx, cy, 4.5, WHITE)):
        draw.ellipse(((x - rad) * k, (y - rad) * k, (x + rad) * k, (y + rad) * k), fill=color)
    for x, color in LIGHTS:
        draw.ellipse(
            (
                (x - LIGHT_R) * k,
                (LIGHT_Y - LIGHT_R) * k,
                (x + LIGHT_R) * k,
                (LIGHT_Y + LIGHT_R) * k,
            ),
            fill=color,
        )
    return image.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cscm-logo.svg").write_text(svg(), encoding="utf-8", newline="\n")
    png(512).save(OUT / "cscm-logo-512.png")
    print("written:", OUT / "cscm-logo.svg", OUT / "cscm-logo-512.png")


if __name__ == "__main__":
    main()

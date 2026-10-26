"""Screenshots with the headless Edge or Chrome of the machine (FR-186): no browser driver and no
download, only the browser's own `--screenshot` command line."""

import os
import shutil
import subprocess  # nosec B404 - runs the installed browser with fixed arguments
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

_WINDOWS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)
_PATH_NAMES = (
    "microsoft-edge",
    "msedge",
    "google-chrome",
    "chromium",
    "chromium-browser",
    "chrome",
)


@dataclass(frozen=True)
class Shot:
    name: str
    path: str  # the page, after signing in
    role: str | None = "admin"  # a username of the demo; None for a page without sign-in
    dark: bool = False
    size: tuple[int, int] = (1200, 750)
    skip: tuple[int, int] | None = None  # cut this band of rows out of a tall page (y from, y to)
    crop_left: int = 0  # cut this many columns off the left (the menu) after the rows are cut


def find_browser() -> str:
    """CSCM_BROWSER, else Edge or Chrome in their usual places, else on the PATH."""
    given = os.environ.get("CSCM_BROWSER")
    if given and Path(given).is_file():
        return given
    for candidate in _WINDOWS:
        if Path(candidate).is_file():
            return candidate
    for name in _PATH_NAMES:
        found = shutil.which(name)
        if found:
            return found
    raise RuntimeError(
        "No Edge or Chrome found. Install one of them, or set CSCM_BROWSER to its executable."
    )


def take(base: str, shot: Shot, target: Path, browser: str | None = None) -> Path:
    """One screenshot of `shot` from the demo at `base`."""
    browser = browser or find_browser()
    theme = "dark" if shot.dark else "light"
    if shot.role:
        url = f"{base}/_show/as/{shot.role}?theme={theme}&next={quote(shot.path, safe='/?=&')}"
    else:
        url = f"{base}/_show/theme/{theme}?next={quote(shot.path, safe='/?=&')}"
    width, height = shot.size
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.unlink()
    with tempfile.TemporaryDirectory(prefix="cscm_browser_") as work:
        # a profile of its own, and the picture beside it on the local disk (the browser cannot
        # always write to a network share, and it clears its profile folder)
        profile = Path(work) / "profile"
        local = Path(work) / "shot.png"
        command = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--disable-extensions",
            "--force-device-scale-factor=1",
            f"--window-size={width},{height}",
            f"--user-data-dir={profile}",
            "--virtual-time-budget=4000",
            f"--screenshot={local}",
        ]
        command.append(url)
        subprocess.run(command, capture_output=True, timeout=90, check=False)  # nosec B603
        for _ in range(20):  # a browser that hands over to another process writes a moment later
            if local.is_file() and local.stat().st_size >= 2000:
                break
            time.sleep(0.5)
        if not local.is_file() or local.stat().st_size < 2000:
            raise RuntimeError(
                f"No screenshot of {shot.name} ({url}); is the browser allowed to start?"
            )
        if shot.skip or shot.crop_left:
            _cut(local, shot.skip, shot.crop_left)
        shutil.copyfile(local, target)
    return target


def take_all(base: str, shots: list[Shot], folder: Path) -> dict[str, Path]:
    browser = find_browser()
    return {s.name: take(base, s, folder / f"{s.name}.png", browser) for s in shots}


def _cut(path: Path, band: tuple[int, int] | None, left: int) -> None:
    """Removes the rows `band` from a screenshot, so a long page shows its top and a later part."""
    from PIL import Image

    with Image.open(path) as image:
        image = image.convert("RGB")
        joined = image
        if band:
            first, last = band
            top = image.crop((0, 0, image.width, first))
            bottom = image.crop((0, last, image.width, image.height))
            joined = Image.new("RGB", (image.width, top.height + bottom.height))
            joined.paste(top, (0, 0))
            joined.paste(bottom, (0, top.height))
        if left:
            joined = joined.crop((left, 0, joined.width, joined.height))
    joined.save(path)

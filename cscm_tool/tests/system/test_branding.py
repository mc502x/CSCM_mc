"""The identity of the product (FR-187): the full name, the owner on top of every title page and
the logo, written once and shown the same way in the documents, the decks and the application.

TC-074. Requirements: FR-187, FR-185, FR-186.
"""

import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image

from app import branding
from tests.helpers import login_as, make_cast

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
IMG = ROOT / "app" / "static" / "img"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_the_owner_the_long_name_and_the_logo_are_written_once():
    assert branding.PRODUCT == "CSCM Tool"
    assert branding.LONG_NAME == "Controller Status Code Management Tool"
    assert branding.OWNER_ROLES == "Software Owner and Administrator"
    assert branding.OWNER_LINE == (
        "Software Owner and Administrator: Bastian Ritter · bastian.ritter@senvion.in"
    )


def test_the_guide_names_the_same_owner():
    guide = (ROOT.parent / "DEPLOYMENT-QUICKSTART.md").read_text(encoding="utf-8")
    assert branding.OWNER_NAME in guide and branding.OWNER_EMAIL in guide


def test_the_logo_files_exist_and_are_drawn():
    svg = ET.parse(IMG / "cscm-logo.svg").getroot()
    assert svg.get("viewBox") == "0 0 256 256" and svg.get("role") == "img"
    assert svg.get("aria-label") == "CSCM Tool"
    shapes = [child.tag.split("}")[1] for child in svg]
    assert (
        shapes.count("polygon") >= 4 and shapes.count("circle") >= 6
    )  # blades, tower, ring, lights
    picture = Image.open(IMG / "cscm-logo-512.png")
    assert picture.size == (512, 512) and picture.mode == "RGBA"
    assert picture.getpixel((0, 0))[3] == 0  # the corner outside the tile is transparent
    assert picture.getpixel((256, 40))[3] == 255  # the tile is drawn
    maker = _load("make_logo", SCRIPTS / "make_logo.py")
    assert (IMG / "cscm-logo.svg").read_text(encoding="utf-8") == maker.svg()


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


def test_the_menu_bar_and_the_login_page_show_the_logo(client, cast):
    login = client.get("/login").get_data(as_text=True)
    assert 'class="login-logo"' in login and "img/cscm-logo.svg" in login
    assert 'rel="icon"' in login  # the icon of the browser tab
    login_as(client, cast["engineer"])
    page = client.get("/status-codes").get_data(as_text=True)
    assert 'class="brand-logo"' in page and page.count("img/cscm-logo.svg") >= 2


def test_every_title_page_carries_the_identity(tmp_path):
    pdf_tool = _load("build_docs_pdf", SCRIPTS / "build_docs_pdf.py")
    import datetime

    pdf = pdf_tool.DocPdf("note", {})
    texts: list[str] = []
    original = pdf.cell

    def record(*args, **kwargs):
        text = kwargs.get("text") or (args[2] if len(args) > 2 else "")
        texts.append(str(text))
        return original(*args, **kwargs)

    pdf.cell = record  # type: ignore[method-assign]
    pdf_tool.title_page(pdf, "manual", datetime.date(2026, 1, 1), "abc1234", "0" * 64)
    assert branding.OWNER_LINE in texts
    assert branding.PRODUCT in texts and branding.LONG_NAME in texts
    assert texts.index(branding.OWNER_LINE) < texts.index(branding.PRODUCT)  # on top

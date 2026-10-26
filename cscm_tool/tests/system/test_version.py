"""The version of the application is written once and shown where a person or a monitor looks for
it (FR-184): the menu, the login page and the health endpoints; pyproject.toml stays equal to it.

TC-049. Requirements: FR-184, NFR-013.
"""

import re
import tomllib
from pathlib import Path

from app.version import VERSION
from tests.helpers import login_as, make_cast

ROOT = Path(__file__).resolve().parents[2]


def test_the_version_is_a_release_number_and_pyproject_agrees():
    assert re.fullmatch(r"\d+\.\d+\.\d+", VERSION)
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == VERSION


def test_the_health_endpoints_name_the_version(client):
    assert client.get("/api/v1/health").get_json() == {"status": "ok", "version": VERSION}
    ready = client.get("/api/v1/health/ready").get_json()
    assert ready["version"] == VERSION and ready["status"] in ("ok", "degraded")


def test_the_login_page_and_the_menu_show_the_version(client, make_user):
    assert f"CSCM Tool v{VERSION}" in client.get("/login").get_data(as_text=True)
    cast = make_cast(make_user)
    for role in ("viewer", "engineer", "admin"):
        login_as(client, cast[role])
        page = client.get("/status-codes").get_data(as_text=True)
        assert page.count(f"CSCM Tool v{VERSION}") == 1
        client.post("/logout")


def test_the_api_contract_documents_the_version_in_both_health_answers():
    spec = (ROOT.parent / "docs" / "artifacts" / "openapi.yaml").read_text(encoding="utf-8")
    assert spec.count("version: { type: string") >= 2

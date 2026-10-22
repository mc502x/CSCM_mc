"""SEC-025: standard security headers on every response."""

import re
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parents[2] / "app" / "templates"


def test_api_response_has_security_headers(client):
    headers = client.get("/api/v1/health").headers

    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Referrer-Policy"] == "same-origin"
    assert headers["Cache-Control"] == "no-store"
    csp = headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "unsafe-eval" not in csp


def test_ui_page_has_csp_and_no_hsts_over_plain_http(client):
    response = client.get("/login")

    assert "Content-Security-Policy" in response.headers
    assert "Strict-Transport-Security" not in response.headers


def test_hsts_sent_over_https(client):
    response = client.get("/api/v1/health", base_url="https://localhost")

    assert "max-age=" in response.headers["Strict-Transport-Security"]


def test_templates_have_no_inline_script_or_handlers():
    """The CSP forbids inline script; guard against regressions."""
    offenders = []
    for path in TEMPLATES.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"<script(?![^>]*\bsrc=)|\son[a-z]+\s*=|javascript:", text):
            offenders.append(f"{path.relative_to(TEMPLATES)}: {match.group(0).strip()}")
    assert offenders == []

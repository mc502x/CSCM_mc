"""US-120 / TC-029: block cloud-SDK imports, cloud identity providers and
externally hosted assets (docs/11-security-architecture.md §12)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_MODULES = (
    "boto3",
    "botocore",
    "azure",
    "msal",
    "google.cloud",
    "google.auth",
    "googleapiclient",
    "firebase_admin",
    "oci",
    "ibm_boto3",
    "sentry_sdk",
    "datadog",
    "newrelic",
    "segment",
    "mixpanel",
)

IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([\w.]+)", re.MULTILINE)
EXTERNAL_URL_RE = re.compile(
    r"""(?:src|href)\s*=\s*["']\s*(?:https?:)?//(?!localhost|127\.0\.0\.1)"""
)


def _is_forbidden(module: str) -> bool:
    return any(module == m or module.startswith(m + ".") for m in FORBIDDEN_MODULES)


def test_no_cloud_sdk_imports_in_source():
    offenders = []
    for path in list((ROOT / "app").rglob("*.py")) + [ROOT / "wsgi.py", ROOT / "dev_server.py"]:
        for module in IMPORT_RE.findall(path.read_text(encoding="utf-8")):
            if _is_forbidden(module):
                offenders.append(f"{path.relative_to(ROOT)}: {module}")
    assert offenders == []


def test_no_cloud_sdk_in_requirements():
    names = []
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            names.append(re.split(r"[=<>\[ ]", line, maxsplit=1)[0].lower().replace("-", "_"))
    offenders = [n for n in names if _is_forbidden(n.split(".")[0])]
    assert offenders == []


def test_templates_and_static_reference_no_external_assets():
    offenders = []
    for path in (ROOT / "app" / "templates").rglob("*.html"):
        if EXTERNAL_URL_RE.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(ROOT)))
    for path in (ROOT / "app" / "static").rglob("*.css"):
        if re.search(
            r"url\(\s*[\"']?(?:https?:)?//|@import\s+[\"']?https?:",
            path.read_text(encoding="utf-8"),
        ):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []

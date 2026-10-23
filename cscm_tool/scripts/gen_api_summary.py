"""Generates the endpoint summary table of docs/09-api-specification.md §7 from the code.

    python scripts/gen_api_summary.py            # print the table
    python scripts/gen_api_summary.py --write    # replace the block in docs/09-api-specification.md

One row per operation of docs/artifacts/openapi.yaml: method, path, purpose (the first sentence
of its OpenAPI summary) and who may call it, read from the access declared on the Flask view
(`view.access`, app/auth/decorators.py), so the document cannot drift from what is enforced.
tests/system/test_docs_consistency.py fails when the block in the document differs from this
output."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

APP_DIR = Path(__file__).resolve().parents[1]
DOC = APP_DIR.parent / "docs" / "09-api-specification.md"
SPEC = APP_DIR.parent / "docs" / "artifacts" / "openapi.yaml"
START = "<!-- api-summary:start -->"
END = "<!-- api-summary:end -->"

ROLE_NAMES = {
    "ADMINISTRATOR": "Administrator",
    "STCD_OWNER": "StCd Owner",
    "ENGINEER": "Engineer",
    "REVIEWER": "Reviewer",
    "CHIEF_ENGINEER": "Chief Engineer",
    "VIEWER": "Viewer",
}
WORKING = {"ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER"}


def _normal(path: str) -> str:
    path = re.sub(r"\{[^}]*\}", "{}", path)
    return re.sub(r"<[^>]*>", "{}", path)


def _access(app) -> dict[tuple[str, str], str]:
    found: dict[tuple[str, str], str] = {}
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api/v1/"):
            continue
        view = app.view_functions[rule.endpoint]
        access = getattr(view, "access", None)
        scope = getattr(view, "_token_scope", None)
        if access is None:
            text = "Public"
        elif access[0] == "login":
            text = "Any signed-in user"
        else:
            roles = set(access[1])
            if roles == set(ROLE_NAMES):
                text = "Any signed-in user"
            elif roles == WORKING:
                text = "Working roles (not Viewer)"
            elif roles == WORKING | {"STCD_OWNER"}:
                text = "Working roles (not Viewer) and StCd Owner (read only)"
            else:
                text = ", ".join(ROLE_NAMES[r] for r in ROLE_NAMES if r in roles)
        if scope:
            text += f"; API token `{scope}`"
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            found[(method, _normal(rule.rule[len("/api/v1") :]))] = text
    return found


def _purpose(summary: str) -> str:
    first = re.split(r"(?<=[.!?])\s(?=[A-Z])", " ".join(summary.split()), maxsplit=1)[0].rstrip(".")
    first = first.replace("|", "/")
    return first if len(first) <= 140 else first[:137].rstrip() + "..."


def rows() -> list[str]:
    sys.path.insert(0, str(APP_DIR))
    from app import create_app

    app = create_app("testing")
    access = _access(app)
    spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
    lines = ["| Method | Path | Purpose | Who may call it |", "|---|---|---|---|"]
    for path in spec["paths"]:
        for method, op in spec["paths"][path].items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            who = access.get((method.upper(), _normal(path)), "?")
            lines.append(
                f"| {method.upper()} | `{path}` | {_purpose(op.get('summary', ''))} | {who} |"
            )
    return lines


def block() -> str:
    return "\n".join([START, *rows(), END])


def main() -> int:
    text = block()
    if "--write" not in sys.argv:
        print(text)
        return 0
    doc = DOC.read_text(encoding="utf-8")
    if START in doc and END in doc:
        head, rest = doc.split(START, 1)
        tail = rest.split(END, 1)[1]
        doc = head + text + tail
    else:
        raise SystemExit(f"{DOC.name} has no {START} / {END} markers")
    DOC.write_text(doc, encoding="utf-8", newline="")
    print(f"updated {DOC.name}: {len(rows()) - 2} operations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""The messages of the service layer that a person can read in the UI (docs/26-translations.md).

The services raise errors with a fixed English sentence; the web screens show them in a flash
message through `translate()`, so a sentence that is in a language's catalogue appears in that
language and any other stays English. The API keeps the English text: its messages are part of the
contract. This module only *finds* the sentences (by reading the source), so the translation
inventory cannot miss one."""

import ast
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGES = ("services", "domain", "importers", "auth")


@cache
def service_messages() -> dict[str, list[str]]:
    """English sentence -> the modules that raise it (a literal first argument of an *Error)."""
    found: dict[str, set[str]] = {}
    for package in PACKAGES:
        for path in sorted((ROOT / package).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call)):
                    continue
                func = node.exc.func
                name = getattr(func, "id", getattr(func, "attr", ""))
                if not name.endswith("Error") and name != "ValidationFailed":
                    continue
                for arg in node.exc.args[:1]:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        found.setdefault(arg.value, set()).add(path.stem)
    return {text: sorted(files) for text, files in found.items()}

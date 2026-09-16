"""CSV catalogue export. SEC (docs/11-security-architecture.md §6): sanitizes
formula-injection characters, since Excel/Sheets treats a leading =, +, -, or
@ in a cell as a formula to evaluate rather than literal text."""

import csv
import io
from typing import Any

_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _sanitize(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def build_csv(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for row in rows:
        writer.writerow({k: _sanitize(v) for k, v in row.items()})
    return buffer.getvalue().encode("utf-8")

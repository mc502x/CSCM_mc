"""XLSX catalogue export (FR-045, added 2026-09-17). openpyxl — pure Python,
no system dependency, consistent with the no-cloud/offline-deployable
constraint (docs/11-security-architecture.md §12, NFR-008). Same
formula-injection sanitization as CSV (SEC-023): Excel treats a leading =,
+, -, or @ in a cell as a formula to evaluate rather than literal text."""

import io
from typing import Any

from openpyxl import Workbook

from app.utils import xlsx_text

_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _sanitize(value: Any) -> Any:
    value = xlsx_text(value)
    if isinstance(value, str) and value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def build_xlsx(rows: list[dict]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Status Codes"

    if rows:
        columns = list(rows[0].keys())
        sheet.append(columns)
        for row in rows:
            sheet.append([_sanitize(row.get(col)) for col in columns])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()

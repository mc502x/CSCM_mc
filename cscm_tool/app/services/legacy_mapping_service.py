"""Legacy -> new status code mapping (FR-048u, docs/06-data-dictionary.md section 5a).

The mapping is not a table of its own: it is `status_code.legacy_reference_number` read together
with the Functional System Group's controller type (Main Controller / Hub Controller) and the
identifier the code was issued - or, for an imported code that is still a Draft, the number it has
reserved. One field means one truth; there is nothing to keep in step.

The direction is **legacy -> new only**. The new library holds more codes than the old one, so a
code without a legacy number is normal ("n/a"), and asking which legacy number a new code replaced
is answered by the code's own legacy field, never by a reverse table."""

from __future__ import annotations

import csv
import io
from typing import Any

from openpyxl import Workbook
from sqlalchemy import text

from app.extensions import db

_HEADERS = (
    "controller",
    "legacy_number",
    "new_identifier",
    "identifier_state",
    "title",
    "lifecycle_state",
    "group",
    "subgroup",
)


def _sort_key(entry: dict[str, Any]) -> tuple:
    legacy = entry["legacy_number"]
    numeric = legacy.isdigit()
    return (entry["controller"], 0 if numeric else 1, int(legacy) if numeric else 0, legacy)


def _safe(value: Any) -> Any:
    return (
        "'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@")) else value
    )


class LegacyMappingService:
    @staticmethod
    def entries(
        controller: str | None = None, query: str | None = None, state: str | None = None
    ) -> list[dict[str, Any]]:
        """Every catalogue code that carries a legacy number, sorted by controller and number.
        `state` filters on identifier_state (issued | reserved | pending)."""
        rows = db.session.execute(
            text(
                "SELECT sc.id, sc.status_code_identifier, sc.reserved_identifier, "
                "sc.legacy_reference_number, g.controller_type, g.code, s.code, "
                "r.title, r.lifecycle_status "
                "FROM status_code sc "
                "JOIN lookup_functional_system_group g ON g.id = sc.functional_system_group_id "
                "JOIN lookup_functional_subgroup s ON s.id = sc.functional_subgroup_id "
                "LEFT JOIN status_code_revision r ON r.status_code_id = sc.id AND r.is_current = 1 "
                "WHERE sc.is_sandbox = 0 AND sc.legacy_reference_number IS NOT NULL "
                "AND TRIM(sc.legacy_reference_number) <> ''"
            )
        ).all()
        needle = (query or "").strip().lower()
        entries: list[dict[str, Any]] = []
        for (
            code_id,
            issued,
            reserved,
            legacy,
            controller_type,
            group,
            subgroup,
            title,
            life,
        ) in rows:
            kind = "HC" if controller_type == "HUB" else "MC"
            if controller and controller.upper() != kind:
                continue
            identifier_state = "issued" if issued else "reserved" if reserved else "pending"
            if state and state != identifier_state:
                continue
            entry = {
                "status_code_id": code_id,
                "controller": kind,
                "legacy_number": str(legacy).strip(),
                "new_identifier": issued or reserved,
                "identifier_state": identifier_state,
                "title": title or "",
                "lifecycle_state": life or "",
                "group": group,
                "subgroup": subgroup,
            }
            if (
                needle
                and needle
                not in " ".join(
                    str(entry[k]) for k in ("legacy_number", "new_identifier", "title") if entry[k]
                ).lower()
            ):
                continue
            entries.append(entry)
        entries.sort(key=_sort_key)
        return entries

    @staticmethod
    def lookup(controller: str, legacy_number: str) -> dict[str, Any] | None:
        """The code that replaced a legacy number; None if nothing in the catalogue carries it."""
        wanted = str(legacy_number).strip()
        for entry in LegacyMappingService.entries(controller=controller):
            if entry["legacy_number"] == wanted:
                return entry
        return None

    @staticmethod
    def summary() -> dict[str, Any]:
        """How the new library relates to the legacy one. `new_without_legacy` is the part with
        no legacy counterpart; the mapping back from there is not applicable."""
        total = int(
            db.session.execute(
                text("SELECT COUNT(*) FROM status_code WHERE is_sandbox = 0")
            ).scalar()
            or 0
        )
        entries = LegacyMappingService.entries()
        by_controller = {"MC": 0, "HC": 0}
        for entry in entries:
            by_controller[entry["controller"]] += 1
        return {
            "codes_total": total,
            "with_legacy_number": len(entries),
            "new_without_legacy": total - len(entries),
            "by_controller": by_controller,
            "identifier_issued": sum(1 for e in entries if e["identifier_state"] == "issued"),
            "identifier_reserved": sum(1 for e in entries if e["identifier_state"] == "reserved"),
            "identifier_pending": sum(1 for e in entries if e["identifier_state"] == "pending"),
        }

    @staticmethod
    def export_csv(entries: list[dict[str, Any]]) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(_HEADERS)
        for entry in entries:
            writer.writerow([_safe(entry[h] if entry[h] is not None else "") for h in _HEADERS])
        return buffer.getvalue().encode("utf-8-sig")

    @staticmethod
    def export_xlsx(entries: list[dict[str, Any]]) -> bytes:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Legacy to new"
        sheet.append(list(_HEADERS))
        for entry in entries:
            sheet.append([_safe(entry[h] if entry[h] is not None else "") for h in _HEADERS])
        sheet.freeze_panes = "A2"
        note = workbook.create_sheet("Note")
        note.append(
            ["Legacy to new only. Codes of the new library without a legacy number are not listed."]
        )
        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

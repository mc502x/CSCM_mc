"""Library Import (EPIC-14, new 2026-09-17; migration toolkit I-05/I-12/I-32, 2026-10-22).
See docs/06-data-dictionary.md §5, docs/05-governance-handbook.md §6b,
docs/09-api-specification.md §6b.

Every row that passes validation becomes an ordinary Draft
StatusCode/StatusCodeRevision/ChangeRequest (cr_type=IMPORT) -- a faster
data-entry path, never a governance bypass: it still needs Cross-Domain
Sign-Off, both Review sign-offs, and Chief Engineer approval before Release,
identical to a hand-typed code (FR-048c).

The toolkit around that rule:

* **template**  - `template_csv()`/`template_xlsx()` give the exact headers and the lookup
  codes (I-05b);
* **dry run**   - `dry_run()` validates every row and reports what *would* happen, creating
  nothing (I-05a);
* **update mode** - rows are matched on `legacy_reference_number` within the Functional
  System Group; a changed row revises the already-imported code (a new revision, or the
  still-open Draft) instead of creating a duplicate; an unchanged row is skipped (I-05c);
* **reconciliation** - how much of the legacy library is imported, in review, released and
  still missing (I-05d);
* **error report** - one line per problem with row, column, value and a fix hint, as CSV and
  XLSX (I-05e);
* **warnings**  - possible duplicates (I-12) and unresolvable references (I-04) are reported
  per row but never block a row;
* **background jobs** - large files are processed by a worker thread with a progress counter
  (I-32); small ones stay inside the upload request.

CSV/XLSX column headers are the same field names StatusCodeCreate uses,
except Functional System Group/Subgroup, the software versions and the eight
audience-access fields are given as their lookup **codes** (e.g. "WCNV",
"Converter", "SCADA User") rather than surrogate ids -- a legacy spreadsheet has
no way to know CSCM Tool's internal ids. Where a code is ambiguous (WTUR/WROT are
each reused for a second, numerically distinct Hub Controller group -- see
app/services/lookup_service.py), the row must also supply
`functional_system_group_range_start` to disambiguate."""

import csv
import io
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from flask import current_app
from openpyxl import Workbook, load_workbook

from app import status_code_fields
from app.domain.authz import require_roles
from app.domain.errors import DomainError, NotFoundError
from app.extensions import db
from app.models.change_request import ChangeRequest
from app.models.import_job import ImportJob
from app.models.lookup import (
    LookupAvailableGroup,
    LookupControllerSoftwareVersion,
    LookupCustomerAccess,
    LookupDevelopmentAccess,
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
    LookupGridOperatorAccess,
    LookupSalesAccess,
    LookupServiceAccess,
    LookupServicePartnerAccess,
    LookupTccAccess,
    LookupTopAccess,
    LookupTurbinePlatform,
)
from app.models.status_code import StatusCode, StatusCodeRevision
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.duplicate_service import DuplicateService
from app.services.reference_service import ReferenceService
from app.services.status_code_service import (
    StatusCodeService,
    ValidationFailed,
    revision_to_data,
)
from app.services.validation import split_identifier_list, validate_revision_fields
from app.utils import utcnow_iso

ALLOWED_EXTENSIONS = {"csv": "CSV", "xlsx": "XLSX"}

_ACCESS_FIELD_MODELS = {
    "development_access": LookupDevelopmentAccess,
    "sales_access": LookupSalesAccess,
    "tcc_access": LookupTccAccess,
    "service_access": LookupServiceAccess,
    "turbine_operator_package_access": LookupTopAccess,
    "grid_operator_access": LookupGridOperatorAccess,
    "service_partner_access": LookupServicePartnerAccess,
    "customer_access": LookupCustomerAccess,
}

_PROGRAM_FIELDS = (
    "yaw_program",
    "manual_reset_program",
    "auto_reset_program",
    "converter_reactive_power_program",
    "brake_program",
    "umrichterprogramm_gsc",
    "umrichterprogramm_msc",
    "yaw_bearing_lubrication_program",
)

REQUIRED_HEADERS = (
    "functional_system_group",
    "functional_subgroup",
    "turbine_platforms",
    "title",
    "description",
    "status_category",
    "available_group",
    "set_delay",
    "reset_delay",
)

# The template's column order; also the set of headers an import understands.
TEMPLATE_HEADERS = (
    "functional_system_group",
    "functional_system_group_range_start",
    "functional_subgroup",
    "turbine_platforms",
    "legacy_reference_number",
    "title",
    "description",
    "software_version",
    "status_category",
    "available_group",
    "alarm_flag",
    "set_delay",
    "reset_delay",
    "up_down_counter",
    "trigger_snapshot",
    "loadless_spinning_permitted",
    "number_of_times_repeated",
    "repeated_over_the_course",
    "status_code_for_repeated_error",
    *_PROGRAM_FIELDS,
    *_ACCESS_FIELD_MODELS,
    "remedy_text",
    "affected_component",
    "related_status_codes",
    "standard_references",
    "applies_from_version",
    "applies_to_version",
    "planned_effective_date",
    "planned_deprecation_date",
)

_EXAMPLE_ROW = {
    "functional_system_group": "WCNV",
    "functional_subgroup": "010xx",
    "turbine_platforms": "3XM;4XM",
    "legacy_reference_number": "1234",
    "title": "Converter DC link undervoltage",
    "description": "Raised when the DC link voltage stays below the limit for the set delay.",
    "status_category": "ERROR",
    "available_group": "27",
    "alarm_flag": "yes",
    "set_delay": "10ms",
    "reset_delay": "2min",
}

_TRUE_VALUES = {"1", "true", "yes", "y", "ja", "x"}
_HINTS = {
    "functional_system_group": (
        "Use a group code from the Lookups sheet of the template (WCNV, WGEN, ...)."
    ),
    "functional_subgroup": "Use a subgroup code that belongs to the chosen group (Lookups sheet).",
    "turbine_platforms": "List 2XM, 3XM and/or 4XM separated by ; or ,",
    "status_category": "ERROR, WARNING or INFO.",
    "set_delay": "A number with a unit, e.g. 10ms, 2s or 2min.",
    "reset_delay": "A number with a unit, e.g. 10ms, 2s or 2min.",
    "available_group": "A whole number, e.g. 27 (see the Lookups sheet).",
    "title": "1-120 characters.",
    "description": "10-4000 characters, different from the title.",
    "legacy_reference_number": "The old status code number; unique per Functional System Group.",
    "applies_from_version": "A software version code from the Lookups sheet, or leave empty.",
    "applies_to_version": "A software version code from the Lookups sheet, or leave empty.",
    "related_status_codes": "Identifiers like StCd-01234 separated by commas.",
    "planned_effective_date": "A date like 2027-03-31.",
    "planned_deprecation_date": "A date like 2027-03-31.",
}


@dataclass
class Issue:
    column: str
    value: Any
    message: str
    hint: str = ""

    def as_dict(self) -> dict:
        return {
            "column": self.column,
            "value": "" if self.value is None else str(self.value),
            "message": self.message,
            "hint": self.hint or _HINTS.get(self.column, ""),
        }


class ImportValidationError(DomainError):
    """One lookup/parse failure inside a row; collected as an Issue, never raised to HTTP."""

    def __init__(self, column: str, value: Any, message: str, hint: str = ""):
        super().__init__(message)
        self.issue = Issue(column, value, message, hint)


@dataclass
class RowResult:
    row: int
    action: str = "error"  # create | update | skip | error
    issues: list[Issue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    identifier: str | None = None

    def as_dict(self) -> dict:
        return {
            "row": self.row,
            "action": self.action,
            "errors": [i.as_dict() for i in self.issues],
            "warnings": self.warnings,
            "status_code_identifier": self.identifier,
        }


def _parse_bool(value: Any) -> bool:
    return str(value).strip().lower() in _TRUE_VALUES if value not in (None, "") else False


def _parse_int(value: Any, column: str = "") -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError) as exc:
        raise ImportValidationError(column, value, f"'{value}' is not a valid number") from exc


def _text(row: dict, key: str) -> str:
    value = row.get(key)
    return "" if value is None else str(value).strip()


def _resolve_group(code: str, range_start_hint: Any) -> LookupFunctionalSystemGroup:
    matches = (
        db.session.query(LookupFunctionalSystemGroup)
        .filter(
            LookupFunctionalSystemGroup.code == code, LookupFunctionalSystemGroup.is_active == 1
        )
        .all()
    )
    if not matches:
        raise ImportValidationError(
            "functional_system_group", code, f"Unknown functional_system_group code: {code}"
        )
    if len(matches) == 1:
        return matches[0]
    if range_start_hint in (None, ""):
        ranges = ", ".join(f"{m.range_start}-{m.range_end}" for m in matches)
        raise ImportValidationError(
            "functional_system_group_range_start",
            "",
            f"functional_system_group '{code}' is ambiguous (ranges: {ranges}); "
            "supply functional_system_group_range_start to disambiguate",
            "Enter the first number of the range, e.g. 9000 for the Main Controller group.",
        )
    hint = _parse_int(range_start_hint, "functional_system_group_range_start")
    for m in matches:
        if m.range_start == hint:
            return m
    raise ImportValidationError(
        "functional_system_group_range_start",
        range_start_hint,
        f"No functional_system_group '{code}' with range_start {hint}",
    )


def _resolve_subgroup(group: LookupFunctionalSystemGroup, code: str) -> LookupFunctionalSubgroup:
    subgroup = (
        db.session.query(LookupFunctionalSubgroup)
        .filter(
            LookupFunctionalSubgroup.functional_system_group_id == group.id,
            LookupFunctionalSubgroup.code == code,
            LookupFunctionalSubgroup.is_active == 1,
        )
        .first()
    )
    if subgroup is None:
        known = ", ".join(
            s.code
            for s in db.session.query(LookupFunctionalSubgroup)
            .filter(LookupFunctionalSubgroup.functional_system_group_id == group.id)
            .order_by(LookupFunctionalSubgroup.sort_order)
        )
        raise ImportValidationError(
            "functional_subgroup",
            code,
            f"Unknown functional_subgroup '{code}' within Functional System Group '{group.code}'",
            f"Subgroups of {group.code}: {known}.",
        )
    return subgroup


def _resolve_access(field_name: str, code: str | None) -> int | None:
    if not code:
        return None
    model = _ACCESS_FIELD_MODELS[field_name]
    value = (
        db.session.query(model).filter(model.code == code, model.is_active == 1).first()  # type: ignore[attr-defined]
    )
    if value is None:
        # People type the label ("SCADA User"), the seed stores a code ("SCADA_USER").
        value = (
            db.session.query(model)
            .filter(model.label == code, model.is_active == 1)  # type: ignore[attr-defined]
            .first()
        )
    if value is None:
        raise ImportValidationError(
            field_name, code, f"Unknown {field_name} code: {code}", "See the Lookups sheet."
        )
    return value.id  # type: ignore[attr-defined]


def _resolve_version(column: str, code: str | None) -> int | None:
    if not code:
        return None
    version = (
        db.session.query(LookupControllerSoftwareVersion)
        .filter(
            LookupControllerSoftwareVersion.code == code,
            LookupControllerSoftwareVersion.is_active == 1,
        )
        .first()
    )
    if version is None:
        raise ImportValidationError(column, code, f"Unknown controller software version: {code}")
    return version.id


def _row_to_data(row: dict, issues: list[Issue]) -> dict | None:
    """Resolves lookup codes to the surrogate-id-based dict shape
    StatusCodeService._build_revision expects (see module docstring). Problems are
    appended to `issues` (all of a row's problems at once, not just the first)."""

    def guarded(func, *args):
        try:
            return func(*args)
        except ImportValidationError as exc:
            issues.append(exc.issue)
            return None

    group = guarded(
        _resolve_group,
        _text(row, "functional_system_group"),
        row.get("functional_system_group_range_start"),
    )
    subgroup = (
        guarded(_resolve_subgroup, group, _text(row, "functional_subgroup")) if group else None
    )

    platforms_raw = _text(row, "turbine_platforms")
    turbine_platforms = [p.strip() for p in platforms_raw.replace(";", ",").split(",") if p.strip()]
    known_platforms = {
        p.code for p in db.session.query(LookupTurbinePlatform).filter_by(is_active=1)
    }
    for platform in turbine_platforms:
        if platform not in known_platforms:
            issues.append(
                Issue(
                    "turbine_platforms",
                    platform,
                    f"Unknown turbine platform: {platform}",
                    "Valid platforms: " + ", ".join(sorted(known_platforms)),
                )
            )

    data: dict[str, Any] = {
        "functional_system_group": group.id if group else None,
        "functional_subgroup": subgroup.id if subgroup else None,
        "turbine_platforms": turbine_platforms,
        "title": _text(row, "title"),
        "description": _text(row, "description"),
        "software_version": _text(row, "software_version") or None,
        "status_category": _text(row, "status_category").upper(),
        "available_group": guarded(_parse_int, row.get("available_group"), "available_group"),
        "alarm_flag": _parse_bool(row.get("alarm_flag")),
        "set_delay": _text(row, "set_delay"),
        "reset_delay": _text(row, "reset_delay"),
        "up_down_counter": _parse_bool(row.get("up_down_counter")),
        "trigger_snapshot": _parse_bool(row.get("trigger_snapshot")),
        "loadless_spinning_permitted": _parse_bool(row.get("loadless_spinning_permitted")),
        "number_of_times_repeated": guarded(
            _parse_int, row.get("number_of_times_repeated"), "number_of_times_repeated"
        ),
        "repeated_over_the_course": _text(row, "repeated_over_the_course") or None,
        "status_code_for_repeated_error": guarded(
            _parse_int, row.get("status_code_for_repeated_error"), "status_code_for_repeated_error"
        ),
        "legacy_reference_number": _text(row, "legacy_reference_number") or None,
        "remedy_text": _text(row, "remedy_text") or None,
        "affected_component": _text(row, "affected_component") or None,
        "related_status_codes": ", ".join(split_identifier_list(_text(row, "related_status_codes")))
        or None,
        "standard_references": _text(row, "standard_references") or None,
        "applies_from_version": guarded(
            _resolve_version, "applies_from_version", _text(row, "applies_from_version") or None
        ),
        "applies_to_version": guarded(
            _resolve_version, "applies_to_version", _text(row, "applies_to_version") or None
        ),
        "planned_effective_date": _text(row, "planned_effective_date") or None,
        "planned_deprecation_date": _text(row, "planned_deprecation_date") or None,
    }
    for field_name in _PROGRAM_FIELDS:
        data[field_name] = guarded(_parse_int, row.get(field_name), field_name) or 0
    for field_name in _ACCESS_FIELD_MODELS:
        data[field_name] = guarded(_resolve_access, field_name, _text(row, field_name) or None)

    value_of = {
        i.column: i for i in issues
    }  # a field already reported as unreadable is not validated again
    for error in validate_revision_fields(data):
        if error["field"] in value_of:
            continue
        column = error["field"]
        issues.append(
            Issue(
                column,
                row.get(column) if column in row else "",
                error["message"],
                _HINTS.get(column, ""),
            )
        )
    return data


def _read_csv_rows(content: bytes) -> tuple[list[str], list[dict]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = [h.strip() for h in (reader.fieldnames or [])]
    rows = []
    for raw in reader:
        rows.append({(k or "").strip(): v for k, v in raw.items()})
    return headers, rows


def _read_xlsx_rows(content: bytes) -> tuple[list[str], list[dict]]:
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    sheet = workbook["Import"] if "Import" in workbook.sheetnames else workbook.active
    rows_iter = sheet.iter_rows(values_only=True)
    headers = [str(h).strip() if h is not None else "" for h in next(rows_iter, [])]
    rows = []
    for raw_row in rows_iter:
        if all(cell is None for cell in raw_row):
            continue
        rows.append({headers[i]: raw_row[i] for i in range(len(headers)) if i < len(raw_row)})
    return headers, rows


def _parse_upload(filename: str, content: bytes) -> tuple[str, str, list[dict]]:
    extension = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
    source_format = ALLOWED_EXTENSIONS.get(extension)
    if source_format is None:
        raise ValueError("Only .csv and .xlsx files are accepted.")
    try:
        headers, rows = (
            _read_csv_rows(content) if source_format == "CSV" else _read_xlsx_rows(content)
        )
    except (UnicodeDecodeError, csv.Error, KeyError, OSError, ValueError) as exc:
        raise ValueError(f"The file could not be read as {source_format}: {exc}") from exc
    missing = [h for h in REQUIRED_HEADERS if h not in headers]
    if missing:
        raise ValueError(
            "The file is missing required column(s): "
            + ", ".join(missing)
            + ". Download the template for the exact headers."
        )
    limit = current_app.config.get("IMPORT_MAX_ROWS", 10000)
    if len(rows) > limit:
        raise ValueError(f"The file has {len(rows)} rows; the limit is {limit} per upload.")
    return extension, source_format, rows


# ------------------------------------------------------------------- matching / comparison
_COMPARED = (
    "turbine_platforms",
    "title",
    "description",
    "software_version",
    "status_category",
    "available_group",
    "alarm_flag",
    "set_delay",
    "reset_delay",
    "up_down_counter",
    "trigger_snapshot",
    "loadless_spinning_permitted",
    "number_of_times_repeated",
    "repeated_over_the_course",
    "status_code_for_repeated_error",
    *_PROGRAM_FIELDS,
    *_ACCESS_FIELD_MODELS,
    "remedy_text",
    "affected_component",
    "related_status_codes",
    "standard_references",
    "applies_from_version",
    "applies_to_version",
)


def _normalise(value: Any) -> Any:
    if isinstance(value, dict):
        return {int(k): v for k, v in value.items()}
    if isinstance(value, list):
        return sorted(value)
    if value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    return value


def changed_fields(current: StatusCodeRevision, data: dict) -> list[str]:
    """The compared fields in which a row (or a program file) differs from the current revision."""
    existing = revision_to_data(current)
    # the fields of the generated programs are compared when the source carries them (v4.1)
    compared = [
        *_COMPARED,
        *(f for f in (*status_code_fields.NEW_FIELDS, "user_groups") if f in data),
    ]
    return [f for f in compared if _normalise(existing.get(f)) != _normalise(data.get(f))]


def _unchanged(current: StatusCodeRevision, data: dict) -> bool:
    return not changed_fields(current, data)


def _find_existing(legacy_reference: str, group_id: int) -> list[StatusCode]:
    return (
        db.session.query(StatusCode)
        .filter(
            StatusCode.legacy_reference_number == legacy_reference,
            StatusCode.functional_system_group_id == group_id,
            StatusCode.is_sandbox == 0,
        )
        .order_by(StatusCode.id)
        .all()
    )


class ImportService:
    # ------------------------------------------------------------------ template
    @staticmethod
    def template_csv() -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(TEMPLATE_HEADERS)
        writer.writerow([_EXAMPLE_ROW.get(h, "") for h in TEMPLATE_HEADERS])
        return buffer.getvalue().encode("utf-8-sig")

    @staticmethod
    def lookup_listing() -> list[tuple[str, list[list[str]]]]:
        """(column, [[code, label, note], ...]) for the Lookups sheet."""
        sections: list[tuple[str, list[list[str]]]] = []
        groups = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter_by(is_active=1)
            .order_by(LookupFunctionalSystemGroup.sort_order)
            .all()
        )
        sections.append(
            (
                "functional_system_group (+ functional_system_group_range_start)",
                [
                    [
                        g.code,
                        g.label,
                        f"range_start {g.range_start} ({g.range_start}-{g.range_end})",
                    ]
                    for g in groups
                ],
            )
        )
        subgroups = []
        for g in groups:
            for s in (
                db.session.query(LookupFunctionalSubgroup)
                .filter_by(functional_system_group_id=g.id, is_active=1)
                .order_by(LookupFunctionalSubgroup.sort_order)
            ):
                subgroups.append(
                    [
                        s.code,
                        s.label,
                        f"in {g.code} {g.range_start}: {s.sub_range_start}-{s.sub_range_end}",
                    ]
                )
        sections.append(("functional_subgroup", subgroups))
        sections.append(
            (
                "turbine_platforms",
                [
                    [p.code, p.label, ""]
                    for p in db.session.query(LookupTurbinePlatform).filter_by(is_active=1)
                ],
            )
        )
        sections.append(
            ("status_category", [["ERROR", "", ""], ["WARNING", "", ""], ["INFO", "", ""]])
        )
        sections.append(
            (
                "available_group",
                [
                    [str(a.code), a.label or "", ""]
                    for a in db.session.query(LookupAvailableGroup)
                    .filter_by(is_active=1)
                    .order_by(LookupAvailableGroup.code)
                ],
            )
        )
        for column, access_model in _ACCESS_FIELD_MODELS.items():
            model: Any = access_model
            sections.append(
                (
                    column,
                    [
                        [v.code, v.label, "" if v.audience_visible else "hidden from this audience"]
                        for v in db.session.query(model)
                        .filter_by(is_active=1)
                        .order_by(model.sort_order)
                    ],
                )
            )
        versions = [
            [v.code, v.label, ""]
            for v in db.session.query(LookupControllerSoftwareVersion)
            .filter_by(is_active=1)
            .order_by(LookupControllerSoftwareVersion.sort_order)
        ]
        sections.append(("applies_from_version / applies_to_version", versions))
        return sections

    @staticmethod
    def template_xlsx() -> bytes:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Import"
        sheet.append(list(TEMPLATE_HEADERS))
        sheet.append([_EXAMPLE_ROW.get(h, "") for h in TEMPLATE_HEADERS])
        sheet.freeze_panes = "A2"

        guide = workbook.create_sheet("Instructions")
        for line in (
            "One row per status code on the 'Import' sheet; delete the example row.",
            "Required columns: " + ", ".join(REQUIRED_HEADERS) + ".",
            "Lookup values are given as codes - see the 'Lookups' sheet.",
            "turbine_platforms: separate several with ; or ,",
            "Boolean columns accept yes/no, true/false, 1/0.",
            "Use 'Validate only' on the import page first: nothing is created until it is clean.",
            "Update mode: rows are matched on legacy_reference_number within the Functional System "
            "Group; a changed row opens a new revision instead of a duplicate.",
            "Imported rows are ordinary Drafts and still go through the full governance cycle.",
        ):
            guide.append([line])

        lookups = workbook.create_sheet("Lookups")
        for column, values in ImportService.lookup_listing():
            lookups.append([column])
            lookups.append(["code", "label", "note"])
            for entry in values:
                lookups.append(entry)
            lookups.append([])
        buffer = io.BytesIO()
        workbook.save(buffer)
        return buffer.getvalue()

    # ------------------------------------------------------------------ row evaluation
    @staticmethod
    def _evaluate(
        row: dict, index: int, mode: str, seen: set[tuple[str, int]]
    ) -> tuple[RowResult, dict | None, StatusCode | None]:
        result = RowResult(row=index)
        data = _row_to_data(row, result.issues)
        existing: StatusCode | None = None
        if data is None or result.issues:
            return result, data, None

        legacy = data.get("legacy_reference_number")
        group_id = data["functional_system_group"]
        matches = _find_existing(legacy, group_id) if legacy else []
        key = (legacy, group_id) if legacy else None

        if len(matches) > 1:
            result.issues.append(
                Issue(
                    "legacy_reference_number",
                    legacy,
                    "More than one catalogue code carries this legacy number in the group: "
                    + ", ".join(m.status_code_identifier or f"#{m.id}" for m in matches),
                    "Resolve the duplicate in the catalogue first.",
                )
            )
        elif key is not None and key in seen:
            result.issues.append(
                Issue(
                    "legacy_reference_number",
                    legacy,
                    "The same legacy number appears twice in this file.",
                    "Keep one row per legacy number.",
                )
            )
        elif mode == "UPDATE":
            if not legacy:
                result.issues.append(
                    Issue(
                        "legacy_reference_number",
                        "",
                        "Update mode needs the legacy number to find the code to revise.",
                        "Fill in legacy_reference_number or use create mode.",
                    )
                )
            elif matches:
                existing = matches[0]
                if existing.functional_subgroup_id != data["functional_subgroup"]:
                    result.issues.append(
                        Issue(
                            "functional_subgroup",
                            row.get("functional_subgroup"),
                            "The Functional Subgroup of an existing code cannot change (BR-001).",
                            f"It is {existing.functional_subgroup.code}.",
                        )
                    )
        elif matches:
            first = matches[0]
            result.issues.append(
                Issue(
                    "legacy_reference_number",
                    legacy,
                    f"Already imported as {first.status_code_identifier or 'a draft'} "
                    f"(id {first.id}).",
                    "Upload in update mode to revise it instead of creating a duplicate.",
                )
            )
        if key is not None:
            seen.add(key)
        if result.issues:
            return result, data, None

        if existing is None:
            result.action = "create"
            for hit in DuplicateService.find_similar(data["title"], data["functional_subgroup"]):
                result.warnings.append(
                    f"Similar to {hit['status_code_identifier'] or 'a draft'} "
                    f"\"{hit['title']}\" ({int(hit['score'] * 100)}% alike)."
                )
            number = data.get("status_code_for_repeated_error")
            if number is not None and not ReferenceService.resolve_number(number):
                result.warnings.append(
                    f"Escalation code {number} does not match a catalogue code "
                    "(fine if it is external)."
                )
        else:
            current = StatusCodeService._repo.get_current_revision(existing.id)
            result.identifier = existing.status_code_identifier
            if current is not None and _unchanged(current, data):
                result.action = "skip"
            elif current is None:
                result.issues.append(
                    Issue(
                        "legacy_reference_number",
                        legacy,
                        "The change request of this code was withdrawn; the code still holds its "
                        "number.",
                        "An Administrator can delete it under Administration, Withdrawn Codes.",
                    )
                )
            elif current.lifecycle_status in ("REVIEW", "PENDING_APPROVAL"):
                result.issues.append(
                    Issue(
                        "legacy_reference_number",
                        legacy,
                        "The code is in review right now and cannot take a new revision.",
                        "Wait for the decision or withdraw the change request.",
                    )
                )
            elif current.lifecycle_status in ("DEPRECATED", "ARCHIVED"):
                result.issues.append(
                    Issue(
                        "legacy_reference_number",
                        legacy,
                        f"The code is {current.lifecycle_status.title()} and cannot be revised.",
                    )
                )
            else:
                result.action = "update"
        return result, data, existing

    # ------------------------------------------------------------------ dry run
    @staticmethod
    def dry_run(filename: str, content: bytes, actor, mode: str = "CREATE") -> dict:
        """Validate every row and report what an import would do. Writes nothing."""
        require_roles(actor, "ADMINISTRATOR", "ENGINEER")
        mode = ImportService._mode(mode)
        _ext, source_format, rows = _parse_upload(filename, content)
        seen: set[tuple[str, int]] = set()
        results = []
        for index, row in enumerate(rows, start=2):  # header is row 1
            result, _data, _existing = ImportService._evaluate(row, index, mode, seen)
            results.append(result)
        db.session.rollback()
        counts = {"create": 0, "update": 0, "skip": 0, "error": 0}
        for r in results:
            counts["error" if r.issues else r.action] += 1
        return {
            "mode": mode,
            "source_format": source_format,
            "row_count": len(rows),
            "would_create": counts["create"],
            "would_update": counts["update"],
            "unchanged": counts["skip"],
            "error_count": counts["error"],
            "warning_count": sum(len(r.warnings) for r in results),
            "ok": counts["error"] == 0,
            "rows": [r.as_dict() for r in results],
        }

    @staticmethod
    def _mode(mode: str | None) -> str:
        mode = (mode or "CREATE").upper()
        if mode not in ("CREATE", "UPDATE"):
            raise ValueError("mode must be CREATE or UPDATE")
        return mode

    # ------------------------------------------------------------------ real import
    @staticmethod
    def process_upload(
        filename: str,
        content: bytes,
        actor,
        mode: str = "CREATE",
        asynchronous: bool | None = None,
    ) -> ImportJob:
        require_roles(actor, "ADMINISTRATOR", "ENGINEER")
        mode = ImportService._mode(mode)
        extension, source_format, rows = _parse_upload(filename, content)

        now = utcnow_iso()
        job = ImportJob(
            requested_by=actor.id,
            source_format=source_format,
            source_file_reference="",
            row_count=len(rows),
            status="PENDING",
            import_mode=mode,
            created_at=now,
        )
        db.session.add(job)
        db.session.commit()  # durable before per-row processing, see module docstring

        import_dir = Path(current_app.instance_path) / "imports" / str(job.id)
        import_dir.mkdir(parents=True, exist_ok=True)
        source_path = import_dir / f"source.{extension}"
        source_path.write_bytes(content)
        job.source_file_reference = str(source_path)
        AuditService.log(
            "ImportJob",
            job.id,
            "IMPORT_STARTED",
            actor=actor,
            after={"source_format": source_format, "row_count": len(rows), "mode": mode},
        )
        db.session.commit()

        threshold = current_app.config.get("IMPORT_ASYNC_ROW_THRESHOLD", 300)
        run_async = asynchronous if asynchronous is not None else len(rows) > threshold
        if not run_async:
            return ImportService._process_rows(job.id, rows, actor, mode)

        if current_app.config.get("IMPORT_ASYNC_INLINE"):
            return ImportService._process_rows(job.id, rows, actor, mode)

        app = current_app._get_current_object()  # type: ignore[attr-defined]
        actor_id = actor.id

        def worker() -> None:
            with app.app_context():
                user = db.session.get(User, actor_id)
                from app.auth.providers import AuthenticatedUser

                if user is None:
                    return
                try:
                    ImportService._process_rows(
                        job.id, rows, AuthenticatedUser.from_model(user), mode
                    )
                except Exception:  # noqa: BLE001  (the job row already records FAILED)
                    current_app.logger.exception("import job %s failed", job.id)
                finally:
                    db.session.remove()

        threading.Thread(target=worker, name=f"import-{job.id}", daemon=True).start()
        return job

    @staticmethod
    def _load_job(job_id: int) -> ImportJob:
        job = db.session.get(ImportJob, job_id)
        if job is None:
            raise NotFoundError("Import job not found")
        return job

    @staticmethod
    def _process_rows(job_id: int, rows: list[dict], actor, mode: str) -> ImportJob:
        job = ImportService._load_job(job_id)
        job.status = "VALIDATING"
        db.session.commit()

        results: list[RowResult] = []
        created = updated = unchanged = 0
        seen: set[tuple[str, int]] = set()
        for index, row in enumerate(rows, start=2):  # header is row 1
            try:
                result, data, existing = ImportService._evaluate(row, index, mode, seen)
                if not result.issues and data is not None:
                    created_inc, updated_inc, unchanged_inc = ImportService._apply(
                        result, data, existing, job, actor
                    )
                    created += created_inc
                    updated += updated_inc
                    unchanged += unchanged_inc
            except (ValidationFailed, ValueError, DomainError) as exc:
                # A failure partway through _build_revision (e.g. an invalid turbine
                # platform code, resolved only after the StatusCode/revision rows were
                # already added to the session) can leave uncommitted state pending; roll
                # it back so it never leaks into the next row's transaction.
                db.session.rollback()
                result = RowResult(row=index)
                if isinstance(exc, ValidationFailed):
                    result.issues = [
                        Issue(e["field"], row.get(e["field"], ""), e["message"])
                        for e in exc.field_errors
                    ]
                else:
                    result.issues = [Issue("", "", str(exc))]
            except Exception:
                # Unexpected failure: the job is recorded as FAILED (never
                # silently left VALIDATING) and the error still surfaces.
                db.session.rollback()
                job = ImportService._load_job(job_id)
                job.status = "FAILED"
                job.created_count = created + updated
                job.error_count = sum(1 for r in results if r.issues)
                job.completed_at = utcnow_iso()
                AuditService.log(
                    "ImportJob",
                    job.id,
                    "IMPORT_FAILED",
                    actor=actor,
                    after={"created_count": created + updated, "failed_at_row": index},
                )
                db.session.commit()
                raise
            results.append(result)
            if index % 10 == 0 or index == len(rows) + 1:
                job = ImportService._load_job(job_id)
                job.processed_count = len(results)
                db.session.commit()

        job = ImportService._load_job(job_id)
        errors = [r for r in results if r.issues]
        job.created_count = created + updated
        job.error_count = len(errors)
        job.warning_count = sum(len(r.warnings) for r in results)
        job.processed_count = len(results)
        job.status = "COMPLETE"
        job.completed_at = utcnow_iso()

        if errors:
            import_dir = Path(job.source_file_reference).parent
            ImportService._write_error_reports(import_dir, errors, job)

        AuditService.log(
            "ImportJob",
            job.id,
            "IMPORT_COMPLETED",
            actor=actor,
            after={
                "row_count": job.row_count,
                "created_count": created,
                "updated_count": updated,
                "unchanged_count": unchanged,
                "error_count": len(errors),
                "warning_count": job.warning_count,
                "mode": mode,
            },
        )
        db.session.commit()
        return job

    @staticmethod
    def _apply(
        result: RowResult, data: dict, existing: StatusCode | None, job: ImportJob, actor
    ) -> tuple[int, int, int]:
        """Carry out one validated row; returns (created, updated, unchanged)."""
        if result.action == "skip":
            return 0, 0, 1
        if result.action == "create":
            revision = StatusCodeService.create_draft(data, actor, import_job_id=job.id)
            result.warnings = [
                w["message"]
                for w in StatusCodeService.warnings_for(revision)
                if w["type"] in ("POSSIBLE_DUPLICATE", "UNKNOWN_REFERENCE", "SELF_REFERENCE")
                or w["type"].endswith("_REFERENCE")
            ]
            return 1, 0, 0

        # update: revise the already-imported code
        if existing is None:
            raise DomainError("Update mode needs the existing code.")
        current = StatusCodeService._repo.get_current_revision(existing.id)
        if current is None:
            raise DomainError("The existing code has no current revision.")
        if current.lifecycle_status == "DRAFT":
            # The still-open Draft is updated in place (its author or an Administrator only;
            # anything else comes back as a DomainError and is reported on the row).
            StatusCodeService.update_draft(current.id, data, actor)
            revision = current
        else:
            revision = StatusCodeService.create_revision(existing.id, data, actor)
            cr = (
                db.session.query(ChangeRequest).filter_by(status_code_revision_id=revision.id).one()
            )
            cr.import_job_id = job.id
            db.session.commit()
        result.identifier = existing.status_code_identifier
        result.warnings = [
            w["message"]
            for w in StatusCodeService.warnings_for(revision)
            if w["type"].endswith("_REFERENCE")
        ]
        return 0, 1, 0

    # ------------------------------------------------------------------ error reports
    @staticmethod
    def _write_error_reports(import_dir: Path, errors: list[RowResult], job: ImportJob) -> None:
        lines = [
            (r.row, i.column, "" if i.value is None else str(i.value), i.message, i.hint)
            for r in errors
            for i in (r.issues or [Issue("", "", "")])
        ]
        csv_path = import_dir / "errors.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["row", "column", "value", "error", "how_to_fix"])
            for row, column, value, message, hint in lines:
                writer.writerow([row, column, _safe_cell(value), message, hint])
        job.error_report_reference = str(csv_path)

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Errors"
        sheet.append(["Row", "Column", "Value", "Problem", "How to fix"])
        for row, column, value, message, hint in lines:
            sheet.append([row, column, _safe_cell(value), message, hint])
        for column_letter, width in zip("ABCDE", (7, 28, 30, 70, 60), strict=True):
            sheet.column_dimensions[column_letter].width = width
        sheet.freeze_panes = "A2"
        xlsx_path = import_dir / "errors.xlsx"
        workbook.save(xlsx_path)
        job.error_report_xlsx_reference = str(xlsx_path)

    # ------------------------------------------------------------------ queries
    @staticmethod
    def list_jobs() -> list[ImportJob]:
        return db.session.query(ImportJob).order_by(ImportJob.id.desc()).all()

    @staticmethod
    def get(job_id: int) -> ImportJob | None:
        return db.session.get(ImportJob, job_id)

    # ------------------------------------------------------------------ reconciliation
    @staticmethod
    def reconciliation(
        expected_legacy_references: list[str] | None = None, expected_total: int | None = None
    ) -> dict:
        """I-05d: where the legacy library stands. `expected_legacy_references` (a master
        list of legacy numbers) makes the "still missing" part concrete; with only
        `expected_total` it is a count."""
        rows = (
            db.session.query(StatusCode, StatusCodeRevision)
            .join(
                StatusCodeRevision,
                (StatusCodeRevision.status_code_id == StatusCode.id)
                & (StatusCodeRevision.is_current == 1),
            )
            .filter(StatusCode.legacy_reference_number.isnot(None), StatusCode.is_sandbox == 0)
            .all()
        )
        buckets = {
            "DRAFT": "imported_draft",
            "REVIEW": "in_review",
            "PENDING_APPROVAL": "in_review",
            "APPROVED": "approved",
            "RELEASED": "released",
            "DEPRECATED": "retired",
            "ARCHIVED": "retired",
        }
        counts = {name: 0 for name in set(buckets.values())}
        present: set[str] = set()
        for code, revision in rows:
            counts[buckets[revision.lifecycle_status]] += 1
            present.add(code.legacy_reference_number)  # type: ignore[arg-type]
        result: dict = {
            "imported_total": len(rows),
            "by_state": counts,
        }
        if expected_legacy_references is not None:
            expected = {e.strip() for e in expected_legacy_references if e and e.strip()}
            missing = sorted(expected - present, key=lambda v: (len(v), v))
            result.update(
                expected_total=len(expected),
                missing_count=len(missing),
                missing=missing[:500],
                unexpected_count=len(present - expected),
                percent_imported=(
                    round(100 * len(expected & present) / len(expected), 1) if expected else None
                ),
            )
        elif expected_total:
            result.update(
                expected_total=expected_total,
                missing_count=max(0, expected_total - len(rows)),
                percent_imported=round(100 * min(len(rows), expected_total) / expected_total, 1),
            )
        result["jobs"] = [
            {
                "id": j.id,
                "mode": j.import_mode,
                "status": j.status,
                "rows": j.row_count,
                "imported": j.created_count,
                "errors": j.error_count,
                "created_at": j.created_at,
            }
            for j in db.session.query(ImportJob).order_by(ImportJob.id.desc()).limit(20)
        ]
        return result


def _safe_cell(value: str) -> str:
    return "'" + value if value.startswith(("=", "+", "-", "@")) else value

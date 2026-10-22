"""Library Import (EPIC-14, new 2026-09-17). See docs/06-data-dictionary.md
§5, docs/05-governance-handbook.md §6b, docs/09-api-specification.md §6b.

Every row that passes validation becomes an ordinary Draft
StatusCode/StatusCodeRevision/ChangeRequest (cr_type=IMPORT) -- a faster
data-entry path, never a governance bypass: it still needs Cross-Domain
Sign-Off, both Review sign-offs, and Chief Engineer approval before Release,
identical to a hand-typed code (FR-048c).

Processed synchronously within the upload request: this on-premises
deployment (docs/14-deployment-architecture.md) has no background task
queue, and NFR-001's sizing (low tens of thousands of revisions over the
system's MVP lifetime) keeps even a full-library import well within a
single request's timeout. The ImportJob status/polling API contract is
still exactly what docs/artifacts/openapi.yaml describes, so a real async
worker could be swapped in later without changing the client-facing shape.

CSV/XLSX column headers are the same field names StatusCodeCreate uses,
except Functional System Group/Subgroup and the eight audience-access
fields are given as their lookup **codes** (e.g. "WCNV", "Converter",
"SCADA User") rather than surrogate ids -- a legacy spreadsheet has no way
to know CSCM Tool's internal ids. Where a code is ambiguous (WTUR/WROT are
each reused for a second, numerically distinct Hub Controller group -- see
app/services/lookup_service.py), the row must also supply
`functional_system_group_range_start` to disambiguate."""

import csv
import io
from pathlib import Path
from typing import Any

from flask import current_app
from openpyxl import load_workbook

from app.domain.authz import require_roles
from app.domain.errors import DomainError
from app.extensions import db
from app.models.import_job import ImportJob
from app.models.lookup import (
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
)
from app.services.audit_service import AuditService
from app.services.status_code_service import StatusCodeService, ValidationFailed
from app.services.validation import validate_revision_fields
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

_TRUE_VALUES = {"1", "true", "yes", "y"}


class ImportValidationError(DomainError):
    """One row's worth of field errors, raised internally and caught per
    row -- never surfaced to the HTTP layer directly (see process_upload)."""

    def __init__(self, messages: list[str]):
        super().__init__("; ".join(messages))
        self.messages = messages


def _parse_bool(value: Any) -> bool:
    return str(value).strip().lower() in _TRUE_VALUES if value not in (None, "") else False


def _parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError) as exc:
        raise ImportValidationError([f"'{value}' is not a valid number"]) from exc


def _resolve_group(code: str, range_start_hint: Any) -> LookupFunctionalSystemGroup:
    matches = (
        db.session.query(LookupFunctionalSystemGroup)
        .filter(
            LookupFunctionalSystemGroup.code == code, LookupFunctionalSystemGroup.is_active == 1
        )
        .all()
    )
    if not matches:
        raise ImportValidationError([f"Unknown functional_system_group code: {code}"])
    if len(matches) == 1:
        return matches[0]
    if range_start_hint in (None, ""):
        ranges = ", ".join(f"{m.range_start}-{m.range_end}" for m in matches)
        raise ImportValidationError(
            [
                f"functional_system_group '{code}' is ambiguous (ranges: {ranges}); "
                "supply functional_system_group_range_start to disambiguate"
            ]
        )
    hint = _parse_int(range_start_hint)
    for m in matches:
        if m.range_start == hint:
            return m
    raise ImportValidationError([f"No functional_system_group '{code}' with range_start {hint}"])


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
        raise ImportValidationError(
            [f"Unknown functional_subgroup '{code}' within Functional System Group '{group.code}'"]
        )
    return subgroup


def _resolve_access(field: str, code: str | None) -> int | None:
    if not code:
        return None
    model = _ACCESS_FIELD_MODELS[field]
    value = db.session.query(model).filter(model.code == code, model.is_active == 1).first()  # type: ignore[attr-defined]
    if value is None:
        raise ImportValidationError([f"Unknown {field} code: {code}"])
    return value.id  # type: ignore[attr-defined]


def _row_to_data(row: dict) -> dict:
    """Resolves lookup codes to the surrogate-id-based dict shape
    StatusCodeService._build_revision expects (see module docstring)."""
    group = _resolve_group(
        (row.get("functional_system_group") or "").strip(),
        row.get("functional_system_group_range_start"),
    )
    subgroup = _resolve_subgroup(group, (row.get("functional_subgroup") or "").strip())

    platforms_raw = row.get("turbine_platforms") or ""
    turbine_platforms = [p.strip() for p in platforms_raw.replace(";", ",").split(",") if p.strip()]

    data: dict[str, Any] = {
        "functional_system_group": group.id,
        "functional_subgroup": subgroup.id,
        "turbine_platforms": turbine_platforms,
        "title": (row.get("title") or "").strip(),
        "description": (row.get("description") or "").strip(),
        "software_version": (row.get("software_version") or "").strip() or None,
        "status_category": (row.get("status_category") or "").strip().upper(),
        "available_group": _parse_int(row.get("available_group")),
        "alarm_flag": _parse_bool(row.get("alarm_flag")),
        "set_delay": (row.get("set_delay") or "").strip(),
        "reset_delay": (row.get("reset_delay") or "").strip(),
        "up_down_counter": _parse_bool(row.get("up_down_counter")),
        "trigger_snapshot": _parse_bool(row.get("trigger_snapshot")),
        "loadless_spinning_permitted": _parse_bool(row.get("loadless_spinning_permitted")),
        "number_of_times_repeated": _parse_int(row.get("number_of_times_repeated")),
        "repeated_over_the_course": (row.get("repeated_over_the_course") or "").strip() or None,
        "status_code_for_repeated_error": _parse_int(row.get("status_code_for_repeated_error")),
        "legacy_reference_number": (row.get("legacy_reference_number") or "").strip() or None,
    }
    for field in _PROGRAM_FIELDS:
        data[field] = _parse_int(row.get(field)) or 0
    for field in _ACCESS_FIELD_MODELS:
        data[field] = _resolve_access(field, (row.get(field) or "").strip() or None)

    field_errors = validate_revision_fields(data)
    if field_errors:
        raise ImportValidationError([f"{e['field']}: {e['message']}" for e in field_errors])
    return data


def _read_csv_rows(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _read_xlsx_rows(content: bytes) -> list[dict]:
    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    sheet = workbook.active
    rows_iter = sheet.iter_rows(values_only=True)
    headers = [str(h).strip() if h is not None else "" for h in next(rows_iter, [])]
    rows = []
    for raw_row in rows_iter:
        if all(cell is None for cell in raw_row):
            continue
        rows.append({headers[i]: raw_row[i] for i in range(len(headers)) if i < len(raw_row)})
    return rows


class ImportService:
    @staticmethod
    def process_upload(filename: str, content: bytes, actor) -> ImportJob:
        require_roles(actor, "ADMINISTRATOR", "ENGINEER")
        extension = (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()
        source_format = ALLOWED_EXTENSIONS.get(extension)
        if source_format is None:
            raise ValueError("Only .csv and .xlsx files are accepted.")

        rows = _read_csv_rows(content) if source_format == "CSV" else _read_xlsx_rows(content)

        now = utcnow_iso()
        job = ImportJob(
            requested_by=actor.id,
            source_format=source_format,
            source_file_reference="",
            row_count=len(rows),
            status="VALIDATING",
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
            after={"source_format": source_format, "row_count": len(rows)},
        )
        db.session.commit()

        errors: list[tuple[int, str]] = []
        created_count = 0
        for index, row in enumerate(rows, start=2):  # header is row 1
            try:
                data = _row_to_data(row)
                StatusCodeService.create_draft(data, actor, import_job_id=job.id)
            except (ImportValidationError, ValidationFailed, ValueError) as exc:
                # A failure partway through _build_revision (e.g. an invalid
                # turbine platform code, resolved only after the StatusCode/
                # revision rows were already added to the session) can leave
                # uncommitted state pending; roll it back so it never leaks
                # into the next row's transaction. `job` is already committed
                # above, so this never touches it.
                db.session.rollback()
                message = (
                    "; ".join(exc.messages) if isinstance(exc, ImportValidationError) else str(exc)
                )
                errors.append((index, message))
            except Exception:
                # Unexpected failure: the job is recorded as FAILED (never
                # silently left VALIDATING) and the error still surfaces.
                db.session.rollback()
                job.status = "FAILED"
                job.created_count = created_count
                job.error_count = len(errors)
                job.completed_at = utcnow_iso()
                AuditService.log(
                    "ImportJob",
                    job.id,
                    "IMPORT_FAILED",
                    actor=actor,
                    after={"created_count": created_count, "failed_at_row": index},
                )
                db.session.commit()
                raise
            else:
                created_count += 1

        job.created_count = created_count
        job.error_count = len(errors)
        job.status = "COMPLETE"
        job.completed_at = utcnow_iso()

        if errors:
            error_path = import_dir / "errors.csv"
            with error_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["row", "error"])
                writer.writerows(errors)
            job.error_report_reference = str(error_path)

        AuditService.log(
            "ImportJob",
            job.id,
            "IMPORT_COMPLETED",
            actor=actor,
            after={
                "row_count": job.row_count,
                "created_count": created_count,
                "error_count": len(errors),
            },
        )
        db.session.commit()
        return job

    @staticmethod
    def list_jobs() -> list[ImportJob]:
        return db.session.query(ImportJob).order_by(ImportJob.id.desc()).all()

    @staticmethod
    def get(job_id: int) -> ImportJob | None:
        return db.session.get(ImportJob, job_id)

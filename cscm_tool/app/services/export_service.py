"""Catalogue (CSV/JSON/PDF) and full-database export. FR-045-FR-047, SEC-015."""

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime

from app.domain.authz import require_roles
from app.export.csv_exporter import build_csv
from app.export.full_database_exporter import export_full_database_bytes
from app.export.json_exporter import build_json
from app.export.pdf_exporter import build_pdf
from app.export.xlsx_exporter import build_xlsx
from app.extensions import db
from app.models.export_job import ExportJob
from app.models.status_code import StatusCodeRevision
from app.repositories.status_code_repository import StatusCodeRepository
from app.services.audit_service import AuditService
from app.utils import utcnow_iso

_BUILDERS: dict[str, tuple[Callable[[list[dict]], bytes], str]] = {
    "csv": (build_csv, "text/csv"),
    "json": (build_json, "application/json"),
    "xlsx": (build_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "pdf": (build_pdf, "application/pdf"),
}


def _access_code(lookup) -> str | None:
    return lookup.code if lookup is not None else None


def flatten_revision(revision: StatusCodeRevision) -> dict:
    """Builds an export row directly from the ORM object rather than
    reusing app.api.v1.serializers.revision_payload: the service layer
    must not depend on the presentation layer
    (docs/18-claude-code-implementation-guide.md §1 layering). v3
    (docs/06-data-dictionary.md §11): every export format, including JSON,
    is a flat table — one row per Status Code Revision with every field as
    a column, mirroring the legacy tool's grid layout."""
    status_code = revision.status_code
    return {
        "status_code_identifier": status_code.status_code_identifier,
        "functional_system_group": status_code.functional_system_group.code,
        "functional_subgroup": status_code.functional_subgroup.code,
        "legacy_reference_number": status_code.legacy_reference_number,
        "turbine_platforms": ", ".join(sorted(p.turbine_platform.code for p in revision.platforms)),
        "revision_number": revision.revision_number,
        "title": revision.title,
        "description": revision.description,
        "software_version": revision.software_version,
        "status_category": revision.status_category,
        "available_group": revision.available_group,
        "alarm_flag": bool(revision.alarm_flag),
        "set_delay": revision.set_delay,
        "reset_delay": revision.reset_delay,
        "up_down_counter": bool(revision.up_down_counter),
        "trigger_snapshot": bool(revision.trigger_snapshot),
        "loadless_spinning_permitted": bool(revision.loadless_spinning_permitted),
        "number_of_times_repeated": revision.number_of_times_repeated,
        "repeated_over_the_course": revision.repeated_over_the_course,
        "status_code_for_repeated_error": revision.status_code_for_repeated_error,
        "yaw_program": revision.yaw_program,
        "manual_reset_program": revision.manual_reset_program,
        "auto_reset_program": revision.auto_reset_program,
        "converter_reactive_power_program": revision.converter_reactive_power_program,
        "brake_program": revision.brake_program,
        "umrichterprogramm_gsc": revision.umrichterprogramm_gsc,
        "umrichterprogramm_msc": revision.umrichterprogramm_msc,
        "yaw_bearing_lubrication_program": revision.yaw_bearing_lubrication_program,
        "development_access": _access_code(revision.development_access),
        "sales_access": _access_code(revision.sales_access),
        "tcc_access": _access_code(revision.tcc_access),
        "service_access": _access_code(revision.service_access),
        "turbine_operator_package_access": _access_code(revision.turbine_operator_package_access),
        "grid_operator_access": _access_code(revision.grid_operator_access),
        "service_partner_access": _access_code(revision.service_partner_access),
        "customer_access": _access_code(revision.customer_access),
        "logical_node": status_code.functional_system_group.code,
        "node_value": status_code.functional_system_group.sort_order,
        "lifecycle_status": revision.lifecycle_status,
        "effective_date": revision.effective_date,
    }


def export_filename(kind: str, extension: str, label: str | None = None) -> str:
    """cscm_<kind>[_<label>]_YYYY-MM-DD_HH-MM.<ext> — the generation time (UTC, the
    same clock as the audit log) is part of every export's file name so
    successive exports never overwrite or get confused with one another."""
    stamp = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M")
    safe_label = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-") if label else ""
    parts = ["cscm", kind] + ([safe_label] if safe_label else []) + [stamp]
    return "_".join(parts) + f".{extension}"


class ExportService:
    _repo = StatusCodeRepository()

    @staticmethod
    def export_catalogue(
        revisions: list[StatusCodeRevision],
        export_format: str,
        actor,
        release_id: int | None = None,
        scope: dict | None = None,
        notice: str | None = None,
        name_label: str | None = None,
    ) -> tuple[bytes, str, str]:
        """`notice` (FR-046) marks the output as not for distribution: it is
        added as a column on every row of every format (the exports stay flat
        tables) plus a banner on the PDF and a filename suffix."""
        builder = _BUILDERS.get(export_format)
        if builder is None:
            raise ValueError(f"Unsupported export format: {export_format}")
        build_fn, mimetype = builder

        rows = [flatten_revision(r) for r in revisions]
        if notice:
            rows = [{**row, "distribution_notice": notice} for row in rows]
        content = build_pdf(rows, notice=notice) if export_format == "pdf" else build_fn(rows)

        job = ExportJob(
            requested_by=actor.id,
            export_type=export_format.upper(),
            export_scope_type="CATALOGUE",
            scope=json.dumps(
                scope if scope is not None else ({"release_id": release_id} if release_id else {})
            ),
            release_id=release_id,
            status="COMPLETE",
            created_at=utcnow_iso(),
            completed_at=utcnow_iso(),
        )
        db.session.add(job)
        db.session.flush()
        AuditService.log(
            "ExportJob",
            job.id,
            "CATALOGUE_EXPORT",
            actor=actor,
            after={
                "format": export_format,
                "release_id": release_id,
                "row_count": len(rows),
                "scope": scope,
            },
        )
        db.session.commit()
        if notice:
            kind = "working-set_NOT_FOR_DISTRIBUTION"
        else:
            kind = "release" if release_id else "released"
        return content, mimetype, export_filename(kind, export_format, name_label)

    @staticmethod
    def released_revisions(**filters) -> list[StatusCodeRevision]:
        """FR-045: the latest Released revision of every non-sandbox code,
        optionally narrowed by group/subgroup/platform (a Release-independent
        view of "everything currently Released")."""
        revisions = ExportService._repo.list_latest_released(**filters)
        return revisions

    @staticmethod
    def working_set_revisions(actor, **filters) -> list[StatusCodeRevision]:
        """FR-046: ad-hoc filtered working set, any lifecycle state, still
        excluding sandbox codes (FR-054). Never available to Viewers (BR-009)."""
        require_roles(actor, "ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")
        return ExportService._repo.search_current_revisions(
            page=1, page_size=100000, eager=True, **filters
        )[0]

    @staticmethod
    def export_full_database(actor) -> tuple[bytes, str, str]:
        """SEC-015: authorization is enforced by the route decorator, not here."""
        require_roles(actor, "ADMINISTRATOR")
        content = export_full_database_bytes()

        job = ExportJob(
            requested_by=actor.id,
            export_type="SQLITE_BACKUP",
            export_scope_type="FULL_DATABASE",
            status="COMPLETE",
            created_at=utcnow_iso(),
            completed_at=utcnow_iso(),
        )
        db.session.add(job)
        db.session.flush()
        AuditService.log(
            "ExportJob",
            job.id,
            "FULL_DATABASE_EXPORT",
            actor=actor,
            after={"size_bytes": len(content)},
        )
        db.session.commit()
        return content, "application/octet-stream", export_filename("full-database-backup", "db")

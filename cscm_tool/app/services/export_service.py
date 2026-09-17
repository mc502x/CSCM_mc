"""Catalogue (CSV/JSON/PDF) and full-database export. FR-045-FR-047, SEC-015."""

import json

from app.export.csv_exporter import build_csv
from app.export.full_database_exporter import export_full_database_bytes
from app.export.json_exporter import build_json
from app.export.pdf_exporter import build_pdf
from app.extensions import db
from app.models.export_job import ExportJob
from app.models.status_code import StatusCodeRevision
from app.services.audit_service import AuditService
from app.utils import utcnow_iso

_BUILDERS = {
    "csv": (build_csv, "text/csv"),
    "json": (build_json, "application/json"),
    "pdf": (build_pdf, "application/pdf"),
}


def _flatten(revision: StatusCodeRevision) -> dict:
    """Builds an export row directly from the ORM object rather than
    reusing app.api.v1.serializers.revision_payload: the service layer
    must not depend on the presentation layer
    (docs/18-claude-code-implementation-guide.md §1 layering), and export
    rows are flattened for CSV/PDF (turbine_platforms joined to a string)
    rather than nested like the JSON API response."""
    status_code = revision.status_code
    return {
        "status_code_identifier": status_code.status_code_identifier,
        "functional_system_group": status_code.functional_system_group.code,
        "functional_subgroup": (
            status_code.functional_subgroup.code if status_code.functional_subgroup else None
        ),
        "turbine_platforms": ", ".join(sorted(p.turbine_platform.code for p in revision.platforms)),
        "revision_number": revision.revision_number,
        "title": revision.title,
        "description": revision.description,
        "status_category": revision.status_category.code,
        "availability_group": revision.availability_group.code,
        "brake_program": revision.brake_program.code,
        "reset_program": revision.reset_program.code,
        "software_version": revision.software_version,
        "operational_state": revision.operational_state.code,
        "access_rights": revision.access_rights.code,
        "alarm_behaviour": revision.alarm_behaviour.code,
        "lifecycle_status": revision.lifecycle_status,
        "effective_date": revision.effective_date,
    }


class ExportService:
    @staticmethod
    def export_catalogue(
        revisions: list[StatusCodeRevision],
        export_format: str,
        actor,
        release_id: int | None = None,
    ) -> tuple[bytes, str, str]:
        builder = _BUILDERS.get(export_format)
        if builder is None:
            raise ValueError(f"Unsupported export format: {export_format}")
        build_fn, mimetype = builder

        rows = [_flatten(r) for r in revisions]
        content = build_fn(rows)

        job = ExportJob(
            requested_by=actor.id,
            export_type=export_format.upper(),
            export_scope_type="CATALOGUE",
            scope=json.dumps({"release_id": release_id} if release_id else {}),
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
            after={"format": export_format, "release_id": release_id, "row_count": len(rows)},
        )
        db.session.commit()
        return content, mimetype, f"cscm_export.{export_format}"

    @staticmethod
    def export_full_database(actor) -> tuple[bytes, str, str]:
        """SEC-015: authorization is enforced by the route decorator, not here."""
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
        return content, "application/octet-stream", "cscm_full_database_backup.db"

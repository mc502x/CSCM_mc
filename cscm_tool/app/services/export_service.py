"""Catalogue (CSV/JSON/XLSX/PDF) and full-database export. FR-045-FR-047, SEC-015.

v4 (docs/21-improvement-ideas.md): an export can be shaped by an export profile (I-02), an
audience (I-03), a language (I-15) and a controller software version (I-07), is described
by a manifest with SHA-256 hashes (I-06) and can ship as a ZIP bundle with that manifest."""

import io
import json
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.domain.authz import require_roles
from app.export.csv_exporter import build_csv
from app.export.full_database_exporter import export_full_database_bytes
from app.export.json_exporter import build_json
from app.export.pdf_exporter import build_pdf
from app.export.xlsx_exporter import build_xlsx
from app.extensions import db
from app.models.export_job import ExportJob, ExportProfile
from app.models.release import Release
from app.models.status_code import StatusCodeRevision
from app.repositories.status_code_repository import StatusCodeRepository
from app.services import manifest_service
from app.services.audience_service import AUDIENCES, AudienceService, validate_audience
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.export_profile_service import parse_columns
from app.services.software_version_service import SoftwareVersionService
from app.services.translation_service import TranslationService, source_language
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
        # v4 (docs/21-improvement-ideas.md): I-14, I-07, I-27, I-25
        "remedy_text": revision.remedy_text,
        "affected_component": revision.affected_component,
        "related_status_codes": revision.related_status_codes,
        "standard_references": revision.standard_references,
        "applies_from_version": (
            revision.applies_from_version.code if revision.applies_from_version else None
        ),
        "applies_to_version": (
            revision.applies_to_version.code if revision.applies_to_version else None
        ),
        "planned_effective_date": revision.planned_effective_date,
        "planned_deprecation_date": revision.planned_deprecation_date,
    }


def export_filename(kind: str, extension: str, label: str | None = None) -> str:
    """cscm_<kind>[_<label>]_YYYY-MM-DD_HH-MM.<ext> — the generation time (UTC, the
    same clock as the audit log) is part of every export's file name so
    successive exports never overwrite or get confused with one another."""
    stamp = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M")
    safe_label = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-") if label else ""
    parts = ["cscm", kind] + ([safe_label] if safe_label else []) + [stamp]
    return "_".join(parts) + f".{extension}"


@dataclass
class ExportOptions:
    """What shapes an export besides the revisions themselves."""

    profile: ExportProfile | None = None
    audience: str | None = None
    language: str | None = None
    strict_language: bool = False
    software_version: str | None = None
    bundle: bool = False
    extra_files: dict[str, bytes] = field(default_factory=dict)


@dataclass
class ExportResult:
    """Iterates as (content, mimetype, filename) so existing callers can unpack it."""

    content: bytes
    mimetype: str
    filename: str
    sha256: str  # of the data file (inside the ZIP when bundled)
    manifest: dict
    job_id: int | None = None

    def __iter__(self):
        return iter((self.content, self.mimetype, self.filename))


class ExportService:
    _repo = StatusCodeRepository()

    @staticmethod
    def _prepare(
        revisions: list[StatusCodeRevision], options: ExportOptions, notice: str | None
    ) -> tuple[list[dict], list[tuple[str, str]] | None]:
        """Applies version/audience/language/profile to `revisions`; returns the flat rows
        and, with a profile, the ordered (field, label) columns."""
        profile = options.profile
        audience = validate_audience(options.audience or (profile.audience if profile else None))
        language = options.language or (profile.language_code if profile else None)
        options.audience = audience
        options.language = language

        if options.software_version:
            version = SoftwareVersionService.get_by_code(options.software_version)
            revisions = [r for r in revisions if SoftwareVersionService.applies(r, version)]
        if audience:
            revisions = AudienceService.filter_revisions(revisions, audience)

        translations: dict = {}
        use_language = bool(language) and language != source_language().code
        if use_language:
            if language is None:
                raise ValueError("language is required for a translated export")
            translations = TranslationService.approved_for([r.id for r in revisions], language)
            if options.strict_language:
                revisions = [r for r in revisions if r.id in translations]

        rows = []
        for revision in revisions:
            row = flatten_revision(revision)
            if use_language:
                translated = translations.get(revision.id)
                if translated is not None:
                    row["title"] = translated.title
                    row["description"] = translated.description
                    if translated.remedy_text:
                        row["remedy_text"] = translated.remedy_text
                row["content_language"] = (
                    language if translated is not None else source_language().code
                )
            if audience:
                row = AudienceService.scope_row(row, revision, audience)
            if notice:
                row["distribution_notice"] = notice
            rows.append(row)

        columns = None
        if profile is not None:
            columns = [(c["field"], c["label"]) for c in parse_columns(profile.columns)]
            if notice and all(f != "distribution_notice" for f, _ in columns):
                columns.append(("distribution_notice", "Distribution notice"))
        return rows, columns

    @staticmethod
    def _render(
        export_format: str,
        rows: list[dict],
        columns: list[tuple[str, str]] | None,
        notice: str | None,
        title: dict | None,
        orientation: str,
        language: str | None = None,
    ) -> bytes:
        if export_format == "pdf":
            return build_pdf(
                rows,
                notice=notice,
                columns=columns,
                title=title,
                orientation=orientation,
                language=language,
            )
        build_fn = _BUILDERS[export_format][0]
        if columns is None:
            return build_fn(rows)
        if export_format == "json":  # machine consumers keep the stable field names
            return build_fn([{field: row.get(field) for field, _ in columns} for row in rows])
        return build_fn([{label: row.get(field) for field, label in columns} for row in rows])

    @staticmethod
    def export_catalogue(
        revisions: list[StatusCodeRevision],
        export_format: str,
        actor,
        release_id: int | None = None,
        scope: dict | None = None,
        notice: str | None = None,
        name_label: str | None = None,
        options: ExportOptions | None = None,
    ) -> ExportResult:
        """`notice` (FR-046) marks the output as not for distribution: it is
        added as a column on every row of every format (the exports stay flat
        tables) plus a banner on the PDF and a filename suffix."""
        builder = _BUILDERS.get(export_format)
        if builder is None:
            raise ValueError(f"Unsupported export format: {export_format}")
        mimetype = builder[1]
        options = options or ExportOptions()
        if notice and options.audience:
            raise ValueError(
                "An audience export is built from Released data only; it cannot be combined "
                "with the unapproved working set."
            )

        rows, columns = ExportService._prepare(revisions, options, notice)
        digest = manifest_service.content_digest(rows)
        release = db.session.get(Release, release_id) if release_id else None
        profile = options.profile
        generated_at = utcnow_iso()

        title = None
        if release is not None or (profile is not None and profile.title_page):
            title = {
                "heading": profile.name if profile else "Status code catalogue",
                "subtitle": f"{release.name} - {release.version_label}" if release else None,
                "lines": [
                    ("Release", release.name if release else "-"),
                    ("Version", release.version_label if release else "-"),
                    (
                        "Effective date",
                        (release.published_at or "not yet published") if release else "-",
                    ),
                    ("Generated (UTC)", generated_at),
                    ("Generated by", getattr(actor, "full_name", "")),
                    ("Records", str(len(rows))),
                    ("Profile", profile.code if profile else "default"),
                    ("Audience", AUDIENCES[options.audience][1] if options.audience else "all"),
                    ("Language", options.language or "source"),
                    ("Software version", options.software_version or "all"),
                ],
                "content_digest": digest,
                "footer": f"{release.name} {release.version_label}" if release else "CSCM Tool",
            }

        data = ExportService._render(
            export_format,
            rows,
            columns,
            notice,
            title,
            profile.pdf_orientation if profile else "L",
            options.language,
        )
        kind = (
            "working-set_NOT_FOR_DISTRIBUTION"
            if notice
            else ("release" if release_id else "released")
        )
        label_parts = [p for p in (name_label, profile.code if profile else None) if p]
        label_parts += [
            p for p in (options.audience, options.language, options.software_version) if p
        ]
        data_name = export_filename(kind, export_format, "-".join(label_parts) or None)
        data_hash = manifest_service.sha256_hex(data)

        manifest = manifest_service.build_manifest(
            generated_at=generated_at,
            generated_by={"id": actor.id, "username": getattr(actor, "username", None)},
            release=(
                {
                    "id": release.id,
                    "name": release.name,
                    "version_label": release.version_label,
                    "effective_date": release.published_at,
                }
                if release
                else None
            ),
            scope=(
                scope if scope is not None else ({"release_id": release_id} if release_id else {})
            ),
            export_format=export_format,
            profile=profile.code if profile else None,
            audience=options.audience,
            language=options.language,
            software_version=options.software_version,
            row_count=len(rows),
            files=[{"name": data_name, "sha256": data_hash, "size_bytes": len(data)}],
            digest=digest,
        )

        job = ExportJob(
            requested_by=actor.id,
            export_type=export_format.upper(),
            export_scope_type="CATALOGUE",
            scope=json.dumps(manifest["scope"]),
            release_id=release_id,
            status="COMPLETE",
            created_at=generated_at,
            completed_at=utcnow_iso(),
            sha256=data_hash,
            size_bytes=len(data),
            row_count=len(rows),
            profile_code=profile.code if profile else None,
            audience=options.audience,
            language_code=options.language,
            software_version_code=options.software_version,
            manifest=json.dumps(manifest, sort_keys=True),
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
                "sha256": data_hash,
                "profile": job.profile_code,
                "audience": options.audience,
                "language": options.language,
                "software_version": options.software_version,
            },
        )
        db.session.commit()

        if options.bundle:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(data_name, data)
                archive.writestr(
                    "MANIFEST.json",
                    json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False),
                )
                for extra_name, extra_bytes in options.extra_files.items():
                    archive.writestr(extra_name, extra_bytes)
            return ExportResult(
                buffer.getvalue(),
                "application/zip",
                data_name.rsplit(".", 1)[0] + ".zip",
                data_hash,
                manifest,
                job.id,
            )
        return ExportResult(data, mimetype, data_name, data_hash, manifest, job.id)

    @staticmethod
    def _record(
        actor,
        *,
        export_type: str,
        scope_type: str,
        release_id: int | None,
        data_name: str,
        data: bytes,
        manifest: dict,
        audit_action: str,
        options: ExportOptions,
        row_count: int,
    ) -> ExportJob:
        job = ExportJob(
            requested_by=actor.id,
            export_type=export_type,
            export_scope_type=scope_type,
            scope=json.dumps(manifest["scope"]),
            release_id=release_id,
            status="COMPLETE",
            created_at=manifest["generated_at"],
            completed_at=utcnow_iso(),
            sha256=manifest["files"][0]["sha256"],
            size_bytes=len(data),
            row_count=row_count,
            audience=options.audience,
            language_code=options.language,
            software_version_code=options.software_version,
            manifest=json.dumps(manifest, sort_keys=True),
        )
        db.session.add(job)
        db.session.flush()
        AuditService.log(
            "ExportJob",
            job.id,
            audit_action,
            actor=actor,
            after={
                "file": data_name,
                "sha256": job.sha256,
                "row_count": row_count,
                "release_id": release_id,
            },
        )
        db.session.commit()
        return job

    @staticmethod
    def _zip(data_name: str, data: bytes, manifest: dict, extras: dict[str, bytes]) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(data_name, data)
            archive.writestr(
                "MANIFEST.json", json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False)
            )
            for name, content in extras.items():
                archive.writestr(name, content)
        return buffer.getvalue()

    @staticmethod
    def export_offline_bundle(
        release: Release, actor, options: ExportOptions | None = None
    ) -> ExportResult:
        """I-24: a single self-contained HTML lookup page for one published Release."""
        from app.export.offline_bundle import build_offline_bundle

        options = options or ExportOptions()
        revisions = [item.revision for item in release.items]
        rows, _columns = ExportService._prepare(revisions, options, None)
        digest = manifest_service.content_digest(rows)
        generated_at = utcnow_iso()
        html = build_offline_bundle(
            rows,
            title=f"{release.name} ({release.version_label})",
            subtitle="Status code lookup"
            + (f" - {AUDIENCES[options.audience][1]}" if options.audience else ""),
            generated=generated_at,
            digest=digest,
        )
        label = "-".join(
            p for p in (release.version_label, options.audience, options.language) if p
        )
        data_name = export_filename("offline-lookup", "html", label)
        manifest = manifest_service.build_manifest(
            generated_at=generated_at,
            generated_by={"id": actor.id, "username": getattr(actor, "username", None)},
            release={
                "id": release.id,
                "name": release.name,
                "version_label": release.version_label,
                "effective_date": release.published_at,
            },
            scope={"release_id": release.id, "kind": "offline-bundle"},
            export_format="html",
            profile=None,
            audience=options.audience,
            language=options.language,
            software_version=options.software_version,
            row_count=len(rows),
            files=[
                {
                    "name": data_name,
                    "sha256": manifest_service.sha256_hex(html),
                    "size_bytes": len(html),
                }
            ],
            digest=digest,
            kind="offline-bundle",
        )
        job = ExportService._record(
            actor,
            export_type="HTML",
            scope_type="OFFLINE_BUNDLE",
            release_id=release.id,
            data_name=data_name,
            data=html,
            manifest=manifest,
            audit_action="OFFLINE_BUNDLE_EXPORT",
            options=options,
            row_count=len(rows),
        )
        sha = manifest["files"][0]["sha256"]
        if options.bundle:
            zipped = ExportService._zip(data_name, html, manifest, {})
            return ExportResult(
                zipped,
                "application/zip",
                data_name.rsplit(".", 1)[0] + ".zip",
                sha,
                manifest,
                job.id,
            )
        return ExportResult(html, "text/html", data_name, sha, manifest, job.id)

    @staticmethod
    def export_release_notes(
        release: Release, fmt: str, actor, bundle: bool = False
    ) -> ExportResult:
        """I-06: release notes (added / changed / deprecated vs the previous Release)."""
        from app.services.release_notes_service import ReleaseNotesService

        notes = ReleaseNotesService.build(release.id)
        if fmt == "json":
            data = json.dumps(notes, indent=2, ensure_ascii=False).encode("utf-8")
            mimetype, extension = "application/json", "json"
        else:
            data, mimetype, extension = ReleaseNotesService.render(notes, fmt)
        rows = (
            [("added", n) for n in notes["added"]]
            + [("changed", n) for n in notes["changed"]]
            + [("deprecated", n) for n in notes["deprecated"]]
        )
        digest = manifest_service.content_digest([notes])
        data_name = export_filename("release-notes", extension, release.version_label)
        manifest = manifest_service.build_manifest(
            generated_at=utcnow_iso(),
            generated_by={"id": actor.id, "username": getattr(actor, "username", None)},
            release={
                "id": release.id,
                "name": release.name,
                "version_label": release.version_label,
                "effective_date": release.published_at,
            },
            scope={"release_id": release.id, "kind": "release-notes"},
            export_format=extension,
            profile=None,
            audience=None,
            language=None,
            software_version=None,
            row_count=len(rows),
            files=[
                {
                    "name": data_name,
                    "sha256": manifest_service.sha256_hex(data),
                    "size_bytes": len(data),
                }
            ],
            digest=digest,
            kind="release-notes",
        )
        job = ExportService._record(
            actor,
            export_type={"md": "MD", "csv": "CSV", "pdf": "PDF", "json": "JSON"}[extension],
            scope_type="RELEASE_NOTES",
            release_id=release.id,
            data_name=data_name,
            data=data,
            manifest=manifest,
            audit_action="RELEASE_NOTES_EXPORT",
            options=ExportOptions(),
            row_count=len(rows),
        )
        sha = manifest["files"][0]["sha256"]
        if bundle:
            return ExportResult(
                ExportService._zip(data_name, data, manifest, {}),
                "application/zip",
                data_name.rsplit(".", 1)[0] + ".zip",
                sha,
                manifest,
                job.id,
            )
        return ExportResult(data, mimetype, data_name, sha, manifest, job.id)

    @staticmethod
    def history(release_id: int | None = None, limit: int = 100) -> list[ExportJob]:
        """Recorded exports (newest first) with their hashes, for audit and verification."""
        query = db.session.query(ExportJob).filter(ExportJob.export_scope_type != "FULL_DATABASE")
        if release_id is not None:
            query = query.filter(ExportJob.release_id == release_id)
        return query.order_by(ExportJob.id.desc()).limit(limit).all()

    @staticmethod
    def find_by_hash(sha256: str) -> list[ExportJob]:
        return db.session.query(ExportJob).filter(ExportJob.sha256 == sha256).all()

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
    def export_full_database(actor, reauth_password: str | None = None) -> tuple[bytes, str, str]:
        """SEC-015: Administrator only; I-17: needs the actor's password again."""
        require_roles(actor, "ADMINISTRATOR")
        AuthService.step_up(actor, reauth_password, "FULL_DATABASE_EXPORT")
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

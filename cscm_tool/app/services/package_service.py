"""Release packages (FR-174): one download with every language and every access level.

Technical Publications builds the manuals and the sales / service / customer documents from a
published Release. Asking for them one language and one audience at a time is 9 audiences x 19
languages x several formats of clicking, so a package does it in one go: a ZIP holding, for the
complete baseline of the Release (FR-173),

    <version>/<language>/<audience or all>/<file>      one file per format
    <version>/release-notes.md                         what this Release changed
    <version>/MANIFEST.json                            every file with its SHA-256, row count,
                                                       language, audience and the per-language
                                                       translation coverage

Roughly 900 main-controller plus 350 hub-controller codes make this several minutes of work, so
the ZIP is built by a worker thread (inline in tests) that reports its progress on the job row.
The finished file is kept under the instance folder and recorded like every other export, with
the SHA-256 of the ZIP. An audience file contains only what that audience may see (BR-021) and an
untranslated code falls back to the source language, marked in `content_language`."""

import json
import re
import threading
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from flask import current_app

from app.auth.providers import AuthenticatedUser
from app.domain.errors import DomainError, NotFoundError
from app.extensions import db
from app.models.export_job import ExportJob
from app.models.lookup import LookupLanguage
from app.models.release import Release
from app.models.user import User
from app.services import manifest_service
from app.services.audience_service import AUDIENCES, validate_audience
from app.services.audit_service import AuditService
from app.services.baseline_service import BaselineService, validate_controller, validate_platform
from app.services.export_service import ExportOptions, ExportService, flatten_revision
from app.services.release_notes_service import ReleaseNotesService
from app.services.translation_service import TranslationService, source_language
from app.utils import utcnow_iso

FORMATS = ("csv", "json", "xlsx", "pdf")
_ALL = "all"  # the folder name of the file for everyone (no audience applied)


@dataclass
class PackageRequest:
    """What goes into a package. Empty `languages` / `audiences` mean "all of them"."""

    formats: tuple[str, ...] = ("csv", "xlsx", "pdf")
    languages: tuple[str, ...] = ()
    audiences: tuple[str, ...] = ()
    include_unfiltered: bool = True  # also the file with every column, for internal use
    platform: str | None = None
    controller: str | None = None
    strict_language: bool = False
    extra: dict = field(default_factory=dict)

    def to_scope(self) -> dict:
        return {
            "kind": "package",
            "formats": list(self.formats),
            "languages": list(self.languages),
            "audiences": list(self.audiences),
            "include_unfiltered": self.include_unfiltered,
            "platform": self.platform,
            "controller": self.controller,
            "strict_language": self.strict_language,
        }


def _safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-")


def package_directory() -> Path:
    path = Path(current_app.instance_path) / "packages"
    path.mkdir(parents=True, exist_ok=True)
    return path


class PackageService:
    @staticmethod
    def languages() -> list[LookupLanguage]:
        return list(
            db.session.query(LookupLanguage)
            .filter(LookupLanguage.is_active == 1)
            .order_by(LookupLanguage.sort_order)
            .all()
        )

    @staticmethod
    def validate(request: PackageRequest) -> PackageRequest:
        formats = tuple(dict.fromkeys(request.formats))
        if not formats:
            raise ValueError("Choose at least one format.")
        unknown = [f for f in formats if f not in FORMATS]
        if unknown:
            raise ValueError(f"Unknown format '{unknown[0]}'. Use one of: {', '.join(FORMATS)}.")
        known_languages = {lang.code for lang in PackageService.languages()}
        languages = tuple(dict.fromkeys(request.languages)) or tuple(sorted(known_languages))
        for code in languages:
            if code not in known_languages:
                raise ValueError(f"Unknown language '{code}'.")
        audiences = tuple(
            dict.fromkeys(validate_audience(a) or "" for a in request.audiences)
        ) or tuple(AUDIENCES)
        audiences = tuple(a for a in audiences if a)
        if not audiences and not request.include_unfiltered:
            raise ValueError("Choose at least one access level or the unfiltered files.")
        return PackageRequest(
            formats=formats,
            languages=languages,
            audiences=audiences,
            include_unfiltered=request.include_unfiltered,
            platform=validate_platform(request.platform),
            controller=validate_controller(request.controller),
            strict_language=request.strict_language,
        )

    # ------------------------------------------------------------------ requesting
    @staticmethod
    def request(
        release: Release,
        actor,
        package: PackageRequest | None = None,
        asynchronous: bool | None = None,
    ) -> ExportJob:
        """Starts building a package; returns the job (PENDING, or COMPLETE when run inline)."""
        if release.status != "PUBLISHED":
            raise DomainError("Only a published Release can be packaged.")
        package = PackageService.validate(package or PackageRequest())
        total = len(PackageService._variants(package)) * len(package.formats)

        job = ExportJob(
            requested_by=actor.id,
            export_type="ZIP",
            export_scope_type="CATALOGUE",
            scope=json.dumps({"release_id": release.id, **package.to_scope()}),
            release_id=release.id,
            status="PENDING",
            created_at=utcnow_iso(),
            language_code=None,
            manifest=json.dumps({"progress": {"done": 0, "total": total}}),
        )
        db.session.add(job)
        db.session.flush()
        AuditService.log(
            "ExportJob",
            job.id,
            "PACKAGE_REQUEST",
            actor=actor,
            after={"release_id": release.id, **package.to_scope(), "files": total},
        )
        db.session.commit()

        run_async = (
            asynchronous
            if asynchronous is not None
            else not current_app.config.get("PACKAGE_ASYNC_INLINE")
        )
        if not run_async:
            return PackageService._build(job.id, actor.id, package)

        app = current_app._get_current_object()  # type: ignore[attr-defined]
        job_id, actor_id = job.id, actor.id

        def worker() -> None:
            with app.app_context():
                try:
                    PackageService._build(job_id, actor_id, package)
                except Exception:  # noqa: BLE001  (the job row already records FAILED)
                    current_app.logger.exception("package job %s failed", job_id)
                finally:
                    db.session.remove()

        threading.Thread(target=worker, name=f"package-{job.id}", daemon=True).start()
        return job

    @staticmethod
    def _variants(package: PackageRequest) -> list[tuple[str, str | None]]:
        """(language, audience) pairs; audience None = the unfiltered file."""
        audiences: list[str | None] = list(package.audiences)
        if package.include_unfiltered:
            audiences.append(None)
        return [(language, audience) for language in package.languages for audience in audiences]

    # ------------------------------------------------------------------ building
    @staticmethod
    def _progress(job: ExportJob, done: int, total: int) -> None:
        job.manifest = json.dumps({"progress": {"done": done, "total": total}})
        db.session.commit()

    @staticmethod
    def _build(job_id: int, actor_id: int, package: PackageRequest) -> ExportJob:
        job = db.session.get(ExportJob, job_id)
        if job is None:
            raise NotFoundError("Package not found")
        try:
            return PackageService._build_zip(job, actor_id, package)
        except Exception as exc:
            db.session.rollback()
            job = db.session.get(ExportJob, job_id)
            if job is not None:
                job.status = "FAILED"
                job.completed_at = utcnow_iso()
                job.manifest = json.dumps({"error": str(exc)[:500]})
                db.session.commit()
            raise

    @staticmethod
    def _build_zip(job: ExportJob, actor_id: int, package: PackageRequest) -> ExportJob:
        release = db.session.get(Release, job.release_id)
        user = db.session.get(User, actor_id)
        if release is None or user is None:
            raise NotFoundError("Release not found")
        actor = AuthenticatedUser.from_model(user)

        revisions = BaselineService.revisions(
            release, platform=package.platform, controller=package.controller
        )
        flat = {r.id: flatten_revision(r) for r in revisions}
        baseline_digest = manifest_service.content_digest([flat[r.id] for r in revisions])
        generated_at = utcnow_iso()
        source = source_language().code
        variants = PackageService._variants(package)
        total = len(variants) * len(package.formats)
        root = _safe(release.version_label)

        # translation coverage per language, for the manifest (and the publication check)
        ids = [r.id for r in revisions]
        coverage = {}
        for language in package.languages:
            translated = (
                len(ids)
                if language == source
                else len(TranslationService.approved_for(ids, language))
            )
            coverage[language] = {"translated": translated, "of": len(ids)}

        target = package_directory() / f"package_{job.id}.zip"
        files: list[dict] = []
        done = 0
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for language, audience in variants:
                options = ExportOptions(
                    audience=audience,
                    language=language,
                    strict_language=package.strict_language,
                    platform=package.platform,
                    controller=package.controller,
                )
                rows, columns = ExportService._prepare(revisions, options, None, flat=flat)
                digest = manifest_service.content_digest(rows)
                folder = f"{root}/{language}/{audience or _ALL}"
                for fmt in package.formats:
                    title = ExportService.title_page(
                        release, None, options, len(rows), digest, actor, generated_at
                    )
                    data = ExportService._render(
                        fmt, rows, columns, None, title, "L", options.language
                    )
                    name = "_".join(
                        p
                        for p in (
                            "cscm",
                            _safe(release.version_label),
                            audience or _ALL,
                            language,
                            package.platform,
                            package.controller,
                        )
                        if p
                    )
                    path = f"{folder}/{name}.{fmt}"
                    archive.writestr(path, data)
                    files.append(
                        {
                            "name": path,
                            "sha256": manifest_service.sha256_hex(data),
                            "size_bytes": len(data),
                            "rows": len(rows),
                            "language": language,
                            "audience": audience,
                            "format": fmt,
                        }
                    )
                    done += 1
                    if done % 5 == 0 or done == total:
                        PackageService._progress(job, done, total)

            notes, _mime, _ext = ReleaseNotesService.render(
                ReleaseNotesService.build(release.id), "md"
            )
            archive.writestr(f"{root}/release-notes.md", notes)
            files.append(
                {
                    "name": f"{root}/release-notes.md",
                    "sha256": manifest_service.sha256_hex(notes),
                    "size_bytes": len(notes),
                    "rows": None,
                    "language": None,
                    "audience": None,
                    "format": "md",
                }
            )

            scope = {"release_id": release.id, "content": "baseline", **package.to_scope()}
            scope["coverage"] = coverage
            manifest = manifest_service.build_manifest(
                generated_at=generated_at,
                generated_by={"id": actor.id, "username": actor.username},
                release={
                    "id": release.id,
                    "name": release.name,
                    "version_label": release.version_label,
                    "effective_date": release.published_at,
                },
                scope=scope,
                export_format="zip",
                profile=None,
                audience=None,
                language=None,
                software_version=None,
                row_count=len(revisions),
                files=files,
                digest=baseline_digest,
                kind="package",
            )
            archive.writestr(
                f"{root}/MANIFEST.json",
                json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False),
            )

        data_hash = manifest_service.sha256_hex(target.read_bytes())
        job.status = "COMPLETE"
        job.completed_at = utcnow_iso()
        job.file_reference = str(target)
        job.sha256 = data_hash
        job.size_bytes = target.stat().st_size
        job.row_count = len(revisions)
        job.manifest = json.dumps(manifest, sort_keys=True)
        AuditService.log(
            "ExportJob",
            job.id,
            "PACKAGE_EXPORT",
            actor=actor,
            after={
                "release_id": release.id,
                "files": len(files),
                "row_count": len(revisions),
                "sha256": data_hash,
            },
        )
        db.session.commit()
        return job

    # ------------------------------------------------------------------ reading
    @staticmethod
    def packages_of(release_id: int) -> list[ExportJob]:
        return [
            job
            for job in db.session.query(ExportJob)
            .filter(ExportJob.release_id == release_id, ExportJob.export_type == "ZIP")
            .order_by(ExportJob.id.desc())
            .all()
            if '"kind": "package"' in (job.scope or "")
        ]

    @staticmethod
    def get(job_id: int) -> ExportJob:
        job = db.session.get(ExportJob, job_id)
        if job is None or '"kind": "package"' not in (job.scope or ""):
            raise NotFoundError("Package not found")
        return job

    @staticmethod
    def status(job: ExportJob) -> dict:
        info = json.loads(job.manifest) if job.manifest else {}
        progress = info.get("progress") or {}
        if job.status == "COMPLETE":
            done = total = len(info.get("files", []))
        else:
            done, total = progress.get("done", 0), progress.get("total", 0)
        return {
            "id": job.id,
            "status": job.status,
            "done": done,
            "total": total,
            "error": info.get("error"),
            "size_bytes": job.size_bytes,
            "sha256": job.sha256,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
        }

    @staticmethod
    def content(job: ExportJob, actor) -> tuple[bytes, str]:
        if job.status != "COMPLETE" or not job.file_reference:
            raise DomainError("The package is not ready.")
        path = Path(job.file_reference)
        if not path.is_file():
            raise NotFoundError("The package file is no longer on the server.")
        release = db.session.get(Release, job.release_id)
        name = f"cscm_package_{_safe(release.version_label) if release else job.id}.zip"
        return path.read_bytes(), name

"""Release notes (I-06): what a Release added, changed and deprecated compared with the
previous published Release - the document Technical Publications needs to update the
manuals, generated instead of compiled by hand.

* added      - codes whose first decided revision is in this Release
* changed    - codes with an earlier decided revision, with the field-level diff
               (the same diff reviewers saw, RevisionDiffService)
* deprecated - codes whose deprecation was approved since the previous Release"""

import csv
import io
from datetime import UTC, datetime

from app.domain.errors import NotFoundError
from app.export.pdf_exporter import build_pdf
from app.extensions import db
from app.models.audit import AuditLogEntry
from app.models.release import Release
from app.models.status_code import StatusCodeRevision
from app.services.revision_diff_service import RevisionDiffService
from app.utils import format_iso


def _label(revision: StatusCodeRevision) -> str:
    return revision.status_code.status_code_identifier or f"draft #{revision.status_code_id}"


class ReleaseNotesService:
    @staticmethod
    def previous_release(release: Release) -> Release | None:
        reference = release.published_at or format_iso(datetime.now(UTC))
        return (
            db.session.query(Release)
            .filter(
                Release.status == "PUBLISHED",
                Release.id != release.id,
                Release.published_at < reference,
            )
            .order_by(Release.published_at.desc(), Release.id.desc())
            .first()
        )

    @staticmethod
    def build(release_id: int) -> dict:
        release = db.session.get(Release, release_id)
        if release is None:
            raise NotFoundError("Release not found")
        previous = ReleaseNotesService.previous_release(release)

        added, changed = [], []
        for item in sorted(release.items, key=lambda i: _label(i.revision)):
            revision = item.revision
            baseline = RevisionDiffService.baseline_for(revision)
            entry = {
                "status_code_id": revision.status_code_id,
                "status_code_identifier": revision.status_code.status_code_identifier,
                "title": revision.title,
                "revision_number": revision.revision_number,
            }
            if baseline is None:
                added.append(entry)
            else:
                changed.append(
                    {
                        **entry,
                        "from_revision": baseline.revision_number,
                        "changes": RevisionDiffService.field_changes(baseline, revision),
                    }
                )

        lower = previous.published_at if previous else ""
        upper = release.published_at or format_iso(datetime.now(UTC))
        deprecated = []
        entries = (
            db.session.query(AuditLogEntry)
            .filter(
                AuditLogEntry.action == "DEPRECATE",
                AuditLogEntry.entity_type == "StatusCodeRevision",
                AuditLogEntry.occurred_at > lower,
                AuditLogEntry.occurred_at <= upper,
            )
            .order_by(AuditLogEntry.id)
            .all()
        )
        for audit_entry in entries:
            dep_revision = db.session.get(StatusCodeRevision, audit_entry.entity_id)
            if dep_revision is None:
                continue
            superseded = None
            if dep_revision.superseded_by_status_code_id:
                from app.models.status_code import StatusCode

                target = db.session.get(StatusCode, dep_revision.superseded_by_status_code_id)
                superseded = target.status_code_identifier if target else None
            deprecated.append(
                {
                    "status_code_id": dep_revision.status_code_id,
                    "status_code_identifier": dep_revision.status_code.status_code_identifier,
                    "title": dep_revision.title,
                    "reason": dep_revision.deprecated_reason,
                    "superseded_by": superseded,
                    "deprecated_at": audit_entry.occurred_at,
                }
            )

        return {
            "release": {
                "id": release.id,
                "name": release.name,
                "version_label": release.version_label,
                "status": release.status,
                "published_at": release.published_at,
            },
            "previous_release": (
                {
                    "id": previous.id,
                    "name": previous.name,
                    "version_label": previous.version_label,
                    "published_at": previous.published_at,
                }
                if previous
                else None
            ),
            "added": added,
            "changed": changed,
            "deprecated": deprecated,
        }

    # ------------------------------------------------------------------ renderers
    @staticmethod
    def render(notes: dict, fmt: str) -> tuple[bytes, str, str]:
        if fmt == "md":
            return ReleaseNotesService._markdown(notes).encode("utf-8"), "text/markdown", "md"
        if fmt == "csv":
            return ReleaseNotesService._csv(notes), "text/csv", "csv"
        if fmt == "pdf":
            return ReleaseNotesService._pdf(notes), "application/pdf", "pdf"
        raise ValueError("format must be md, csv, pdf or json")

    @staticmethod
    def _markdown(notes: dict) -> str:
        release, previous = notes["release"], notes["previous_release"]
        lines = [
            f"# Release notes - {release['name']} ({release['version_label']})",
            "",
            f"Effective: {release['published_at'] or 'not yet published (preview)'}  ",
            "Compared with: "
            + (
                f"{previous['name']} ({previous['version_label']})"
                if previous
                else "no earlier release - everything is new"
            ),
            "",
            f"## Added ({len(notes['added'])})",
            "",
        ]
        lines += [f"- {a['status_code_identifier']} - {a['title']}" for a in notes["added"]] or [
            "_None._"
        ]
        lines += ["", f"## Changed ({len(notes['changed'])})", ""]
        for c in notes["changed"]:
            lines.append(
                f"### {c['status_code_identifier']} - {c['title']} "
                f"(revision {c['from_revision']} -> {c['revision_number']})"
            )
            lines.append("")
            if c["changes"]:
                lines += ["| Field | Before | After |", "|---|---|---|"]
                for ch in c["changes"]:
                    lines.append(
                        f"| {ch['field']} | {_md(ch['old_value'])} | {_md(ch['new_value'])} |"
                    )
            else:
                lines.append("_No field differences._")
            lines.append("")
        if not notes["changed"]:
            lines.append("_None._")
        lines += ["", f"## Deprecated ({len(notes['deprecated'])})", ""]
        for d in notes["deprecated"]:
            extra = f" - replaced by {d['superseded_by']}" if d["superseded_by"] else ""
            lines.append(f"- {d['status_code_identifier']} - {d['title']}{extra}: {d['reason']}")
        if not notes["deprecated"]:
            lines.append("_None._")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _flat_rows(notes: dict) -> list[dict]:
        rows = []
        for a in notes["added"]:
            rows.append(_row("ADDED", a, "", "", "", ""))
        for c in notes["changed"]:
            if not c["changes"]:
                rows.append(_row("CHANGED", c, "", "", "", "no field differences"))
            for ch in c["changes"]:
                rows.append(
                    _row(
                        "CHANGED",
                        c,
                        ch["field"],
                        _text(ch["old_value"]),
                        _text(ch["new_value"]),
                        "",
                    )
                )
        for d in notes["deprecated"]:
            rows.append(
                _row(
                    "DEPRECATED",
                    d,
                    "",
                    "",
                    "",
                    (d["reason"] or "")
                    + (f" (replaced by {d['superseded_by']})" if d["superseded_by"] else ""),
                )
            )
        return rows

    @staticmethod
    def _csv(notes: dict) -> bytes:
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=[
                "kind",
                "status_code_identifier",
                "title",
                "field",
                "before",
                "after",
                "note",
            ],
        )
        writer.writeheader()
        for row in ReleaseNotesService._flat_rows(notes):
            writer.writerow({k: _csv_safe(v) for k, v in row.items()})
        return buffer.getvalue().encode("utf-8")

    @staticmethod
    def _pdf(notes: dict) -> bytes:
        release = notes["release"]
        return build_pdf(
            ReleaseNotesService._flat_rows(notes),
            columns=[
                ("kind", "Kind"),
                ("status_code_identifier", "Status code"),
                ("title", "Title"),
                ("field", "Field"),
                ("before", "Before"),
                ("after", "After"),
                ("note", "Note"),
            ],
            title={
                "heading": f"Release notes - {release['name']}",
                "subtitle": release["version_label"],
                "lines": [
                    ("Effective", release["published_at"] or "preview"),
                    (
                        "Compared with",
                        (
                            notes["previous_release"]["version_label"]
                            if notes["previous_release"]
                            else "no earlier release"
                        ),
                    ),
                    ("Added", str(len(notes["added"]))),
                    ("Changed", str(len(notes["changed"]))),
                    ("Deprecated", str(len(notes["deprecated"]))),
                ],
                "footer": f"Release notes {release['version_label']}",
            },
        )


def _text(value) -> str:
    return "" if value is None else str(value)


def _md(value) -> str:
    return _text(value).replace("|", "\\|").replace("\n", " ") or "-"


def _csv_safe(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _row(kind: str, item: dict, field: str, before: str, after: str, note: str) -> dict:
    return {
        "kind": kind,
        "status_code_identifier": item["status_code_identifier"],
        "title": item["title"],
        "field": field,
        "before": before,
        "after": after,
        "note": note,
    }

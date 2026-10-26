"""Evidence on change requests (I-13): test reports, simulation results, design notes,
a safety assessment. Stored outside the web root (instance/attachments), type- and
size-allow-listed (SEC-024), content-checked against the claimed type, hashed, served
only to authenticated working roles as a download (never rendered in the browser)."""

import hashlib
import uuid
from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename

from app.domain.errors import ForbiddenError, InvalidTransitionError, NotFoundError
from app.extensions import db
from app.models.change_request import ChangeRequest, CrAttachment
from app.services.audit_service import AuditService
from app.utils import utcnow_iso

# extension -> (content type, kind of content check)
ALLOWED_TYPES: dict[str, tuple[str, str]] = {
    "pdf": ("application/pdf", "pdf"),
    "png": ("image/png", "png"),
    "jpg": ("image/jpeg", "jpeg"),
    "jpeg": ("image/jpeg", "jpeg"),
    "txt": ("text/plain", "text"),
    "log": ("text/plain", "text"),
    "md": ("text/markdown", "text"),
    "csv": ("text/csv", "text"),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "zip"),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "zip"),
}

_WORKING_ROLES = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")
_OPEN_STATES = ("DRAFT", "REVIEW", "PENDING_APPROVAL")


def _content_matches(kind: str, data: bytes) -> bool:
    if kind == "pdf":
        return data.startswith(b"%PDF-")
    if kind == "png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if kind == "jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if kind == "zip":
        return data.startswith(b"PK\x03\x04")
    if kind == "text":
        if b"\x00" in data:
            return False
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return True
    return False


def _storage_root() -> Path:
    return Path(current_app.instance_path) / "attachments"


class AttachmentService:
    @staticmethod
    def add(
        cr_id: int, filename: str, content: bytes, description: str | None, actor
    ) -> CrAttachment:
        cr = db.session.get(ChangeRequest, cr_id)
        if cr is None:
            raise NotFoundError("Change request not found")
        if actor.id != cr.requested_by and actor.role_code != "ADMINISTRATOR":
            raise ForbiddenError(
                "Only the author of the CR or an Administrator may attach evidence."
            )
        if cr.revision.lifecycle_status not in _OPEN_STATES:
            raise InvalidTransitionError("Evidence can only be attached while the CR is open.")

        safe_name = secure_filename(filename or "")
        extension = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
        if not safe_name or extension not in ALLOWED_TYPES:
            raise ValueError(
                "File type not allowed. Allowed: "
                + ", ".join(f".{e}" for e in sorted(ALLOWED_TYPES))
            )
        max_bytes = current_app.config["ATTACHMENT_MAX_BYTES"]
        if not content:
            raise ValueError("The file is empty.")
        if len(content) > max_bytes:
            raise ValueError(f"The file is larger than {max_bytes // (1024 * 1024)} MB.")
        content_type, kind = ALLOWED_TYPES[extension]
        if not _content_matches(kind, content):
            raise ValueError(f"The file content does not look like a .{extension} file.")
        existing = (
            db.session.query(CrAttachment).filter(CrAttachment.change_request_id == cr.id).count()
        )
        if existing >= current_app.config["ATTACHMENT_MAX_PER_CR"]:
            raise ValueError("This CR already has the maximum number of attachments.")

        digest = hashlib.sha256(content).hexdigest()
        directory = _storage_root() / str(cr.id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{uuid.uuid4().hex}.bin"
        path.write_bytes(content)

        attachment = CrAttachment(
            change_request_id=cr.id,
            filename=safe_name,
            content_type=content_type,
            size_bytes=len(content),
            sha256=digest,
            storage_path=str(path),
            description=(description or "").strip()[:300] or None,
            uploaded_by=actor.id,
            uploaded_at=utcnow_iso(),
        )
        db.session.add(attachment)
        db.session.flush()
        AuditService.log(
            "ChangeRequest",
            cr.id,
            "ATTACHMENT_ADD",
            actor=actor,
            after={
                "attachment_id": attachment.id,
                "filename": safe_name,
                "size_bytes": len(content),
                "sha256": digest,
            },
        )
        db.session.commit()
        return attachment

    @staticmethod
    def list_for(cr_id: int, actor) -> list[CrAttachment]:
        if actor.role_code not in _WORKING_ROLES:
            raise ForbiddenError("Evidence is visible to working roles only.")
        return (
            db.session.query(CrAttachment)
            .filter(CrAttachment.change_request_id == cr_id)
            .order_by(CrAttachment.id)
            .all()
        )

    @staticmethod
    def get_for_download(attachment_id: int, actor) -> tuple[Path, CrAttachment]:
        if actor.role_code not in _WORKING_ROLES:
            raise ForbiddenError("Evidence is visible to working roles only.")
        attachment = db.session.get(CrAttachment, attachment_id)
        if attachment is None:
            raise NotFoundError("Attachment not found")
        path = Path(attachment.storage_path)
        if not path.is_file():
            raise NotFoundError("The stored file is missing")
        return path, attachment

    @staticmethod
    def delete(attachment_id: int, actor) -> None:
        attachment = db.session.get(CrAttachment, attachment_id)
        if attachment is None:
            raise NotFoundError("Attachment not found")
        cr = db.session.get(ChangeRequest, attachment.change_request_id)
        if cr is None:
            raise NotFoundError("Change request not found")
        if actor.id != attachment.uploaded_by and actor.role_code != "ADMINISTRATOR":
            raise ForbiddenError("Only the uploader or an Administrator may remove evidence.")
        if cr.revision.lifecycle_status != "DRAFT":
            raise InvalidTransitionError(
                "Evidence cannot be removed once the CR has been submitted for review."
            )
        AuditService.log(
            "ChangeRequest",
            cr.id,
            "ATTACHMENT_DELETE",
            actor=actor,
            before={"attachment_id": attachment.id, "filename": attachment.filename},
        )
        Path(attachment.storage_path).unlink(missing_ok=True)
        db.session.delete(attachment)
        db.session.commit()

    @staticmethod
    def purge_for_cr(cr_id: int) -> None:
        """Called when a CR is withdrawn: its evidence goes with it (the audit entry of the
        withdrawal records what was attached)."""
        for attachment in (
            db.session.query(CrAttachment).filter(CrAttachment.change_request_id == cr_id).all()
        ):
            Path(attachment.storage_path).unlink(missing_ok=True)
            db.session.delete(attachment)

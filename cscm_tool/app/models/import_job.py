"""Library import (EPIC-14, new 2026-09-17). See docs/06-data-dictionary.md
§5 and docs/05-governance-handbook.md §6b: every successfully validated row
becomes a normal Draft StatusCode/StatusCodeRevision/ChangeRequest triple —
import is a faster data-entry path, never a governance bypass."""

from app.extensions import Base, db


class ImportJob(Base):
    __tablename__ = "import_job"

    id = db.Column(db.Integer, primary_key=True)
    requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    source_format = db.Column(db.Text, nullable=False)  # CSV | XLSX
    source_file_reference = db.Column(db.Text, nullable=False)
    row_count = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Text, nullable=False, default="PENDING")
    created_count = db.Column(db.Integer, nullable=False, default=0)
    error_count = db.Column(db.Integer, nullable=False, default=0)
    error_report_reference = db.Column(db.Text)
    created_at = db.Column(db.Text, nullable=False)
    completed_at = db.Column(db.Text)

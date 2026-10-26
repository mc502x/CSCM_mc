"""Library import (EPIC-14, new 2026-09-17). See docs/06-data-dictionary.md
§5 and docs/05-governance-handbook.md §6b: every successfully validated row
becomes a normal Draft StatusCode/StatusCodeRevision/ChangeRequest triple —
import is a faster data-entry path, never a governance bypass."""

from app.extensions import Base, db


class ImportJob(Base):
    __tablename__ = "import_job"

    id = db.Column(db.Integer, primary_key=True)
    requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    source_format = db.Column(db.Text, nullable=False)  # CSV | XLSX | ST
    source_file_reference = db.Column(db.Text, nullable=False)
    row_count = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Text, nullable=False, default="PENDING")
    created_count = db.Column(db.Integer, nullable=False, default=0)
    error_count = db.Column(db.Integer, nullable=False, default=0)
    error_report_reference = db.Column(db.Text)
    created_at = db.Column(db.Text, nullable=False)
    completed_at = db.Column(db.Text)
    processed_count = db.Column(db.Integer, nullable=False, default=0)  # I-32 progress
    warning_count = db.Column(db.Integer, nullable=False, default=0)  # I-12 / I-04
    import_mode = db.Column(db.Text, nullable=False, default="CREATE")  # I-05: CREATE | UPDATE
    error_report_xlsx_reference = db.Column(db.Text)
    change_set_id = db.Column(db.Integer, db.ForeignKey("change_set.id"))  # v4.2: ST batch


class ImportSourceItem(Base):
    """One imported StCd_<n>.st program: where it came from and everything the file said."""

    __tablename__ = "import_source_item"

    id = db.Column(db.Integer, primary_key=True)
    import_job_id = db.Column(db.Integer, db.ForeignKey("import_job.id"), nullable=False)
    status_code_id = db.Column(db.Integer, db.ForeignKey("status_code.id"), nullable=False)
    source_file = db.Column(db.Text, nullable=False)
    source_sha256 = db.Column(db.Text, nullable=False)
    program_number = db.Column(db.Integer, nullable=False)
    controller = db.Column(db.Text, nullable=False)  # MC | HC
    source_line = db.Column(db.Integer, nullable=False, default=0)
    parsed_json = db.Column(db.Text, nullable=False)

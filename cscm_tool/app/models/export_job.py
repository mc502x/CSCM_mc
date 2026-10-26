"""Catalogue and full-database export tracking. See docs/14-deployment-architecture.md §5."""

from app.extensions import Base, db


class ExportJob(Base):
    __tablename__ = "export_job"

    id = db.Column(db.Integer, primary_key=True)
    requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    export_type = db.Column(
        db.Text, nullable=False
    )  # CSV | JSON | XLSX | PDF | SQLITE_BACKUP | HTML | MD | ZIP
    export_scope_type = db.Column(
        db.Text, nullable=False, default="CATALOGUE"
    )  # CATALOGUE | FULL_DATABASE | RELEASE_NOTES | OFFLINE_BUNDLE
    scope = db.Column(db.Text, nullable=False, default="{}")
    release_id = db.Column(db.Integer, db.ForeignKey("release.id"))
    status = db.Column(db.Text, nullable=False, default="PENDING")  # PENDING | COMPLETE | FAILED
    created_at = db.Column(db.Text, nullable=False)
    completed_at = db.Column(db.Text)
    file_reference = db.Column(db.Text)
    sha256 = db.Column(db.Text)  # I-06
    size_bytes = db.Column(db.Integer)
    row_count = db.Column(db.Integer)
    profile_code = db.Column(db.Text)
    audience = db.Column(db.Text)
    language_code = db.Column(db.Text)
    software_version_code = db.Column(db.Text)
    manifest = db.Column(db.Text)  # JSON text of the manifest handed out with the file

    requester = db.relationship("User")
    release = db.relationship("Release")


class ExportProfile(Base):
    """I-02/I-03: Administrator-managed export column sets (data, not code)."""

    __tablename__ = "export_profile"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False, unique=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    columns = db.Column(db.Text, nullable=False)  # JSON [{"field":..,"label":..}]
    language_code = db.Column(db.Text)
    audience = db.Column(db.Text)
    title_page = db.Column(db.Integer, nullable=False, default=1)
    pdf_orientation = db.Column(db.Text, nullable=False, default="L")
    is_active = db.Column(db.Integer, nullable=False, default=1)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.Text, nullable=False)

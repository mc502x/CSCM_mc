"""Catalogue and full-database export tracking. See docs/14-deployment-architecture.md §5."""

from app.extensions import Base, db


class ExportJob(Base):
    __tablename__ = "export_job"

    id = db.Column(db.Integer, primary_key=True)
    requested_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    export_type = db.Column(db.Text, nullable=False)  # CSV | JSON | PDF | SQLITE_BACKUP
    export_scope_type = db.Column(
        db.Text, nullable=False, default="CATALOGUE"
    )  # CATALOGUE | FULL_DATABASE
    scope = db.Column(db.Text, nullable=False, default="{}")
    release_id = db.Column(db.Integer, db.ForeignKey("release.id"))
    status = db.Column(db.Text, nullable=False, default="PENDING")  # PENDING | COMPLETE | FAILED
    created_at = db.Column(db.Text, nullable=False)
    completed_at = db.Column(db.Text)
    file_reference = db.Column(db.Text)

    requester = db.relationship("User")
    release = db.relationship("Release")

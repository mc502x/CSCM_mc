"""Release management. See docs/05-governance-handbook.md and schema.sql
trg_prevent_sandbox_release / trg_prevent_release_item_delete triggers."""

from typing import cast

from app.extensions import Base, db
from app.models.status_code import StatusCodeRevision


class Release(Base):
    __tablename__ = "release"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    version_label = db.Column(db.Text, nullable=False, unique=True)
    description = db.Column(db.Text)
    scope_filter = db.Column(db.Text, nullable=False, default="{}")
    status = db.Column(db.Text, nullable=False, default="BUILDING")  # BUILDING | PUBLISHED
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.Text, nullable=False)
    published_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    published_at = db.Column(db.Text)

    items: list["ReleaseItem"] = cast(
        "list[ReleaseItem]", db.relationship("ReleaseItem", back_populates="release")
    )


class ReleaseItem(Base):
    __tablename__ = "release_item"

    id = db.Column(db.Integer, primary_key=True)
    release_id = db.Column(db.Integer, db.ForeignKey("release.id"), nullable=False)
    status_code_revision_id = db.Column(
        db.Integer, db.ForeignKey("status_code_revision.id"), nullable=False, unique=True
    )

    release: Release = cast(Release, db.relationship("Release", back_populates="items"))
    revision: StatusCodeRevision = cast(StatusCodeRevision, db.relationship("StatusCodeRevision"))

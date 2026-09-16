"""Immutable audit trail. See docs/12-audit-compliance.md. Written only via
AuditService, never mutated or deleted after insert."""

from app.extensions import Base, db


class AuditLogEntry(Base):
    __tablename__ = "audit_log_entry"

    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.Text, nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.Text, nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    occurred_at = db.Column(db.Text, nullable=False)
    before_value = db.Column(db.Text)
    after_value = db.Column(db.Text)
    ip_address = db.Column(db.Text)
    request_id = db.Column(db.Text, nullable=False)

    actor = db.relationship("User")

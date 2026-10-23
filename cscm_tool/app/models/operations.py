"""Operational and integration tables added by the v4 improvement pack
(docs/21-improvement-ideas.md). Shapes mirror docs/artifacts/schema.sql."""

from typing import cast

from app.extensions import Base, db
from app.models.user import User


class RevisionTranslation(Base):
    """I-15: a revision's text in another language. No row means MISSING."""

    __tablename__ = "revision_translation"

    id = db.Column(db.Integer, primary_key=True)
    status_code_revision_id = db.Column(
        db.Integer, db.ForeignKey("status_code_revision.id"), nullable=False
    )
    language_id = db.Column(db.Integer, db.ForeignKey("lookup_language.id"), nullable=False)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    remedy_text = db.Column(db.Text)
    translation_status = db.Column(db.Text, nullable=False, default="DRAFT")  # DRAFT | APPROVED
    translated_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    translated_at = db.Column(db.Text, nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    approved_at = db.Column(db.Text)

    language = db.relationship("LookupLanguage")

    __table_args__ = (db.UniqueConstraint("status_code_revision_id", "language_id"),)


class Delegation(Base):
    """I-16: out-of-office cover for a decision role."""

    __tablename__ = "delegation"

    id = db.Column(db.Integer, primary_key=True)
    delegator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    delegate_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    role_code = db.Column(db.Text, nullable=False)
    valid_from = db.Column(db.Text, nullable=False)
    valid_to = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.Text, nullable=False)
    revoked_at = db.Column(db.Text)

    delegator: User = cast(User, db.relationship("User", foreign_keys=[delegator_id]))
    delegate: User = cast(User, db.relationship("User", foreign_keys=[delegate_id]))


class SavedSearch(Base):
    __tablename__ = "saved_search"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.Text, nullable=False)
    definition = db.Column(db.Text, nullable=False)  # JSON: filters + columns
    created_at = db.Column(db.Text, nullable=False)

    __table_args__ = (db.UniqueConstraint("user_id", "name"),)


class Notification(Base):
    """I-08: in-app notice for whoever holds the next decision."""

    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    kind = db.Column(db.Text, nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.Text)
    change_request_id = db.Column(db.Integer, db.ForeignKey("change_request.id"))
    dedupe_key = db.Column(db.Text, unique=True)
    created_at = db.Column(db.Text, nullable=False)
    read_at = db.Column(db.Text)
    emailed_at = db.Column(db.Text)


class LoginAttempt(Base):
    """I-20: persistent rate-limit counters shared by every worker process."""

    __tablename__ = "login_attempt"

    id = db.Column(db.Integer, primary_key=True)
    scope = db.Column(db.Text, nullable=False)  # IP | USER
    key = db.Column(db.Text, nullable=False)
    attempted_at = db.Column(db.Float, nullable=False)  # epoch seconds


class AppSetting(Base):
    __tablename__ = "app_setting"

    key = db.Column(db.Text, primary_key=True)
    value = db.Column(db.Text, nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    updated_at = db.Column(db.Text, nullable=False)


class OccurrenceImport(Base):
    """I-28: one batch of occurrence counts per code for a period."""

    __tablename__ = "occurrence_import"

    id = db.Column(db.Integer, primary_key=True)
    source_label = db.Column(db.Text, nullable=False)
    period_start = db.Column(db.Text, nullable=False)
    period_end = db.Column(db.Text, nullable=False)
    imported_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    imported_at = db.Column(db.Text, nullable=False)
    row_count = db.Column(db.Integer, nullable=False, default=0)
    unmatched_count = db.Column(db.Integer, nullable=False, default=0)


class CodeOccurrence(Base):
    __tablename__ = "code_occurrence"

    id = db.Column(db.Integer, primary_key=True)
    occurrence_import_id = db.Column(
        db.Integer, db.ForeignKey("occurrence_import.id"), nullable=False
    )
    status_code_id = db.Column(db.Integer, db.ForeignKey("status_code.id"), nullable=False)
    occurrences = db.Column(db.Integer, nullable=False)

    __table_args__ = (db.UniqueConstraint("occurrence_import_id", "status_code_id"),)


class ApiToken(Base):
    """I-29: a scoped, hashed, expiring machine token. The plaintext is shown once."""

    __tablename__ = "api_token"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.Text, nullable=False)
    token_prefix = db.Column(db.Text, nullable=False)
    token_hash = db.Column(db.Text, nullable=False, unique=True)
    scopes = db.Column(db.Text, nullable=False)  # space separated
    expires_at = db.Column(db.Text, nullable=False)
    last_used_at = db.Column(db.Text)
    revoked_at = db.Column(db.Text)
    created_at = db.Column(db.Text, nullable=False)


class Webhook(Base):
    __tablename__ = "webhook"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, nullable=False)
    secret = db.Column(db.Text, nullable=False)
    events = db.Column(db.Text, nullable=False, default="release.published")
    is_active = db.Column(db.Integer, nullable=False, default=1)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.Text, nullable=False)
    last_delivery_at = db.Column(db.Text)
    last_status = db.Column(db.Text)


class WebhookDelivery(Base):
    __tablename__ = "webhook_delivery"

    id = db.Column(db.Integer, primary_key=True)
    webhook_id = db.Column(db.Integer, db.ForeignKey("webhook.id"), nullable=False)
    event = db.Column(db.Text, nullable=False)
    payload = db.Column(db.Text, nullable=False)
    http_status = db.Column(db.Integer)
    ok = db.Column(db.Integer, nullable=False, default=0)
    error = db.Column(db.Text)
    delivered_at = db.Column(db.Text, nullable=False)


class HubMcMapping(Base):
    """I-36: which Main Controller code replaces which Hub Controller code."""

    __tablename__ = "hub_mc_mapping"

    id = db.Column(db.Integer, primary_key=True)
    hub_status_code_id = db.Column(
        db.Integer, db.ForeignKey("status_code.id"), nullable=False, unique=True
    )
    mc_status_code_id = db.Column(db.Integer, db.ForeignKey("status_code.id"), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.Text, nullable=False)

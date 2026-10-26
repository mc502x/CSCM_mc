"""Translation review (docs/26-translations.md): who reviews which language, the reviews, their
answers and the overrides that accepted proposals create."""

from app.extensions import Base, db


class LanguageReviewer(Base):
    __tablename__ = "language_reviewer"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    language_code = db.Column(db.Text, db.ForeignKey("lookup_language.code"), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    assigned_at = db.Column(db.Text, nullable=False)


class TranslationReview(Base):
    __tablename__ = "translation_review"

    id = db.Column(db.Integer, primary_key=True)
    language_code = db.Column(db.Text, db.ForeignKey("lookup_language.code"), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.Text, nullable=False, default="OPEN")  # OPEN | COMPLETED
    started_at = db.Column(db.Text, nullable=False)
    completed_at = db.Column(db.Text)
    fingerprint = db.Column(db.Text, nullable=False)
    string_count = db.Column(db.Integer, nullable=False)


class TranslationReviewItem(Base):
    __tablename__ = "translation_review_item"

    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey("translation_review.id"), nullable=False)
    string_id = db.Column(db.Text, nullable=False)
    english = db.Column(db.Text, nullable=False)
    current_text = db.Column(db.Text)
    verdict = db.Column(db.Text)  # OK | CHANGE | UNCLEAR
    proposal = db.Column(db.Text)
    comment = db.Column(db.Text)
    decision = db.Column(db.Text, nullable=False, default="PENDING")
    decided_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    decided_at = db.Column(db.Text)
    updated_at = db.Column(db.Text, nullable=False)


class TranslationOverride(Base):
    __tablename__ = "translation_override"

    id = db.Column(db.Integer, primary_key=True)
    language_code = db.Column(db.Text, db.ForeignKey("lookup_language.code"), nullable=False)
    string_id = db.Column(db.Text, nullable=False)
    english = db.Column(db.Text, nullable=False)
    text = db.Column(db.Text, nullable=False)
    review_item_id = db.Column(db.Integer, db.ForeignKey("translation_review_item.id"))
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.Text, nullable=False)

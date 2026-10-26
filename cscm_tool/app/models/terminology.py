"""Technical nomenclature (docs/26-translations.md, FR-166): the terms of the controller and the
workflow and their translations, apart from the interface translations."""

from app.extensions import Base, db


class TerminologyTerm(Base):
    __tablename__ = "terminology_term"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False, unique=True)
    category = db.Column(db.Text, nullable=False)
    english = db.Column(db.Text, nullable=False)
    definition = db.Column(db.Text, nullable=False, default="")
    keep_english = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Integer, nullable=False, default=1)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.Text, nullable=False)


class TerminologyTranslation(Base):
    __tablename__ = "terminology_translation"

    id = db.Column(db.Integer, primary_key=True)
    term_id = db.Column(db.Integer, db.ForeignKey("terminology_term.id"), nullable=False)
    language_code = db.Column(db.Text, db.ForeignKey("lookup_language.code"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    status = db.Column(db.Text, nullable=False, default="DRAFT")  # DRAFT | APPROVED
    note = db.Column(db.Text)
    proposed_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    proposed_at = db.Column(db.Text, nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    approved_at = db.Column(db.Text)

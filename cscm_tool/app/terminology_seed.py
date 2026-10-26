"""The technical nomenclature that ships with the tool (docs/26-translations.md, FR-166).

The rows are in `app/terminology_seed_product.py` and `app/terminology_seed_process.py`; this
module reads them into dictionaries and checks their shape, so a malformed row fails the tests
rather than the migration."""

from app.terminology_seed_process import KEEP, PROCESS
from app.terminology_seed_product import PRODUCT

# the order of the translations in every row
LANGUAGES = (
    "de", "fr", "hi", "ar", "bn", "mr", "te", "ta", "gu",
    "ur", "kn", "or", "ml", "pa", "es", "it", "da", "ka",
)  # fmt: skip
CATEGORIES = ("PRODUCT", "DATA", "STATE", "PROCESS", "ROLE", "AUDIENCE", "KEEP")


def terms() -> list[dict]:
    """One dict per term: code, category, english, definition, keep_english, translations."""
    out: list[dict] = []
    for code, category, english, definition, texts in [*PRODUCT, *PROCESS]:
        parts = [p.strip() for p in texts.split(" | ")]
        if len(parts) != len(LANGUAGES):
            raise ValueError(f"{code}: {len(parts)} translations, expected {len(LANGUAGES)}")
        out.append(
            {
                "code": code,
                "category": category,
                "english": english,
                "definition": definition,
                "keep_english": False,
                "translations": dict(zip(LANGUAGES, parts, strict=True)),
            }
        )
    for code, category, english, definition in KEEP:
        out.append(
            {
                "code": code,
                "category": category,
                "english": english,
                "definition": definition,
                "keep_english": True,
                "translations": {},
            }
        )
    return out

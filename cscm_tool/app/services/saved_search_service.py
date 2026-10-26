"""Saved searches, the column chooser and shareable filter links (I-26).

A *definition* is the filters of the Status Code list plus the visible columns. It is stored
per user under a name, and the same definition round-trips through the URL query string, so a
link pasted into a ticket reproduces exactly the view its author saw."""

import json
from urllib.parse import urlencode

from app.domain.errors import ForbiddenError, NotFoundError
from app.extensions import db
from app.models.operations import SavedSearch
from app.utils import utcnow_iso

FILTER_KEYS = (
    "q",
    "functional_system_group",
    "functional_subgroup",
    "turbine_platform",
    "lifecycle_status",
    "status_category",
    "sort",
    "is_sandbox",
)
# column key -> header label
COLUMNS: dict[str, str] = {
    "status_code_identifier": "Identifier",
    "title": "Title",
    "functional_system_group": "Group",
    "functional_subgroup": "Subgroup",
    "turbine_platforms": "Platforms",
    "status_category": "Category",
    "alarm_flag": "Alarm",
    "set_delay": "Set delay",
    "reset_delay": "Reset delay",
    "lifecycle_status": "State",
    "revision_number": "Rev.",
    "effective_date": "Effective",
    "affected_component": "Component",
}
DEFAULT_COLUMNS = (
    "status_code_identifier",
    "title",
    "functional_system_group",
    "status_category",
    "lifecycle_status",
)
SORTABLE = ("status_code_identifier", "title", "status_category", "lifecycle_status", "id")


def clean_definition(raw: dict | None) -> dict:
    """Validated copy: only known filter keys with non-empty values, only known columns."""
    raw = raw or {}
    filters = {}
    for key in FILTER_KEYS:
        value = (raw.get("filters") or {}).get(key, raw.get(key))
        if value not in (None, ""):
            filters[key] = str(value)
    columns = raw.get("columns")
    if isinstance(columns, str):
        columns = [c for c in columns.split(",") if c]
    columns = [c for c in (columns or []) if c in COLUMNS]
    return {"filters": filters, "columns": columns or list(DEFAULT_COLUMNS)}


def query_string(definition: dict) -> str:
    cleaned = clean_definition(definition)
    params = dict(cleaned["filters"])
    if cleaned["columns"] != list(DEFAULT_COLUMNS):
        params["cols"] = ",".join(cleaned["columns"])
    return urlencode(params)


class SavedSearchService:
    @staticmethod
    def list_for(actor) -> list[SavedSearch]:
        return (
            db.session.query(SavedSearch)
            .filter(SavedSearch.user_id == actor.id)
            .order_by(SavedSearch.name)
            .all()
        )

    @staticmethod
    def save(actor, name: str, definition: dict) -> SavedSearch:
        name = (name or "").strip()
        if not 1 <= len(name) <= 80:
            raise ValueError("A saved search needs a name of 1-80 characters.")
        cleaned = clean_definition(definition)
        row = (
            db.session.query(SavedSearch)
            .filter(SavedSearch.user_id == actor.id, SavedSearch.name == name)
            .first()
        )
        if row is None:
            row = SavedSearch(
                user_id=actor.id,
                name=name,
                definition=json.dumps(cleaned),
                created_at=utcnow_iso(),
            )
            db.session.add(row)
        else:  # saving under an existing name replaces it
            row.definition = json.dumps(cleaned)
        db.session.commit()
        return row

    @staticmethod
    def get(actor, search_id: int) -> SavedSearch:
        row = db.session.get(SavedSearch, search_id)
        if row is None:
            raise NotFoundError("Saved search not found")
        if row.user_id != actor.id:
            raise ForbiddenError("This saved search belongs to someone else.")
        return row

    @staticmethod
    def delete(actor, search_id: int) -> None:
        row = SavedSearchService.get(actor, search_id)
        db.session.delete(row)
        db.session.commit()

    @staticmethod
    def definition_of(row: SavedSearch) -> dict:
        return clean_definition(json.loads(row.definition))

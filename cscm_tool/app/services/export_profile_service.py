"""Export profiles (I-02): Administrator-managed column sets with header labels, an
optional default audience (I-03) and language (I-15) - data, not code.

A profile names export *fields* (the column names of the flat export row, see
`EXPORT_FIELDS`); the label is only the header shown to the reader."""

import json

from app.domain.authz import require_roles
from app.domain.errors import DomainError, NotFoundError
from app.extensions import db
from app.models.export_job import ExportProfile
from app.models.lookup import LookupLanguage
from app.services.audience_service import validate_audience
from app.services.audit_service import AuditService
from app.utils import utcnow_iso

# Every column flatten_revision() produces, plus the two the pipeline adds on request.
# (tests/integration/test_export_profiles.py keeps this list in step with flatten_revision.)
EXPORT_FIELDS = (
    "status_code_identifier",
    "functional_system_group",
    "functional_subgroup",
    "legacy_reference_number",
    "turbine_platforms",
    "revision_number",
    "title",
    "description",
    "software_version",
    "status_category",
    "available_group",
    "alarm_flag",
    "set_delay",
    "reset_delay",
    "up_down_counter",
    "trigger_snapshot",
    "loadless_spinning_permitted",
    "number_of_times_repeated",
    "repeated_over_the_course",
    "status_code_for_repeated_error",
    "yaw_program",
    "manual_reset_program",
    "auto_reset_program",
    "converter_reactive_power_program",
    "brake_program",
    "umrichterprogramm_gsc",
    "umrichterprogramm_msc",
    "yaw_bearing_lubrication_program",
    "development_access",
    "sales_access",
    "tcc_access",
    "service_access",
    "turbine_operator_package_access",
    "grid_operator_access",
    "service_partner_access",
    "customer_access",
    "logical_node",
    "node_value",
    "lifecycle_status",
    "effective_date",
    "remedy_text",
    "affected_component",
    "related_status_codes",
    "standard_references",
    "applies_from_version",
    "applies_to_version",
    "planned_effective_date",
    "planned_deprecation_date",
    "content_language",
    "access_level",
    "audience",
)


def parse_columns(raw: str) -> list[dict]:
    return json.loads(raw)


def _validate_columns(columns) -> list[dict]:
    if not isinstance(columns, list) or not columns:
        raise ValueError("A profile needs at least one column.")
    cleaned, seen = [], set()
    for entry in columns:
        if not isinstance(entry, dict):
            raise ValueError("Each column must be an object with 'field' and 'label'.")
        field = entry.get("field")
        label = (entry.get("label") or "").strip()
        if field not in EXPORT_FIELDS:
            raise ValueError(f"'{field}' is not an export field.")
        if field in seen:
            raise ValueError(f"Column '{field}' appears twice.")
        if not 1 <= len(label) <= 60:
            raise ValueError(f"The header label for '{field}' must be 1-60 characters.")
        seen.add(field)
        cleaned.append({"field": field, "label": label})
    return cleaned


def _validate_language(code: str | None) -> str | None:
    if not code:
        return None
    language = (
        db.session.query(LookupLanguage)
        .filter(LookupLanguage.code == code, LookupLanguage.is_active == 1)
        .first()
    )
    if language is None:
        raise ValueError(f"Unknown or inactive language '{code}'.")
    return code


class ExportProfileService:
    @staticmethod
    def list_all(include_inactive: bool = False) -> list[ExportProfile]:
        query = db.session.query(ExportProfile)
        if not include_inactive:
            query = query.filter(ExportProfile.is_active == 1)
        return query.order_by(ExportProfile.sort_order, ExportProfile.id).all()

    @staticmethod
    def get_by_code(code: str) -> ExportProfile:
        profile = (
            db.session.query(ExportProfile)
            .filter(ExportProfile.code == code, ExportProfile.is_active == 1)
            .first()
        )
        if profile is None:
            raise NotFoundError(f"Unknown export profile '{code}'.")
        return profile

    @staticmethod
    def create(data: dict, actor) -> ExportProfile:
        require_roles(actor, "ADMINISTRATOR")
        code = (data.get("code") or "").strip().upper()
        name = (data.get("name") or "").strip()
        if not code.replace("_", "").isalnum() or not 2 <= len(code) <= 40:
            raise ValueError("code must be 2-40 letters, digits or underscores.")
        if not 1 <= len(name) <= 80:
            raise ValueError("name must be 1-80 characters.")
        if db.session.query(ExportProfile).filter(ExportProfile.code == code).first():
            raise DomainError(f"An export profile '{code}' already exists.")
        profile = ExportProfile(
            code=code,
            name=name,
            description=(data.get("description") or "").strip() or None,
            columns=json.dumps(_validate_columns(data.get("columns"))),
            language_code=_validate_language(data.get("language")),
            audience=validate_audience(data.get("audience")),
            title_page=1 if data.get("title_page", True) else 0,
            pdf_orientation="P" if data.get("pdf_orientation") == "P" else "L",
            sort_order=int(data.get("sort_order", 0)),
            created_by=actor.id,
            created_at=utcnow_iso(),
        )
        db.session.add(profile)
        db.session.flush()
        AuditService.log(
            "ExportProfile",
            profile.id,
            "EXPORT_PROFILE_CREATE",
            actor=actor,
            after={"code": code, "columns": parse_columns(profile.columns)},
        )
        db.session.commit()
        return profile

    @staticmethod
    def update(profile_id: int, data: dict, actor) -> ExportProfile:
        require_roles(actor, "ADMINISTRATOR")
        profile = db.session.get(ExportProfile, profile_id)
        if profile is None:
            raise NotFoundError("Export profile not found")
        before = {
            "name": profile.name,
            "columns": parse_columns(profile.columns),
            "audience": profile.audience,
            "language": profile.language_code,
            "is_active": profile.is_active,
        }
        if "name" in data:
            name = (data["name"] or "").strip()
            if not 1 <= len(name) <= 80:
                raise ValueError("name must be 1-80 characters.")
            profile.name = name
        if "description" in data:
            profile.description = (data["description"] or "").strip() or None
        if "columns" in data:
            profile.columns = json.dumps(_validate_columns(data["columns"]))
        if "language" in data:
            profile.language_code = _validate_language(data["language"])
        if "audience" in data:
            profile.audience = validate_audience(data["audience"])
        if "title_page" in data:
            profile.title_page = 1 if data["title_page"] else 0
        if "pdf_orientation" in data:
            profile.pdf_orientation = "P" if data["pdf_orientation"] == "P" else "L"
        if "is_active" in data:
            profile.is_active = 1 if data["is_active"] else 0
        AuditService.log(
            "ExportProfile",
            profile.id,
            "EXPORT_PROFILE_UPDATE",
            actor=actor,
            before=before,
            after={
                "name": profile.name,
                "columns": parse_columns(profile.columns),
                "audience": profile.audience,
                "language": profile.language_code,
                "is_active": profile.is_active,
            },
        )
        db.session.commit()
        return profile

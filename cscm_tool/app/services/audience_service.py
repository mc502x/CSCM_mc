"""Audience-scoped publication (I-03, decision D-02).

A code carries eight audience-access values (Development, Sales, TCC, Service,
Turbine Operator Package, Grid Operator, Service Partner, Customer). An export or
bundle made *for an audience* contains only the codes whose value for that audience
lets it see the code, and none of the other audiences' columns.

"Lets it see" is data, not code: every access vocabulary row carries
`audience_visible`. 'Covert' is seeded as 0 (hidden) until the business confirms what
it means (docs/06-data-dictionary.md §9d), and a code with *no* value for the audience
is hidden too - the safe default is to disclose nothing. Only values the Administrator
has confirmed at sign-off count; a Draft's proposed values never do."""

from app import status_code_fields
from app.models.status_code import StatusCodeRevision

# audience -> (revision attribute, label)
AUDIENCES: dict[str, tuple[str, str]] = {
    "development": ("development_access", "Development"),
    "sales": ("sales_access", "Sales"),
    "tcc": ("tcc_access", "TCC"),
    "service": ("service_access", "Service"),
    "turbine_operator_package": ("turbine_operator_package_access", "Turbine Operator Package"),
    "grid_operator": ("grid_operator_access", "Grid Operator"),
    "service_partner": ("service_partner_access", "Service Partner"),
    "customer": ("customer_access", "Customer"),
}

ACCESS_COLUMNS = tuple(attr for attr, _label in AUDIENCES.values())

# Internal columns that never leave the building in an audience export.
INTERNAL_COLUMNS = (
    "legacy_reference_number",
    "yaw_program",
    "manual_reset_program",
    "auto_reset_program",
    "converter_reactive_power_program",
    "brake_program",
    "umrichterprogramm_gsc",
    "umrichterprogramm_msc",
    "yaw_bearing_lubrication_program",
    *status_code_fields.PROGRAM_FIELDS,
    *status_code_fields.FLAG_FIELDS,
    "operating_mode_mask",
    "task_call_frequency",
    "user_group_levels",
)


def validate_audience(audience: str | None) -> str | None:
    if audience in (None, ""):
        return None
    if audience not in AUDIENCES:
        raise ValueError(f"Unknown audience '{audience}'. Use one of: {', '.join(AUDIENCES)}.")
    return audience


class AudienceService:
    @staticmethod
    def access_value(revision: StatusCodeRevision, audience: str):
        return getattr(revision, AUDIENCES[audience][0])

    @staticmethod
    def is_visible(revision: StatusCodeRevision, audience: str) -> bool:
        if revision.admin_signoff_at is None:  # access values not yet confirmed
            return False
        value = AudienceService.access_value(revision, audience)
        return value is not None and bool(value.audience_visible)

    @staticmethod
    def filter_revisions(
        revisions: list[StatusCodeRevision], audience: str
    ) -> list[StatusCodeRevision]:
        return [r for r in revisions if AudienceService.is_visible(r, audience)]

    @staticmethod
    def scope_row(row: dict, revision: StatusCodeRevision, audience: str) -> dict:
        """The audience's view of an export row: other audiences' columns and internal
        columns removed, this audience's own access value kept as `access_level`."""
        value = AudienceService.access_value(revision, audience)
        scoped = {
            key: val
            for key, val in row.items()
            if key not in ACCESS_COLUMNS and key not in INTERNAL_COLUMNS
        }
        scoped["audience"] = audience
        scoped["access_level"] = value.code if value is not None else None
        return scoped

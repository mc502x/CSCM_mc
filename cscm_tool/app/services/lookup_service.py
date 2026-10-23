"""Read-only controlled-vocabulary listings and code-resolution helper used
by every other service. See docs/artifacts/openapi.yaml /lookups/{vocabulary}
and docs/06-data-dictionary.md §9.

v3 (2026-09-17) note on Functional System Group / Subgroup resolution: since
`lookup_functional_system_group.code` is no longer unique on its own (WTUR
and WROT are each reused for a second, numerically distinct Hub Controller
group — docs/06-data-dictionary.md §9), any client input that identifies a
Functional System Group (or, for the same reason of future-proofing against
Administrator-created subgroups with colliding names across groups, a
Functional Subgroup) is resolved by its unique surrogate **id**, not by its
`code` string — see `get_by_id` below. This is a deliberate interpretation
of a real gap in the v3 API spec, which still shows a bare `code` string as
the example value for these fields without addressing the ambiguity it
itself warns implementers about ("always resolve a group by its numeric
range, never by prefix alone"). All other vocabularies keep genuinely
unique codes and are still resolved by `get_by_code`."""

from typing import TypeVar

from app.extensions import Base, db
from app.models.lookup import (
    LookupAvailableGroup,
    LookupControllerSoftwareVersion,
    LookupCustomerAccess,
    LookupDevelopmentAccess,
    LookupEngineeringDomain,
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
    LookupGridOperatorAccess,
    LookupLanguage,
    LookupSalesAccess,
    LookupServiceAccess,
    LookupServicePartnerAccess,
    LookupTccAccess,
    LookupTopAccess,
    LookupTurbinePlatform,
)

VOCABULARY_MODELS: dict[str, type[Base]] = {
    "functional-system-groups": LookupFunctionalSystemGroup,
    "functional-subgroups": LookupFunctionalSubgroup,
    "turbine-platforms": LookupTurbinePlatform,
    "engineering-domains": LookupEngineeringDomain,
    "available-groups": LookupAvailableGroup,
    "development-access": LookupDevelopmentAccess,
    "sales-access": LookupSalesAccess,
    "tcc-access": LookupTccAccess,
    "service-access": LookupServiceAccess,
    "turbine-operator-package-access": LookupTopAccess,
    "grid-operator-access": LookupGridOperatorAccess,
    "service-partner-access": LookupServicePartnerAccess,
    "customer-access": LookupCustomerAccess,
    "controller-software-versions": LookupControllerSoftwareVersion,
    "languages": LookupLanguage,
}

LookupT = TypeVar("LookupT", bound=Base)


class LookupService:
    @staticmethod
    def list_vocabulary(
        vocabulary: str, functional_system_group_id: int | None = None
    ) -> list[Base]:
        model = VOCABULARY_MODELS.get(vocabulary)
        if model is None:
            raise ValueError(f"Unknown vocabulary: {vocabulary}")

        query = db.session.query(model).filter(model.is_active == 1)  # type: ignore[attr-defined]
        if model is LookupFunctionalSubgroup:
            if not functional_system_group_id:
                raise ValueError(
                    "functional_system_group query parameter is required for functional-subgroups"
                )
            query = query.filter(
                LookupFunctionalSubgroup.functional_system_group_id == functional_system_group_id
            )
        return list(query.order_by(model.sort_order).all())  # type: ignore[attr-defined]

    @staticmethod
    def get_by_code(model: type[LookupT], code) -> LookupT:
        """Resolves an API-facing lookup code (e.g. "3XM") to its active row.
        Not used for LookupFunctionalSystemGroup/LookupFunctionalSubgroup —
        see the module docstring; use get_by_id for those."""
        obj = (
            db.session.query(model)
            .filter(model.code == code, model.is_active == 1)  # type: ignore[attr-defined]
            .first()
        )
        if obj is None:
            raise ValueError(f"Unknown or inactive {model.__name__} code: {code}")
        return obj

    @staticmethod
    def get_by_id(model: type[LookupT], value_id) -> LookupT:
        """Resolves a lookup row by its surrogate id, raising the same kind
        of ValueError as get_by_code on a missing/invalid/inactive row, so
        callers can treat both the same way (e.g. surfacing a 422)."""
        try:
            parsed_id = int(value_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid {model.__name__} id: {value_id!r}") from exc
        obj = db.session.get(model, parsed_id)
        if obj is None or not obj.is_active:  # type: ignore[attr-defined]
            raise ValueError(f"Unknown or inactive {model.__name__} id: {value_id}")
        return obj

"""Read-only controlled-vocabulary listings and code-resolution helper used
by every other service. See docs/artifacts/openapi.yaml /lookups/{vocabulary}
and docs/06-data-dictionary.md §9."""

from typing import TypeVar

from app.extensions import Base, db
from app.models.lookup import (
    LookupAccessRights,
    LookupAlarmBehaviour,
    LookupAvailabilityGroup,
    LookupBrakeProgram,
    LookupEngineeringDomain,
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
    LookupOperationalState,
    LookupResetProgram,
    LookupStatusCategory,
    LookupTurbinePlatform,
)

VOCABULARY_MODELS: dict[str, type[Base]] = {
    "functional-system-groups": LookupFunctionalSystemGroup,
    "functional-subgroups": LookupFunctionalSubgroup,
    "turbine-platforms": LookupTurbinePlatform,
    "engineering-domains": LookupEngineeringDomain,
    "status-categories": LookupStatusCategory,
    "availability-groups": LookupAvailabilityGroup,
    "brake-programs": LookupBrakeProgram,
    "reset-programs": LookupResetProgram,
    "operational-states": LookupOperationalState,
    "access-rights": LookupAccessRights,
    "alarm-behaviours": LookupAlarmBehaviour,
}

LookupT = TypeVar("LookupT", bound=Base)


class LookupService:
    @staticmethod
    def list_vocabulary(
        vocabulary: str, functional_system_group_code: str | None = None
    ) -> list[Base]:
        model = VOCABULARY_MODELS.get(vocabulary)
        if model is None:
            raise ValueError(f"Unknown vocabulary: {vocabulary}")

        query = db.session.query(model).filter(model.is_active == 1)  # type: ignore[attr-defined]
        if model is LookupFunctionalSubgroup:
            if not functional_system_group_code:
                raise ValueError(
                    "functional_system_group query parameter is required for functional-subgroups"
                )
            group = LookupService.get_by_code(
                LookupFunctionalSystemGroup, functional_system_group_code
            )
            query = query.filter(LookupFunctionalSubgroup.functional_system_group_id == group.id)
        return list(query.order_by(model.sort_order).all())  # type: ignore[attr-defined]

    @staticmethod
    def get_by_code(model: type[LookupT], code: str) -> LookupT:
        """Resolves an API-facing lookup code (e.g. "WCNV") to its active row.
        Every other service uses this rather than querying lookups directly."""
        obj = (
            db.session.query(model)
            .filter(model.code == code, model.is_active == 1)  # type: ignore[attr-defined]
            .first()
        )
        if obj is None:
            raise ValueError(f"Unknown or inactive {model.__name__} code: {code}")
        return obj

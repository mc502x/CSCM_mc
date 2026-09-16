"""Atomic Functional Group/Subgroup identifier allocation. See
docs/07-database-design.md §7a. Every call must run inside the caller's own
service-method transaction (no intermediate commit before or after) —
race-safety comes from the `begin` event listener in app/__init__.py making
every transaction BEGIN IMMEDIATE, not from anything in this module itself."""

from sqlalchemy import text

from app.domain.errors import DomainError
from app.extensions import db
from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup

_REAL_PREFIX_LEN = len("StCd-")
_SANDBOX_PREFIX_LEN = len("StCd-T")
_SANDBOX_RANGE_START = 0
_SANDBOX_RANGE_END = 99999


class CapacityExhaustedError(DomainError):
    """FR-025: allocation beyond a (sub)range's upper bound raises this
    rather than overflowing into a neighboring group."""


class NumberingService:
    @staticmethod
    def allocate_next_identifier(
        functional_system_group_id: int, functional_subgroup_id: int | None
    ) -> str:
        """Returns e.g. 'StCd-01233'. functional_subgroup_id, if given,
        narrows the range to that subgroup's sub-band instead of the whole
        group's range."""
        range_start, range_end = _resolve_range(functional_system_group_id, functional_subgroup_id)

        current_max = db.session.execute(
            text(
                "SELECT MAX(CAST(SUBSTR(status_code_identifier, :offset) AS INTEGER)) "
                "FROM status_code "
                "WHERE functional_system_group_id = :group_id "
                "AND status_code_identifier IS NOT NULL "
                "AND CAST(SUBSTR(status_code_identifier, :offset) AS INTEGER) "
                "BETWEEN :range_start AND :range_end"
            ),
            {
                "offset": _REAL_PREFIX_LEN + 1,
                "group_id": functional_system_group_id,
                "range_start": range_start,
                "range_end": range_end,
            },
        ).scalar()

        next_number = (range_start - 1 if current_max is None else current_max) + 1
        if next_number > range_end:
            raise CapacityExhaustedError(
                f"Numbering range {range_start}-{range_end} is exhausted; "
                "Controls Engineering must open a new (sub)range."
            )
        return f"StCd-{next_number:05d}"

    @staticmethod
    def allocate_next_sandbox_identifier() -> str:
        """Draws from the isolated StCd-T##### band; never touches a real
        Functional System Group range (FR-053)."""
        current_max = db.session.execute(
            text(
                "SELECT MAX(CAST(SUBSTR(status_code_identifier, :offset) AS INTEGER)) "
                "FROM status_code WHERE status_code_identifier LIKE 'StCd-T%'"
            ),
            {"offset": _SANDBOX_PREFIX_LEN + 1},
        ).scalar()
        next_number = (_SANDBOX_RANGE_START - 1 if current_max is None else current_max) + 1
        if next_number > _SANDBOX_RANGE_END:
            raise CapacityExhaustedError(
                "Sandbox identifier band StCd-T00000..T99999 is exhausted."
            )
        return f"StCd-T{next_number:05d}"

    @staticmethod
    def preview_next_identifier(
        functional_system_group_id: int, functional_subgroup_id: int | None
    ) -> str:
        """Non-binding preview (FR-021/US-023) — identical computation, but
        the caller must not persist anything: no number is reserved by
        calling this, and a concurrent Submit-for-Review may claim it first."""
        return NumberingService.allocate_next_identifier(
            functional_system_group_id, functional_subgroup_id
        )


def _resolve_range(
    functional_system_group_id: int, functional_subgroup_id: int | None
) -> tuple[int, int]:
    if functional_subgroup_id is not None:
        subgroup = db.session.get(LookupFunctionalSubgroup, functional_subgroup_id)
        if subgroup is None:
            raise ValueError(f"Unknown functional_subgroup_id: {functional_subgroup_id}")
        return subgroup.sub_range_start, subgroup.sub_range_end

    group = db.session.get(LookupFunctionalSystemGroup, functional_system_group_id)
    if group is None:
        raise ValueError(f"Unknown functional_system_group_id: {functional_system_group_id}")
    return group.range_start, group.range_end

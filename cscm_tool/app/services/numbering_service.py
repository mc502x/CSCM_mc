"""Atomic Functional Group/Subgroup identifier allocation. See
docs/07-database-design.md §7a. Every call must run inside the caller's own
service-method transaction (no intermediate commit before or after) —
race-safety comes from the `begin` event listener in app/__init__.py making
every transaction BEGIN IMMEDIATE, not from anything in this module itself."""

import re

from sqlalchemy import text

from app.domain.errors import DomainError
from app.extensions import db
from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup

_REAL_PREFIX_LEN = len("StCd-")
_REAL_IDENTIFIER_RE = re.compile(r"^StCd-\d{5}$")
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
        current_max = _current_max(functional_system_group_id, range_start, range_end)

        next_number = (range_start - 1 if current_max is None else current_max) + 1
        # A number an imported program already carries is reserved for that code (v4.2).
        reserved = _reserved_numbers(next_number, range_end)
        while next_number in reserved:
            next_number += 1
        if next_number > range_end:
            raise CapacityExhaustedError(
                f"Numbering range {range_start}-{range_end} is exhausted; "
                "Controls Engineering must open a new (sub)range."
            )
        return f"StCd-{next_number:05d}"

    @staticmethod
    def capacity(functional_system_group_id: int, functional_subgroup_id: int | None) -> dict:
        """How full a (sub)range is (I-19). Numbers are never reused (BR-001), so
        `remaining` counts from the highest number handed out, not from the count of
        codes: a gap left by a withdrawn draft is not available again."""
        range_start, range_end = _resolve_range(functional_system_group_id, functional_subgroup_id)
        current_max = _current_max(functional_system_group_id, range_start, range_end)
        allocated = db.session.execute(
            text(
                "SELECT COUNT(*) FROM status_code "
                "WHERE functional_system_group_id = :group_id "
                "AND status_code_identifier GLOB 'StCd-[0-9]*' "
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
        last = range_start - 1 if current_max is None else current_max
        total = range_end - range_start + 1
        return {
            "range_start": range_start,
            "range_end": range_end,
            "total": total,
            "allocated": int(allocated or 0),
            "highest_allocated": current_max,
            "remaining": range_end - last,
            "percent_remaining": round(100 * (range_end - last) / total, 1),
        }

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
    def validate_manual_identifier(
        identifier: str,
        functional_system_group_id: int,
        functional_subgroup_id: int | None,
        status_code_id: int | None = None,
    ) -> str:
        """FR-021a: an Administrator-chosen out-of-sequence identifier must
        be well-formed, fall inside the subgroup's sub-band, and not already
        be allocated (BR-001, numbers are never reused)."""
        if not _REAL_IDENTIFIER_RE.match(identifier or ""):
            raise ValueError("Identifier override must match StCd-NNNNN (five digits).")
        number = int(identifier[_REAL_PREFIX_LEN:])
        range_start, range_end = _resolve_range(functional_system_group_id, functional_subgroup_id)
        if not range_start <= number <= range_end:
            raise ValueError(
                f"Identifier override {identifier} lies outside the permitted range "
                f"StCd-{range_start:05d}..StCd-{range_end:05d}."
            )
        taken = db.session.execute(
            text("SELECT 1 FROM status_code WHERE status_code_identifier = :i"),
            {"i": identifier},
        ).first()
        if taken is not None:
            raise ValueError(f"Identifier {identifier} is already allocated.")
        reserved_by = db.session.execute(
            text("SELECT id FROM status_code WHERE reserved_identifier = :i AND id IS NOT :own"),
            {"i": identifier, "own": status_code_id},
        ).first()
        if reserved_by is not None:
            raise ValueError(f"Identifier {identifier} is reserved by an imported status code.")
        return identifier

    @staticmethod
    def validate_reserved_identifier(
        identifier: str,
        functional_system_group_id: int,
        functional_subgroup_id: int | None,
        status_code_id: int,
    ) -> str:
        """The number an imported program carries is issued as it is; it only has to be
        well-formed, inside the subgroup's band and not issued to another code meanwhile."""
        return NumberingService.validate_manual_identifier(
            identifier, functional_system_group_id, functional_subgroup_id, status_code_id
        )

    @staticmethod
    def band_of(number: int) -> tuple[int, int] | None:
        """(group id, subgroup id) of the subgroup whose band holds `number`; None if no active
        subgroup covers it. Used by the status code import to place a program by its number."""
        row = db.session.execute(
            text(
                "SELECT s.functional_system_group_id, s.id FROM lookup_functional_subgroup s "
                "JOIN lookup_functional_system_group g ON g.id = s.functional_system_group_id "
                "WHERE s.is_active = 1 AND g.is_active = 1 "
                "AND :n BETWEEN s.sub_range_start AND s.sub_range_end ORDER BY s.id LIMIT 1"
            ),
            {"n": number},
        ).first()
        return (row[0], row[1]) if row else None

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


def _reserved_numbers(first: int, last: int) -> set[int]:
    rows = db.session.execute(
        text(
            "SELECT CAST(SUBSTR(reserved_identifier, :offset) AS INTEGER) FROM status_code "
            "WHERE reserved_identifier IS NOT NULL "
            "AND CAST(SUBSTR(reserved_identifier, :offset) AS INTEGER) BETWEEN :a AND :b"
        ),
        {"offset": _REAL_PREFIX_LEN + 1, "a": first, "b": last},
    ).all()
    return {int(r[0]) for r in rows}


def _current_max(functional_system_group_id: int, range_start: int, range_end: int) -> int | None:
    return db.session.execute(
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

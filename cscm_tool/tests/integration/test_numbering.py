"""docs/07-database-design.md §7a: atomic Functional Group/Subgroup allocation."""

import pytest

from app.extensions import db
from app.models.lookup import LookupFunctionalSystemGroup
from app.services.numbering_service import CapacityExhaustedError, NumberingService


def test_first_allocation_in_a_group_starts_at_range_start(app):
    with app.app_context():
        group = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(LookupFunctionalSystemGroup.code == "WCNV")
            .one()
        )
        identifier = NumberingService.allocate_next_identifier(group.id, None)
        assert identifier == "StCd-01000"


def test_allocation_increments_and_persists(app):
    with app.app_context():
        group = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(LookupFunctionalSystemGroup.code == "WGEN")
            .one()
        )
        first = NumberingService.allocate_next_identifier(group.id, None)
        _persist_status_code(group.id, first)

        second = NumberingService.allocate_next_identifier(group.id, None)
        assert second == "StCd-02001"


def test_capacity_exhaustion_raises(app):
    with app.app_context():
        group = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(LookupFunctionalSystemGroup.code == "WROT")
            .one()
        )
        # Fabricate an identifier at the top of the range to force exhaustion
        # without actually allocating 1000 codes.
        _persist_status_code(group.id, f"StCd-{group.range_end:05d}")

        with pytest.raises(CapacityExhaustedError):
            NumberingService.allocate_next_identifier(group.id, None)


def test_sandbox_allocation_never_collides_with_real_range(app):
    with app.app_context():
        identifier = NumberingService.allocate_next_sandbox_identifier()
        assert identifier == "StCd-T00000"


def _persist_status_code(group_id: int, identifier: str) -> None:
    from app.models.status_code import StatusCode
    from app.models.user import User
    from app.utils import utcnow_iso

    owner = db.session.query(User).first()
    if owner is None:
        from app.auth.password import hash_password

        owner = User(
            username="fixture-owner",
            email="fixture-owner@example.com",
            password_hash=hash_password("a genuinely long passphrase"),
            full_name="Fixture Owner",
            role_id=2,
            created_at=utcnow_iso(),
        )
        db.session.add(owner)
        db.session.flush()

    db.session.add(
        StatusCode(
            status_code_identifier=identifier,
            functional_system_group_id=group_id,
            owner_id=owner.id,
            created_at=utcnow_iso(),
        )
    )
    db.session.commit()

"""TC-001 / TC-002 / BR-004: the 7-state lifecycle and its guard."""

import itertools

import pytest

from app.domain.errors import InvalidTransitionError
from app.domain.lifecycle import STATES, TRANSITIONS, assert_valid_transition, is_valid_transition
from app.extensions import db
from app.models.status_code import StatusCodeRevision
from tests.helpers import create_draft, make_cast

VALID = {(old, new) for old, targets in TRANSITIONS.items() for new in targets}


def test_there_are_exactly_seven_states():
    assert len(STATES) == 7
    assert set(TRANSITIONS) == set(STATES)


@pytest.mark.parametrize("old,new", sorted(VALID))
def test_every_defined_transition_is_accepted(old, new):
    assert is_valid_transition(old, new)
    assert_valid_transition(old, new)  # does not raise


@pytest.mark.parametrize("old,new", sorted(set(itertools.product(STATES, STATES)) - VALID))
def test_every_other_pairwise_transition_is_rejected(old, new):
    assert not is_valid_transition(old, new)
    with pytest.raises(InvalidTransitionError):
        assert_valid_transition(old, new)


def test_terminal_and_gated_states_cannot_be_skipped():
    # BR-004: Released only via Approved; Approved only via PendingApproval.
    assert not is_valid_transition("DRAFT", "APPROVED")
    assert not is_valid_transition("REVIEW", "APPROVED")
    assert not is_valid_transition("DRAFT", "RELEASED")
    assert not is_valid_transition("PENDING_APPROVAL", "RELEASED")
    assert TRANSITIONS["ARCHIVED"] == frozenset()


def test_orm_guard_blocks_an_illegal_status_assignment(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, _ = create_draft(app, client, cast, wcnv_ids)
    with app.app_context():
        row = db.session.get(StatusCodeRevision, revision["id"])
        with pytest.raises(InvalidTransitionError):
            row.lifecycle_status = "APPROVED"  # Draft -> Approved skips the governance
        db.session.rollback()
        row = db.session.get(StatusCodeRevision, revision["id"])
        row.lifecycle_status = "REVIEW"  # legal
        db.session.rollback()

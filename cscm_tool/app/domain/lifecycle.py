"""The 7-state revision lifecycle (docs/05-governance-handbook.md §3, BR-004).

Every status change on a `StatusCodeRevision` is checked against TRANSITIONS
at attribute-set time, so no service (or future code path) can move a
revision along an edge the governance model does not define."""

from sqlalchemy import event
from sqlalchemy.orm.base import NEVER_SET, NO_VALUE

from app.domain.errors import InvalidTransitionError
from app.models.status_code import StatusCodeRevision

STATES = (
    "DRAFT",
    "REVIEW",
    "PENDING_APPROVAL",
    "APPROVED",
    "RELEASED",
    "DEPRECATED",
    "ARCHIVED",
)

TRANSITIONS: dict[str, frozenset[str]] = {
    # Submit for Review (FR-031)
    "DRAFT": frozenset({"REVIEW"}),
    # Both sign-offs recorded -> PendingApproval (FR-035); any rejection -> Draft (FR-033/034)
    "REVIEW": frozenset({"PENDING_APPROVAL", "DRAFT"}),
    # Chief Engineer approves (-> Approved, or -> Deprecated for a deprecation CR) or rejects
    "PENDING_APPROVAL": frozenset({"APPROVED", "DEPRECATED", "DRAFT"}),
    # Included in a published Release (FR-043)
    "APPROVED": frozenset({"RELEASED"}),
    # Superseding/deprecating a Released code is a new revision (copy-on-write);
    # the Released revision itself is left untouched (BR-007).
    "RELEASED": frozenset(),
    # Archive after the retention period (BR-006), or exceptional reinstatement
    "DEPRECATED": frozenset({"ARCHIVED", "RELEASED"}),
    "ARCHIVED": frozenset(),
}


def is_valid_transition(old: str, new: str) -> bool:
    return new in TRANSITIONS.get(old, frozenset())


def assert_valid_transition(old: str, new: str) -> None:
    if not is_valid_transition(old, new):
        raise InvalidTransitionError(f"Invalid lifecycle transition {old} -> {new}.")


def register_lifecycle_guard() -> None:
    """Idempotent: safe to call from every create_app()."""
    if event.contains(StatusCodeRevision.lifecycle_status, "set", _guard):
        return
    event.listen(StatusCodeRevision.lifecycle_status, "set", _guard, active_history=True)


def _guard(target, value, oldvalue, initiator):
    if oldvalue in (NO_VALUE, NEVER_SET, None) or oldvalue == value:
        return
    assert_valid_transition(oldvalue, value)

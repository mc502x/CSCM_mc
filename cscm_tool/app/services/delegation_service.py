"""Delegation and out-of-office cover for the decision roles (I-16, decision D-08).

A Reviewer, Administrator or Chief Engineer names a delegate for a date range. The
delegate acts *as themselves*: the audit trail names the delegate as actor and records
`on_behalf_of`, and every segregation-of-duties rule keeps applying to the delegate
personally (they cannot decide a CR they wrote or already signed, and the two Review
sign-offs must still come from two different people). Delegation grants the *decision
actions* of the delegated role only (reviewer sign-off, administrator sign-off, Chief
Engineer decision and the matching queues) - never user administration or any other
Administrator privilege."""

from datetime import UTC, date, datetime

from app.domain.errors import ForbiddenError, NotFoundError
from app.extensions import db
from app.models.operations import Delegation
from app.models.user import User
from app.services.audit_service import AuditService
from app.utils import utcnow_iso

DELEGABLE_ROLES = ("REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER")


def _parse_day(value: str | None, field: str) -> str:
    try:
        return date.fromisoformat(value or "").isoformat()
    except ValueError as exc:
        raise ValueError(f"{field} must be a date like 2027-03-31.") from exc


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


class DelegationService:
    @staticmethod
    def create(
        delegator_id: int, delegate_id: int, valid_from: str, valid_to: str, actor
    ) -> Delegation:
        delegator = db.session.get(User, delegator_id)
        delegate = db.session.get(User, delegate_id)
        if delegator is None or delegate is None:
            raise NotFoundError("User not found")
        if actor.id != delegator.id and actor.role_code != "ADMINISTRATOR":
            raise ForbiddenError("Only the delegator or an Administrator may create a delegation.")
        if delegator.role.code not in DELEGABLE_ROLES:
            raise ValueError("Only Reviewers, Administrators and Chief Engineers can delegate.")
        if delegate.id == delegator.id:
            raise ValueError("You cannot delegate to yourself.")
        if not delegate.is_active or delegate.role.code == "VIEWER":
            raise ValueError("The delegate must be an active user who is not a Viewer.")
        start = _parse_day(valid_from, "valid_from")
        end = _parse_day(valid_to, "valid_to")
        if end < start:
            raise ValueError("valid_to must not be before valid_from.")
        if end < _today():
            raise ValueError("The delegation period has already ended.")

        delegation = Delegation(
            delegator_id=delegator.id,
            delegate_id=delegate.id,
            role_code=delegator.role.code,
            valid_from=start,
            valid_to=end,
            created_by=actor.id,
            created_at=utcnow_iso(),
        )
        db.session.add(delegation)
        db.session.flush()
        AuditService.log(
            "Delegation",
            delegation.id,
            "DELEGATION_CREATE",
            actor=actor,
            after={
                "delegator_id": delegator.id,
                "delegate_id": delegate.id,
                "role": delegation.role_code,
                "valid_from": start,
                "valid_to": end,
            },
        )
        db.session.commit()
        return delegation

    @staticmethod
    def revoke(delegation_id: int, actor) -> Delegation:
        delegation = db.session.get(Delegation, delegation_id)
        if delegation is None:
            raise NotFoundError("Delegation not found")
        if actor.id != delegation.delegator_id and actor.role_code != "ADMINISTRATOR":
            raise ForbiddenError("Only the delegator or an Administrator may revoke a delegation.")
        if delegation.revoked_at is None:
            delegation.revoked_at = utcnow_iso()
            AuditService.log(
                "Delegation",
                delegation.id,
                "DELEGATION_REVOKE",
                actor=actor,
                after={"revoked": True},
            )
            db.session.commit()
        return delegation

    @staticmethod
    def list_for(actor, include_inactive: bool = False) -> list[Delegation]:
        query = db.session.query(Delegation)
        if actor.role_code != "ADMINISTRATOR":
            query = query.filter(
                (Delegation.delegator_id == actor.id) | (Delegation.delegate_id == actor.id)
            )
        if not include_inactive:
            query = query.filter(Delegation.revoked_at.is_(None), Delegation.valid_to >= _today())
        return query.order_by(Delegation.valid_from, Delegation.id).all()

    @staticmethod
    def _active_query(user_id: int, on: str | None = None):
        day = on or _today()
        return (
            db.session.query(Delegation)
            .join(User, User.id == Delegation.delegator_id)
            .filter(
                Delegation.delegate_id == user_id,
                Delegation.revoked_at.is_(None),
                Delegation.valid_from <= day,
                Delegation.valid_to >= day,
                User.is_active == 1,
            )
        )

    @staticmethod
    def active_roles_for(user_id: int, on: str | None = None) -> frozenset[str]:
        """Decision roles `user_id` may exercise today on someone's behalf."""
        return frozenset(d.role_code for d in DelegationService._active_query(user_id, on).all())

    @staticmethod
    def delegators_for(user_id: int, role_code: str, on: str | None = None) -> list[int]:
        return sorted(
            d.delegator_id
            for d in DelegationService._active_query(user_id, on).all()
            if d.role_code == role_code
        )

    @staticmethod
    def is_out_of_office(user_id: int, on: str | None = None) -> bool:
        """True while `user_id` has an active delegation of their own role to someone else."""
        day = on or _today()
        return (
            db.session.query(Delegation)
            .filter(
                Delegation.delegator_id == user_id,
                Delegation.revoked_at.is_(None),
                Delegation.valid_from <= day,
                Delegation.valid_to >= day,
            )
            .first()
            is not None
        )

    @staticmethod
    def delegates_of(user_id: int, on: str | None = None) -> list[int]:
        day = on or _today()
        return [
            d.delegate_id
            for d in db.session.query(Delegation)
            .filter(
                Delegation.delegator_id == user_id,
                Delegation.revoked_at.is_(None),
                Delegation.valid_from <= day,
                Delegation.valid_to >= day,
            )
            .all()
        ]


def require_decision_role(actor, role: str) -> None:
    """The decision-action version of `require_roles`: the actor holds `role`
    themselves or is covering for someone who does (I-16)."""
    if getattr(actor, "role_code", None) == role:
        return
    if role in getattr(actor, "delegated_role_codes", frozenset()):
        return
    raise ForbiddenError(f"SEC-010: this action requires the {role} role or a delegation of it.")

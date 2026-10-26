"""In-app notices and the daily SLA reminder (I-08).

`send_reminders()` (run by `flask send-reminders` from a scheduler) walks the CRs
that are waiting on a decision and, for each one past its amber/red threshold,
notifies whoever holds the *next* decision - plus anyone currently covering for
them (I-16). A notice is created at most once per user, CR, stage, level and day
(`dedupe_key`), so running the job twice is harmless. If an SMTP relay is
configured the same text is also mailed (MailService); otherwise the in-app
banner is the whole mechanism."""

from datetime import UTC, datetime

from sqlalchemy import func

from app.domain.errors import ForbiddenError, NotFoundError
from app.extensions import db
from app.models.change_request import ChangeRequest
from app.models.lookup import Role
from app.models.operations import Notification
from app.models.user import User
from app.services.delegation_service import DelegationService
from app.services.mail_service import MailService
from app.services.sla_service import SlaService
from app.utils import utcnow_iso


def _active_users(role_code: str) -> list[User]:
    return (
        db.session.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(Role.code == role_code, User.is_active == 1)
        .order_by(User.id)
        .all()
    )


def decision_holders(cr: ChangeRequest) -> list[User]:
    """Who can take the next decision on `cr` right now (and so should be reminded)."""
    revision = cr.revision
    holders: dict[int, User] = {}

    def add(user: User) -> None:
        if user.id != cr.requested_by:
            holders[user.id] = user

    state = revision.lifecycle_status
    if state == "REVIEW":
        if revision.reviewer_signoff_by is None:
            if cr.assigned_reviewer_id is not None:
                assigned = db.session.get(User, cr.assigned_reviewer_id)
                if assigned is not None and assigned.is_active:
                    add(assigned)
            else:
                for user in _active_users("REVIEWER"):
                    add(user)
        if revision.admin_signoff_by is None:
            for user in _active_users("ADMINISTRATOR"):
                add(user)
    elif state == "PENDING_APPROVAL":
        blocked = {cr.requested_by, revision.reviewer_signoff_by, revision.admin_signoff_by}
        for user in _active_users("CHIEF_ENGINEER"):
            if user.id not in blocked:
                add(user)

    # People covering for an absent holder are reminded too.
    for user in list(holders.values()):
        for delegate_id in DelegationService.delegates_of(user.id):
            delegate = db.session.get(User, delegate_id)
            if delegate is not None and delegate.is_active:
                add(delegate)
    return list(holders.values())


class NotificationService:
    @staticmethod
    def notify(
        user_id: int,
        kind: str,
        message: str,
        link: str | None = None,
        change_request_id: int | None = None,
        dedupe_key: str | None = None,
    ) -> Notification | None:
        if dedupe_key is not None and (
            db.session.query(Notification.id).filter(Notification.dedupe_key == dedupe_key).first()
        ):
            return None
        notice = Notification(
            user_id=user_id,
            kind=kind,
            message=message,
            link=link,
            change_request_id=change_request_id,
            dedupe_key=dedupe_key,
            created_at=utcnow_iso(),
        )
        db.session.add(notice)
        db.session.flush()
        return notice

    @staticmethod
    def send_reminders(now: datetime | None = None) -> dict:
        now = now or datetime.now(UTC)
        today = now.date().isoformat()
        created = emailed = 0
        for cr, info in SlaService.stalled(now):
            label = (
                cr.revision.status_code.status_code_identifier
                or f"draft #{cr.revision.status_code_id}"
            )
            action = "Review sign-off" if info["stage"] == "review" else "Chief Engineer approval"
            message = (
                f"CR #{cr.id} ({label} - {cr.revision.title}) has waited {info['age_days']} "
                f"business days for {action} ({info['level'].upper()})."
            )
            link = f"/change-requests/{cr.id}"
            for user in decision_holders(cr):
                key = f"sla:{cr.id}:{info['stage']}:{info['level']}:{today}:{user.id}"
                notice = NotificationService.notify(
                    user.id, "SLA_REMINDER", message, link, cr.id, key
                )
                if notice is None:
                    continue
                created += 1
                if MailService.enabled() and MailService.send(
                    user.email, f"[CSCM] CR #{cr.id} is waiting for you", f"{message}\n{link}\n"
                ):
                    notice.emailed_at = utcnow_iso()
                    emailed += 1
        db.session.commit()
        return {"created": created, "emailed": emailed}

    @staticmethod
    def list_for(user_id: int, unread_only: bool = False, limit: int = 100) -> list[Notification]:
        query = db.session.query(Notification).filter(Notification.user_id == user_id)
        if unread_only:
            query = query.filter(Notification.read_at.is_(None))
        return query.order_by(Notification.id.desc()).limit(limit).all()

    @staticmethod
    def unread_count(user_id: int) -> int:
        return int(
            db.session.query(func.count(Notification.id))
            .filter(Notification.user_id == user_id, Notification.read_at.is_(None))
            .scalar()
            or 0
        )

    @staticmethod
    def mark_read(notification_id: int, actor) -> Notification:
        notice = db.session.get(Notification, notification_id)
        if notice is None:
            raise NotFoundError("Notification not found")
        if notice.user_id != actor.id:
            raise ForbiddenError("This notification belongs to someone else.")
        if notice.read_at is None:
            notice.read_at = utcnow_iso()
            db.session.commit()
        return notice

    @staticmethod
    def mark_all_read(actor) -> int:
        updated = (
            db.session.query(Notification)
            .filter(Notification.user_id == actor.id, Notification.read_at.is_(None))
            .update({Notification.read_at: utcnow_iso()})
        )
        db.session.commit()
        return int(updated)

"""Login rate limiter backed by the database (I-20). docs/11-security-architecture.md §5:
10 attempts/IP/5min and 5 attempts/username/15min, enforced independently.

The counters used to live in process memory, so a restart cleared them and every worker
process kept its own. They are rows in `login_attempt` now: a restart keeps them and any
number of worker processes share them. The check-then-record runs inside the login
request's write transaction (BEGIN IMMEDIATE, app/__init__.py), which is what makes it
atomic across processes.

The caller must commit: AuthService.login does so on every path after recording."""

import time
from contextlib import suppress

from sqlalchemy import func

from app.extensions import db
from app.models.operations import LoginAttempt

_IP_WINDOW_SECONDS = 5 * 60
_IP_MAX_ATTEMPTS = 10
_USERNAME_WINDOW_SECONDS = 15 * 60
_USERNAME_MAX_ATTEMPTS = 5

_last_app = None  # test helper only, see reset_for_testing()


def remember_app(app) -> None:
    global _last_app
    _last_app = app


def _count(scope: str, key: str, window: int, now: float) -> int:
    return int(
        db.session.query(func.count(LoginAttempt.id))
        .filter(
            LoginAttempt.scope == scope,
            LoginAttempt.key == key,
            LoginAttempt.attempted_at > now - window,
        )
        .scalar()
        or 0
    )


def check_and_record_login_attempt(
    ip_address: str, username: str, now: float | None = None
) -> bool:
    """Records this attempt and returns False if either the IP or the
    username has exceeded its independent rate limit."""
    now = time.time() if now is None else now
    username_key = username.lower()

    # Rows older than the longest window can never matter again.
    db.session.query(LoginAttempt).filter(
        LoginAttempt.attempted_at <= now - max(_IP_WINDOW_SECONDS, _USERNAME_WINDOW_SECONDS)
    ).delete(synchronize_session=False)

    if (
        _count("IP", ip_address, _IP_WINDOW_SECONDS, now) >= _IP_MAX_ATTEMPTS
        or _count("USER", username_key, _USERNAME_WINDOW_SECONDS, now) >= _USERNAME_MAX_ATTEMPTS
    ):
        return False

    db.session.add(LoginAttempt(scope="IP", key=ip_address, attempted_at=now))
    db.session.add(LoginAttempt(scope="USER", key=username_key, attempted_at=now))
    db.session.flush()
    return True


def reset_for_testing() -> None:
    """Test-only helper: forget every recorded attempt of the most recently created app."""
    app = _last_app
    if app is None:
        return
    with suppress(Exception), app.app_context():  # the app's database may be gone between tests
        try:
            db.session.query(LoginAttempt).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

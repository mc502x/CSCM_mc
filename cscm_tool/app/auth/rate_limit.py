"""In-process sliding-window login rate limiter. docs/11-security-
architecture.md §5: 10 attempts/IP/5min and 5 attempts/username/15min,
enforced independently. In-memory is sufficient for the single-process
on-premises MVP deployment (08-system-architecture.md §1); a multi-process
deployment would need a shared store instead — noted here, not built,
since MVP scope is a single application server."""

import threading
import time
from collections import defaultdict, deque

_IP_WINDOW_SECONDS = 5 * 60
_IP_MAX_ATTEMPTS = 10
_USERNAME_WINDOW_SECONDS = 15 * 60
_USERNAME_MAX_ATTEMPTS = 5

_lock = threading.Lock()
_ip_attempts: dict[str, deque] = defaultdict(deque)
_username_attempts: dict[str, deque] = defaultdict(deque)


def _prune(attempts: deque, window_seconds: int, now: float) -> None:
    while attempts and now - attempts[0] > window_seconds:
        attempts.popleft()


def check_and_record_login_attempt(ip_address: str, username: str) -> bool:
    """Records this attempt and returns False if either the IP or the
    username has exceeded its independent rate limit."""
    now = time.monotonic()
    with _lock:
        ip_deque = _ip_attempts[ip_address]
        username_deque = _username_attempts[username.lower()]
        _prune(ip_deque, _IP_WINDOW_SECONDS, now)
        _prune(username_deque, _USERNAME_WINDOW_SECONDS, now)

        if len(ip_deque) >= _IP_MAX_ATTEMPTS or len(username_deque) >= _USERNAME_MAX_ATTEMPTS:
            return False

        ip_deque.append(now)
        username_deque.append(now)
        return True


def reset_for_testing() -> None:
    """Test-only helper; each test otherwise shares this module's global state."""
    with _lock:
        _ip_attempts.clear()
        _username_attempts.clear()

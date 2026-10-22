"""Per-request SQLite transaction mode (see the `begin` listener in
app/__init__.py)."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import g, has_request_context, request

_READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def is_read_only_request() -> bool:
    """True when the current request may use a deferred (read) transaction."""
    if not has_request_context():
        return False  # CLI, migrations, tests, background work: always take the write lock
    return request.method in _READ_METHODS and not g.get("writes_on_get", False)


def writes_on_get(view: Callable[..., Any]) -> Callable[..., Any]:
    """Marks a GET endpoint that writes (e.g. an export, which records an
    ExportJob and an audit entry) so its transaction takes the write lock up
    front like any other writer. Apply as the OUTERMOST decorator so the flag
    is set before the first database access (authentication)."""

    @wraps(view)
    def wrapper(*args: Any, **kwargs: Any):
        g.writes_on_get = True
        return view(*args, **kwargs)

    return wrapper

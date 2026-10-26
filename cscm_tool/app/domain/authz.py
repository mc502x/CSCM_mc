"""Service-layer authorization (SEC-010).

Route decorators are the first gate; every role-restricted service entry
point repeats the check so no future caller (a new route, a CLI command, a
background job) can reach a privileged operation by forgetting a decorator."""

from app.domain.errors import ForbiddenError


def require_roles(actor, *roles: str) -> None:
    role_code = getattr(actor, "role_code", None)
    if role_code not in roles:
        raise ForbiddenError(f"SEC-010: this action requires one of: {', '.join(roles)}.")

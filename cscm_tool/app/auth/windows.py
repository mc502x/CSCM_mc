"""Windows sign-in (docs/03-srs.md FR-163, docs/11-security-architecture.md SEC-033).

In a deployment people will not type a password: the organisation's gateway (IIS with Windows
authentication behind Application Request Routing, Apache with Kerberos, nginx with spnego, or
any other reverse proxy that authenticates against Active Directory) tells the application who
the browser's user is. This module is the application's side of that hand-over:

* `request_identity()` reads the identity - the header `WINDOWS_AUTH_HEADER` (default
  `X-Remote-User`) or the WSGI `REMOTE_USER` - and **believes it only when the request comes from
  one of `WINDOWS_AUTH_TRUSTED_PROXIES`**; from anywhere else the header is ignored, because anybody
  can send a header;
* `resolve_user()` matches the identity with an account by **e-mail address**: a user principal
  name (`name@corp.example`) is the address itself, a name with a domain in front (`CORP\\name`)
  becomes `name@WINDOWS_AUTH_EMAIL_DOMAIN` (or, without that setting, the user name). The address
  is why it cannot be changed (FR-162).
  Nobody is created on the fly: a Windows user without an active account is refused.

On a developer machine there is no gateway. `WINDOWS_AUTH_SIMULATE` shows a page that lets the
developer type the identity the gateway would have supplied; it then runs through exactly the same
code. The simulation is refused in production (app/__init__.py)."""

from __future__ import annotations

from flask import current_app, request, session

from app.extensions import db
from app.models.user import User

SIMULATED_KEY = "windows_sim_identity"


def mode() -> str:
    return str(current_app.config.get("AUTH_MODE", "password"))


def password_login_allowed() -> bool:
    return mode() in ("password", "both")


def windows_login_allowed() -> bool:
    return mode() in ("windows", "both")


def simulation_enabled() -> bool:
    return bool(current_app.config.get("WINDOWS_AUTH_SIMULATE")) and windows_login_allowed()


def _trusted_proxy() -> bool:
    return (request.remote_addr or "") in current_app.config.get("WINDOWS_AUTH_TRUSTED_PROXIES", ())


def request_identity() -> tuple[str | None, str]:
    """(identity, source) of the Windows user behind this request; source is `simulation`,
    `gateway` or `none`. A header from an address that is not a trusted proxy is not an identity."""
    if simulation_enabled() and session.get(SIMULATED_KEY):
        return str(session[SIMULATED_KEY]), "simulation"
    header = current_app.config.get("WINDOWS_AUTH_HEADER", "X-Remote-User")
    supplied = (request.headers.get(header) or request.environ.get("REMOTE_USER") or "").strip()
    if supplied and _trusted_proxy():
        return supplied, "gateway"
    if supplied:
        current_app.logger.warning(
            "ignored %s from %s: not a trusted proxy (WINDOWS_AUTH_TRUSTED_PROXIES)",
            header,
            request.remote_addr,
        )
    return None, "none"


def candidate_emails(identity: str) -> list[str]:
    """The addresses an identity can stand for. `name@domain` is itself one."""
    identity = identity.strip().lower()
    if "@" in identity and "\\" not in identity:
        return [identity]
    if "\\" in identity:
        name = identity.split("\\", 1)[1]
        domain = current_app.config.get("WINDOWS_AUTH_EMAIL_DOMAIN")
        return [f"{name}@{str(domain).lower()}"] if domain else []
    return []


def resolve_user(identity: str) -> User | None:
    """The account of a Windows identity, active or not (the caller decides what inactive means)."""
    for email in candidate_emails(identity):
        user = db.session.query(User).filter(db.func.lower(User.email) == email).first()
        if user is not None:
            return user
    if "\\" in identity:  # DOMAIN\name without a mail domain: the user name
        name = identity.split("\\", 1)[1].strip().lower()
        return db.session.query(User).filter(db.func.lower(User.username) == name).first()
    return None

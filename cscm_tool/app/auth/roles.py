"""The role catalogue: every role with its level, its colour and who may hand it out.

Six fixed roles (docs/11-security-architecture.md section 3). The *level* orders them by how much
they can do and is what the colour of a role badge shows: red is the highest. The role a person
holds is still decided by `user.role_id`; nothing here grants a right by itself - routes and
services check the role code explicitly (SEC-010) - this module only answers "which roles may
change which roles" (BR-024) and "how is a role drawn".

* **ADMINISTRATOR** - level 100, red. Creates users, assigns every role, owns the lookups and
  settings, builds and publishes Releases.
* **STCD_OWNER** - level 80. Owns the status code library: reads everything and may change the role
  of a user between VIEWER, ENGINEER and REVIEWER. Never creates users and has no say in the
  approval of status codes, so ownership and sign-off stay with different people - with one
  exception: a change of the legacy -> new mapping needs the approval of the StCd Owner, the
  Chief Engineer and an Administrator (BR-027).
* **CHIEF_ENGINEER** - level 60. The final approval.
* **REVIEWER** - level 40. Review sign-off.
* **ENGINEER** - level 30. Writes status codes.
* **VIEWER** - level 10. Reads released data.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleInfo:
    code: str
    label: str
    level: int
    css: str


ROLES: dict[str, RoleInfo] = {
    r.code: r
    for r in (
        RoleInfo("ADMINISTRATOR", "Administrator", 100, "administrator"),
        RoleInfo("STCD_OWNER", "StCd Owner", 80, "stcd-owner"),
        RoleInfo("CHIEF_ENGINEER", "Chief Engineer", 60, "chief-engineer"),
        RoleInfo("REVIEWER", "Reviewer", 40, "reviewer"),
        RoleInfo("ENGINEER", "Engineer", 30, "engineer"),
        RoleInfo("VIEWER", "Viewer", 10, "viewer"),
    )
}

# highest level first - the order roles are listed in
ROLE_CODES: tuple[str, ...] = tuple(sorted(ROLES, key=lambda c: -ROLES[c].level))

# The roles an StCd Owner may give and take away; every other role needs an Administrator.
OWNER_ASSIGNABLE: tuple[str, ...] = ("VIEWER", "ENGINEER", "REVIEWER")

# Roles that act in the review workflow, and those that may also read it (the StCd Owner oversees
# the library without being able to decide anything).
WORKING_ROLES: tuple[str, ...] = ("ADMINISTRATOR", "ENGINEER", "REVIEWER", "CHIEF_ENGINEER")
OVERSIGHT_ROLES: tuple[str, ...] = (*WORKING_ROLES, "STCD_OWNER")

# Who may open the user list and see the roles of the colleagues.
USER_LIST_ROLES: tuple[str, ...] = ("ADMINISTRATOR", "STCD_OWNER")


def role_info(code: str | None) -> RoleInfo:
    """The entry of a role; an unknown code is drawn as a plain, lowest-level badge."""
    return ROLES.get(code or "", RoleInfo(code or "?", code or "?", 0, "unknown"))


def assignable_roles(actor_role: str | None) -> tuple[str, ...]:
    """The roles an actor may give to somebody (BR-024)."""
    if actor_role == "ADMINISTRATOR":
        return ROLE_CODES
    if actor_role == "STCD_OWNER":
        return OWNER_ASSIGNABLE
    return ()


def may_change_role(actor_role: str | None, current_role: str, new_role: str) -> bool:
    """An Administrator changes any role. An StCd Owner changes a role only when the person holds
    one of the three roles now and gets one of them (so an Administrator, a Chief Engineer or
    another owner can never be touched, and nobody can be promoted past Reviewer)."""
    if actor_role == "ADMINISTRATOR":
        return True
    if actor_role == "STCD_OWNER":
        return current_role in OWNER_ASSIGNABLE and new_role in OWNER_ASSIGNABLE
    return False

"""The menu on the left (docs/10-ui-ux-specification.md section 3, FR-169).

The menu is data: groups of links, each link with the roles that see it, so that what a role
sees can be tested and the template only draws it. Titles and labels are interface text
(translated); the groups are collapsible and show how many items wait for the user."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func

ALL = ("VIEWER", "ENGINEER", "REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER", "STCD_OWNER")
WORKING = ("ENGINEER", "REVIEWER", "ADMINISTRATOR", "CHIEF_ENGINEER", "STCD_OWNER")


@dataclass(frozen=True)
class Item:
    endpoint: str
    label: str
    roles: tuple[str, ...] = ALL
    active: tuple[str, ...] = ()  # endpoints or prefixes ("ui.release") that light the link
    count: str | None = None  # key of nav_counts()
    needs: str | None = None  # a flag the template context provides (translation access)
    acts_as: tuple[str, ...] = ()  # a delegate may act as one of these roles


@dataclass(frozen=True)
class Group:
    key: str
    title: str
    items: tuple[Item, ...]
    parts: tuple[tuple[str, tuple[Item, ...]], ...] = field(default_factory=tuple)  # sub-blocks


MENU: tuple[Group, ...] = (
    Group(
        "home",
        "",
        (Item("ui.dashboard", "Dashboard", active=("ui.dashboard",)),),
    ),
    Group(
        "catalogue",
        "Catalogue",
        (
            Item(
                "ui.status_code_list",
                "Status Codes",
                active=("ui.status_code",),
            ),
            Item("ui.release_list", "Releases", active=("ui.release",)),
            Item("ui.export_center", "Export Center", active=("ui.export_center",)),
            Item(
                "ui.status_code_new_sandbox",
                "New Sandbox Code",
                roles=("ADMINISTRATOR",),
                active=("ui.status_code_new_sandbox",),
            ),
        ),
    ),
    Group(
        "workflow",
        "Workflow",
        (
            Item(
                "ui.my_change_requests",
                "My Change Requests",
                roles=WORKING,
                active=("ui.my_change_requests",),
                count="my_open_crs",
            ),
            Item(
                "ui.review_queue",
                "Review Queue",
                roles=("REVIEWER", "ADMINISTRATOR"),
                acts_as=("REVIEWER", "ADMINISTRATOR"),
                active=("ui.review_queue",),
                count="review_queue",
            ),
            Item(
                "ui.approval_queue",
                "Approval Queue",
                roles=("CHIEF_ENGINEER",),
                acts_as=("CHIEF_ENGINEER",),
                active=("ui.approval_queue",),
                count="approval_queue",
            ),
            Item("ui.change_set_list", "Change Sets", roles=WORKING, active=("ui.change_set",)),
            Item(
                "ui.delegations",
                "Delegation",
                roles=("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER"),
                active=("ui.delegations",),
            ),
        ),
    ),
    Group(
        "migration",
        "Import and Migration",
        (
            Item(
                "ui.import_new",
                "Library Import",
                roles=("ENGINEER", "ADMINISTRATOR"),
                active=("ui.import",),
            ),
            Item(
                "ui.st_import_new",
                "Import from .st files",
                roles=("ENGINEER", "ADMINISTRATOR"),
                active=("ui.st_import",),
            ),
            Item(
                "ui.legacy_mapping", "Legacy mapping", roles=WORKING, active=("ui.legacy_mapping",)
            ),
            Item(
                "ui.hub_consolidation",
                "Hub Consolidation",
                roles=WORKING,
                active=("ui.hub_consolidation",),
            ),
            Item(
                "ui.withdrawn_codes",
                "Withdrawn Codes",
                roles=("ADMINISTRATOR",),
                active=("ui.withdrawn_codes",),
                count="withdrawn",
            ),
        ),
    ),
    Group(
        "insight",
        "Insight",
        (
            Item(
                "ui.catalogue_health",
                "Catalogue Health",
                roles=("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER"),
                active=("ui.catalogue_health",),
            ),
            Item(
                "ui.stalled_requests",
                "Stalled Requests",
                roles=("ADMINISTRATOR",),
                active=("ui.stalled_requests",),
                count="stalled",
            ),
            Item(
                "ui.success_metrics",
                "Success Metrics",
                roles=("ADMINISTRATOR", "CHIEF_ENGINEER"),
                active=("ui.success_metrics",),
            ),
            Item(
                "ui.fleet_feedback",
                "Fleet Feedback",
                roles=("ADMINISTRATOR", "CHIEF_ENGINEER"),
                active=("ui.fleet_feedback",),
            ),
        ),
    ),
    Group(
        "languages",
        "Languages",
        (
            Item("ui.terminology_index", "Terminology", active=("ui.terminology",)),
            Item(
                "ui.translations_overview",
                "Translations",
                needs="translation_access",
                active=("ui.translation",),
            ),
        ),
    ),
    Group(
        "administration",
        "Administration",
        (),
        parts=(
            (
                "People",
                (
                    Item(
                        "ui.user_list",
                        "Users",
                        roles=("ADMINISTRATOR", "STCD_OWNER"),
                        active=("ui.user",),
                    ),
                ),
            ),
            (
                "Configuration",
                (
                    Item(
                        "ui.lookup_admin",
                        "Lookups",
                        roles=("ADMINISTRATOR",),
                        active=("ui.lookup_admin",),
                    ),
                    Item(
                        "ui.export_profiles",
                        "Export Profiles",
                        roles=("ADMINISTRATOR",),
                        active=("ui.export_profiles",),
                    ),
                    Item(
                        "ui.review_checklist",
                        "Review Checklist",
                        roles=("ADMINISTRATOR",),
                        active=("ui.review_checklist",),
                    ),
                    Item(
                        "ui.app_settings",
                        "Settings",
                        roles=("ADMINISTRATOR",),
                        active=("ui.app_settings",),
                    ),
                    Item(
                        "ui.integrations",
                        "Integrations",
                        roles=("ADMINISTRATOR",),
                        active=("ui.integrations",),
                    ),
                ),
            ),
            (
                "Operations",
                (
                    Item(
                        "ui.operations",
                        "Operations",
                        roles=("ADMINISTRATOR",),
                        active=("ui.operations",),
                    ),
                    Item(
                        "ui.audit_log",
                        "Audit Log",
                        roles=("ADMINISTRATOR", "REVIEWER", "CHIEF_ENGINEER"),
                        active=("ui.audit_log",),
                    ),
                ),
            ),
        ),
    ),
    Group("help", "", (Item("ui.help_page", "Help", active=("ui.help_page",)),)),
)

# everything the template takes from this module, for the translation inventory
LABELS: tuple[str, ...] = tuple(
    dict.fromkeys(
        [
            *(g.title for g in MENU if g.title),
            *(i.label for g in MENU for i in g.items),
            *(title for g in MENU for title, _items in g.parts),
            *(i.label for g in MENU for _title, items in g.parts for i in items),
            "Menu",
            "New Status Code",
        ]
    )
)


def _visible(item: Item, user, flags: dict) -> bool:
    if item.needs and not flags.get(item.needs):
        return False
    if user.role_code in item.roles:
        return True
    return any(user.can_act_as(role) for role in item.acts_as)


def is_active(item: Item, endpoint: str) -> bool:
    if item.endpoint == "ui.status_code_list" and endpoint in (
        "ui.status_code_new",
        "ui.status_code_new_sandbox",
    ):
        return False  # the New buttons light themselves
    return any(endpoint.startswith(prefix) for prefix in item.active)


# the counts that mean "something waits for you" (a group closed by the user still shows them)
WAITING = ("review_queue", "approval_queue", "stalled", "withdrawn")


def visible_menu(user, endpoint: str, flags: dict, counts: dict) -> list[dict]:
    """The groups the user sees: [{key, title, open, blocks: [{title, items: [...]}]}]."""
    groups = []
    for group in MENU:
        blocks: list[tuple[str, tuple[Item, ...]]] = []
        if group.items:
            blocks.append(("", group.items))
        blocks.extend(group.parts)
        shown: list[dict] = []
        for block_title, block_items in blocks:
            items = [
                {
                    "endpoint": i.endpoint,
                    "label": i.label,
                    "active": is_active(i, endpoint),
                    "count": counts.get(i.count) if i.count else None,
                    "count_key": i.count,
                }
                for i in block_items
                if _visible(i, user, flags)
            ]
            if items:
                shown.append({"title": block_title, "items": items})
        if not shown:
            continue
        groups.append(
            {
                "key": group.key,
                "title": group.title,
                "blocks": shown,
                "has_active": any(i["active"] for b in shown for i in b["items"]),
                "waiting": sum(
                    i["count"] or 0 for b in shown for i in b["items"] if i["count_key"] in WAITING
                ),
            }
        )
    return groups


def nav_counts(user) -> dict[str, int]:
    """How many items wait for the user, for the badges of the menu (never raises)."""
    from app.extensions import db
    from app.models.change_request import ChangeRequest
    from app.models.status_code import StatusCode, StatusCodeRevision

    counts: dict[str, int] = {}
    try:
        if user.role_code in ("ENGINEER", "ADMINISTRATOR"):
            counts["my_open_crs"] = (
                db.session.query(func.count(ChangeRequest.id))
                .filter(
                    ChangeRequest.requested_by == user.id,
                    ChangeRequest.state.in_(("DRAFT", "REVIEW", "PENDING_APPROVAL")),
                )
                .scalar()
                or 0
            )
        if user.can_act_as("REVIEWER") or user.can_act_as("ADMINISTRATOR"):
            base = (
                db.session.query(func.count(ChangeRequest.id))
                .join(
                    StatusCodeRevision,
                    ChangeRequest.status_code_revision_id == StatusCodeRevision.id,
                )
                .filter(
                    StatusCodeRevision.lifecycle_status == "REVIEW",
                    ChangeRequest.requested_by != user.id,
                )
            )
            counts["review_queue"] = (
                base.filter(
                    (StatusCodeRevision.reviewer_signoff_by.is_(None))
                    | (StatusCodeRevision.admin_signoff_by.is_(None))
                ).scalar()
                or 0
            )
        if user.can_act_as("CHIEF_ENGINEER"):
            counts["approval_queue"] = (
                db.session.query(func.count(StatusCodeRevision.id))
                .filter(StatusCodeRevision.lifecycle_status == "PENDING_APPROVAL")
                .scalar()
                or 0
            )
        if user.role_code == "ADMINISTRATOR":
            from app.services.sla_service import SlaService

            counts["stalled"] = len(SlaService.stalled())
            counts["withdrawn"] = (
                db.session.query(func.count(StatusCode.id))
                .filter(
                    StatusCode.is_sandbox == 0,
                    StatusCode.withdrawn_at.is_not(None),
                    StatusCode.deleted_at.is_(None),
                )
                .scalar()
                or 0
            )
    except Exception:  # noqa: BLE001 - a menu must never break a page
        return {}
    return counts

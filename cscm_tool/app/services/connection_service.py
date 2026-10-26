# ruff: noqa: E501  (docstring lines)
"""How status codes are connected (docs/10-ui-ux-specification.md section 10c, FR-179).

The generated programs (`StCd_<n>.st`) say more about a code than its own attributes: what it
depends on. Three kinds of connection are read from them (app/importers/stcd.py, a text reading, never
an interpretation of the controller logic):

* **suppressed by** - the set condition holds `NOT StatuscodeActiveArBo[StCd_x.Idx]`: the code is
  not raised while code x is active. x is the *cause*, this code a *consequence* that is silenced
  while its cause is present; chains of these are the nearest thing to a hierarchy the programs
  contain;
* **requires** - the code's active flag appears without a NOT: the code is only set while x is active;
* **escalates to** - the repeat code: when the code has been raised `MaxRepeatNb` times within
  `RepeatTime`, the program sets the repeat code instead of or as well. Most repeat codes lie in a pool
  outside the governed catalogue (9084, 9085 ...); those show as *external*.

The connections are derived on every request from what the import kept of each program
(`import_source_item.parsed_json`, the newest item of a code), so a re-import changes them and
nothing needs to be maintained by hand. A code that was not imported from a program has none."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func

from app.extensions import db
from app.importers import stcd
from app.models.import_job import ImportSourceItem
from app.models.lookup import LookupFunctionalSystemGroup
from app.models.status_code import StatusCode, StatusCodeRevision

SUPPRESSED_BY = "SUPPRESSED_BY"
REQUIRES = "REQUIRES"
ESCALATES_TO = "ESCALATES_TO"
KINDS = (SUPPRESSED_BY, REQUIRES, ESCALATES_TO)
MAX_DEPTH = 6
_DEAD = ("DEPRECATED", "ARCHIVED")


@dataclass(frozen=True)
class Link:
    source: int  # status_code id
    kind: str
    number: int  # the number the program names
    target: int | None  # status_code id when the number is in the catalogue


def _number_of(identifier: str | None) -> int | None:
    if identifier and identifier.startswith("StCd-") and identifier[5:].isdigit():
        return int(identifier[5:])
    return None


class ConnectionService:
    # ------------------------------------------------------------------ the raw material
    @staticmethod
    def nodes() -> dict[int, dict[str, Any]]:
        """Every governed code that has an identifier - or, as an imported Draft, the number it has
        reserved: id -> what the pages show of it."""
        identifier = func.coalesce(
            StatusCode.status_code_identifier, StatusCode.reserved_identifier
        )
        rows = (
            db.session.query(
                StatusCode.id,
                identifier,
                StatusCode.legacy_reference_number,
                LookupFunctionalSystemGroup.controller_type,
                LookupFunctionalSystemGroup.code,
                StatusCodeRevision.title,
                StatusCodeRevision.lifecycle_status,
            )
            .join(
                LookupFunctionalSystemGroup,
                LookupFunctionalSystemGroup.id == StatusCode.functional_system_group_id,
            )
            .outerjoin(
                StatusCodeRevision,
                (StatusCodeRevision.status_code_id == StatusCode.id)
                & (StatusCodeRevision.is_current == 1),
            )
            .filter(
                StatusCode.is_sandbox == 0,
                StatusCode.deleted_at.is_(None),
                identifier.isnot(None),
            )
            .all()
        )
        return {
            row[0]: {
                "id": row[0],
                "identifier": row[1],
                "number": _number_of(row[1]),
                "legacy": row[2],
                "controller": "HC" if row[3] == "HUB" else "MC",
                "group": row[4],
                "title": row[5] or "",
                "state": row[6] or "",
            }
            for row in rows
        }

    @staticmethod
    def links(nodes: dict[int, dict[str, Any]] | None = None) -> list[Link]:
        """All connections of the catalogue, from the newest import item of every code."""
        nodes = nodes if nodes is not None else ConnectionService.nodes()
        by_number: dict[int, int] = {}
        for node in nodes.values():
            if node["number"] is not None:
                by_number[node["number"]] = node["id"]
        by_legacy: dict[int, int] = {
            int(n["legacy"]): n["id"] for n in nodes.values() if str(n["legacy"] or "").isdigit()
        }

        def resolve(number: int) -> int | None:
            return by_number.get(number) or by_legacy.get(number)

        newest = (
            db.session.query(func.max(ImportSourceItem.id))
            .group_by(ImportSourceItem.status_code_id)
            .subquery()
        )
        items = (
            db.session.query(ImportSourceItem.status_code_id, ImportSourceItem.parsed_json)
            .filter(ImportSourceItem.id.in_(db.session.query(newest)))
            .all()
        )
        import json

        links: list[Link] = []
        for status_code_id, raw in items:
            if status_code_id not in nodes:
                continue
            parsed = json.loads(raw)
            if "suppressed_by" in parsed:
                suppressed, required = parsed["suppressed_by"], parsed.get("requires", [])
            else:  # imported before the programs were read for connections
                suppressed, required = stcd.condition_links(parsed.get("set_condition") or "")
            for number in suppressed:
                links.append(Link(status_code_id, SUPPRESSED_BY, number, resolve(number)))
            for number in required:
                links.append(Link(status_code_id, REQUIRES, number, resolve(number)))
            if parsed.get("repeat_code"):
                number = int(parsed["repeat_code"])
                links.append(Link(status_code_id, ESCALATES_TO, number, resolve(number)))
        return links

    # ------------------------------------------------------------------ one code
    @staticmethod
    def for_code(status_code_id: int) -> dict[str, Any]:
        """The connections of one code, both directions, with the chain of causes above it."""
        nodes = ConnectionService.nodes()
        links = ConnectionService.links(nodes)

        def view(link: Link, other: int | None, number: int) -> dict[str, Any]:
            node = nodes.get(other) if other is not None else None
            return {
                "kind": link.kind,
                "number": number,
                "code": node,
                "dead": bool(node and node["state"] in _DEAD),
                "external": node is None,
            }

        outgoing = [
            view(link, link.target, link.number) for link in links if link.source == status_code_id
        ]
        incoming = [
            view(link, link.source, nodes[link.source]["number"] or 0)
            for link in links
            if link.target == status_code_id and link.source in nodes
        ]

        def climb(start: int, kind: str) -> list[dict[str, Any]]:
            chain: list[dict[str, Any]] = []
            seen = {start}
            current = start
            for _ in range(MAX_DEPTH):
                step = next(
                    (
                        link
                        for link in links
                        if link.source == current and link.kind == kind and link.target
                    ),
                    None,
                )
                if step is None or step.target in seen or step.target is None:
                    break
                seen.add(step.target)
                chain.append(nodes[step.target])
                current = step.target
            return chain

        return {
            "outgoing": outgoing,
            "incoming": incoming,
            "causes": climb(status_code_id, SUPPRESSED_BY),
            "escalation": climb(status_code_id, ESCALATES_TO),
            "known": bool(outgoing or incoming),
        }

    # ------------------------------------------------------------------ the whole catalogue
    @staticmethod
    def hierarchy(controller: str | None = None) -> dict[str, Any]:
        """Causes with the consequences they suppress (a tree), where repeated codes escalate to,
        and what looks wrong: causes that are not in the catalogue, causes that are deprecated, loops.
        """
        nodes = ConnectionService.nodes()
        links = ConnectionService.links(nodes)
        if controller:
            allowed = {i for i, n in nodes.items() if n["controller"] == controller}
        else:
            allowed = set(nodes)

        children: dict[int, list[int]] = {}
        suppressed_ids: set[int] = set()
        findings: list[dict[str, Any]] = []
        for link in links:
            if link.source not in allowed:
                continue
            node = nodes[link.source]
            if link.kind == SUPPRESSED_BY:
                suppressed_ids.add(link.source)
                if link.target is None:
                    findings.append(
                        {
                            "type": "UNKNOWN_CAUSE",
                            "code": node,
                            "number": link.number,
                        }
                    )
                else:
                    children.setdefault(link.target, []).append(link.source)
                    if nodes[link.target]["state"] in _DEAD:
                        findings.append(
                            {"type": "DEAD_CAUSE", "code": node, "other": nodes[link.target]}
                        )
            elif link.kind == REQUIRES and link.target is None:
                findings.append(
                    {"type": "UNKNOWN_REQUIREMENT", "code": node, "number": link.number}
                )

        def tree(root: int, trail: tuple[int, ...]) -> dict[str, Any]:
            kids = sorted(
                children.get(root, []),
                key=lambda i: (nodes[i]["number"] or 0, i),
            )
            return {
                "code": nodes[root],
                "children": [
                    tree(k, (*trail, root))
                    for k in kids
                    if k not in trail and len(trail) < MAX_DEPTH
                ],
                "loop": [k for k in kids if k in trail],
            }

        roots = sorted(
            (r for r in children if r not in suppressed_ids and r in nodes),
            key=lambda i: (nodes[i]["number"] or 0, i),
        )
        trees = [tree(r, ()) for r in roots]
        # a cycle has no root: report the members of cycles that no tree reached
        reached: set[int] = set()

        def collect(branch: dict[str, Any]) -> None:
            reached.add(branch["code"]["id"])
            for child in branch["children"]:
                collect(child)

        for branch in trees:
            collect(branch)
        in_loops = sorted(
            (
                i
                for i in suppressed_ids
                if i in nodes and i not in reached and any(i in kids for kids in children.values())
            ),
            key=lambda i: (nodes[i]["number"] or 0, i),
        )
        for i in in_loops:
            findings.append({"type": "LOOP", "code": nodes[i]})

        targets: dict[int, dict[str, Any]] = {}
        for link in links:
            if link.kind != ESCALATES_TO or link.source not in allowed:
                continue
            entry = targets.setdefault(
                link.number,
                {
                    "number": link.number,
                    "code": nodes.get(link.target) if link.target else None,
                    "sources": [],
                },
            )
            entry["sources"].append(nodes[link.source])
            if entry["code"] and entry["code"]["state"] in _DEAD:
                findings.append(
                    {"type": "DEAD_ESCALATION", "code": nodes[link.source], "other": entry["code"]}
                )
        escalation = sorted(targets.values(), key=lambda e: (-len(e["sources"]), e["number"]))
        counts = {
            kind: sum(1 for link in links if link.kind == kind and link.source in allowed)
            for kind in KINDS
        }
        return {
            "trees": trees,
            "escalation": escalation,
            "findings": findings,
            "counts": counts,
            "codes_with_connections": len({k.source for k in links if k.source in allowed}),
        }

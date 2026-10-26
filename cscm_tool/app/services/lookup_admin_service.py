"""Controlled-vocabulary administration. docs/05-governance-handbook.md §3:
"Controlled vocabularies... are owned by Governance (Administrator role);
Engineers may propose new values, only an Administrator may activate one."
(Engineer proposals themselves — US-092 — are P2/not built; this covers the
Administrator side, US-091.)

v3 (2026-09-17, EPIC-16): Functional System Group and Functional Subgroup
creation are no longer routed through the generic create_value dispatcher —
docs/artifacts/openapi.yaml gives each its own dedicated endpoint/request
shape (code+label+range vs functional_system_group+code+label+sub_range),
and both require non-overlap validation the generic dispatcher has no
concept of (FR-048f/FR-048h, trg_prevent_subgroup_overlap/
trg_prevent_group_overlap as the database-layer backstop).

Numeric ranges are immutable through update_value once a vocabulary row
exists (BR-001: "Identifier + Functional System Group assignment is
immutable") — it never touches range_start/range_end/sub_range_start/
sub_range_end, only code/label/description/is_active/sort_order."""

from typing import Any

from app.domain.authz import require_roles
from app.domain.errors import DomainError, NotFoundError
from app.extensions import db
from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup
from app.services.audit_service import AuditService
from app.services.lookup_service import VOCABULARY_MODELS, LookupService


class LookupAdminService:
    @staticmethod
    def create_value(vocabulary: str, data: dict, actor) -> object:
        require_roles(actor, "ADMINISTRATOR")
        model = VOCABULARY_MODELS.get(vocabulary)
        if model is None:
            raise ValueError(f"Unknown vocabulary: {vocabulary}")
        if model in (LookupFunctionalSystemGroup, LookupFunctionalSubgroup):
            raise DomainError(
                f"{model.__name__} values are created via their own dedicated, "
                "non-overlap-validated endpoint, not the generic vocabulary API "
                "(docs/09-api-specification.md §6c)."
            )

        code = data.get("code")
        label = data.get("label")
        if code is None or not label:
            raise ValueError("code and label are required")

        existing = db.session.query(model).filter(model.code == code).first()  # type: ignore[attr-defined]
        if existing is not None:
            raise DomainError(f"{model.__name__} code '{code}' already exists.")

        kwargs: dict[str, Any] = {
            "code": code,
            "label": label,
            "is_active": 1,
            "sort_order": data.get("sort_order", 0),
        }
        if hasattr(model, "description"):
            kwargs["description"] = data.get("description")
        value = model(**kwargs)  # type: ignore[assignment]

        db.session.add(value)
        db.session.flush()

        AuditService.log(
            "Lookup",
            value.id,  # type: ignore[attr-defined]
            "LOOKUP_CHANGE",
            actor=actor,
            after={"vocabulary": vocabulary, "code": code, "label": label},
        )
        db.session.commit()
        return value

    @staticmethod
    def create_functional_system_group(data: dict, actor) -> LookupFunctionalSystemGroup:
        """FR-048g/h: Administrator-only, into any currently free range.
        Overlap is checked here (service layer, for a helpful named-conflict
        409) with trg_prevent_group_overlap as the database-layer backstop."""
        require_roles(actor, "ADMINISTRATOR")
        code = data.get("code")
        label = data.get("label")
        range_start = data.get("range_start")
        range_end = data.get("range_end")
        if not code or not label or range_start is None or range_end is None:
            raise ValueError("code, label, range_start, and range_end are required")
        if range_end <= range_start:
            raise ValueError("range_end must be greater than range_start")

        conflict = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(
                LookupFunctionalSystemGroup.range_start <= range_end,
                LookupFunctionalSystemGroup.range_end >= range_start,
            )
            .first()
        )
        if conflict is not None:
            raise DomainError(
                f"Proposed range {range_start}-{range_end} overlaps existing group "
                f"'{conflict.label}' ({conflict.range_start}-{conflict.range_end})."
            )

        group = LookupFunctionalSystemGroup(
            code=code,
            label=label,
            range_start=range_start,
            range_end=range_end,
            is_active=1,
            sort_order=data.get("sort_order", 0),
        )
        db.session.add(group)
        db.session.flush()

        AuditService.log(
            "Lookup",
            group.id,
            "LOOKUP_CHANGE",
            actor=actor,
            after={
                "vocabulary": "functional-system-groups",
                "code": code,
                "label": label,
                "range_start": range_start,
                "range_end": range_end,
            },
        )
        db.session.commit()
        return group

    @staticmethod
    def create_functional_subgroup(data: dict, actor) -> LookupFunctionalSubgroup:
        """FR-048e/f: Administrator-only, within an existing Functional
        System Group (resolved by id — see app/services/lookup_service.py
        module docstring for why). Overlap is checked here for a helpful
        named-conflict 409, with trg_prevent_subgroup_overlap as the
        database-layer backstop."""
        require_roles(actor, "ADMINISTRATOR")
        group_id = data.get("functional_system_group")
        code = data.get("code")
        label = data.get("label")
        sub_range_start = data.get("sub_range_start")
        sub_range_end = data.get("sub_range_end")
        if (
            not group_id
            or not code
            or not label
            or sub_range_start is None
            or sub_range_end is None
        ):
            raise ValueError(
                "functional_system_group, code, label, sub_range_start, and "
                "sub_range_end are required"
            )
        if sub_range_end <= sub_range_start:
            raise ValueError("sub_range_end must be greater than sub_range_start")

        group = LookupService.get_by_id(LookupFunctionalSystemGroup, group_id)

        conflict = (
            db.session.query(LookupFunctionalSubgroup)
            .filter(
                LookupFunctionalSubgroup.functional_system_group_id == group.id,
                LookupFunctionalSubgroup.sub_range_start <= sub_range_end,
                LookupFunctionalSubgroup.sub_range_end >= sub_range_start,
            )
            .first()
        )
        if conflict is not None:
            raise DomainError(
                f"Proposed sub-range {sub_range_start}-{sub_range_end} overlaps existing "
                f"subgroup '{conflict.label}' "
                f"({conflict.sub_range_start}-{conflict.sub_range_end})."
            )

        subgroup = LookupFunctionalSubgroup(
            functional_system_group_id=group.id,
            code=code,
            label=label,
            sub_range_start=sub_range_start,
            sub_range_end=sub_range_end,
            is_active=1,
            sort_order=data.get("sort_order", 0),
        )
        db.session.add(subgroup)
        db.session.flush()

        AuditService.log(
            "Lookup",
            subgroup.id,
            "SUBGROUP_CREATE",
            actor=actor,
            after={
                "vocabulary": "functional-subgroups",
                "functional_system_group_id": group.id,
                "code": code,
                "label": label,
                "sub_range_start": sub_range_start,
                "sub_range_end": sub_range_end,
            },
        )
        db.session.commit()
        return subgroup

    @staticmethod
    def update_value(vocabulary: str, value_id: int, data: dict, actor) -> object:
        require_roles(actor, "ADMINISTRATOR")
        model = VOCABULARY_MODELS.get(vocabulary)
        if model is None:
            raise ValueError(f"Unknown vocabulary: {vocabulary}")

        found = db.session.get(model, value_id)
        if found is None:
            raise NotFoundError(f"{model.__name__} {value_id} not found")
        # All concrete vocabulary models share this shape (code/label/
        # is_active/sort_order, optionally description) but the generic
        # VOCABULARY_MODELS dispatch only gives mypy the common Base type —
        # same trade-off already accepted in lookup_service.py.
        value: Any = found
        before = {
            "label": value.label,
            "description": getattr(value, "description", None),
            "is_active": bool(value.is_active),
        }

        if "label" in data:
            value.label = data["label"]
        if "description" in data and hasattr(value, "description"):
            value.description = data["description"]
        if "is_active" in data:
            value.is_active = 1 if data["is_active"] else 0
        if "sort_order" in data:
            value.sort_order = data["sort_order"]

        AuditService.log(
            "Lookup",
            value.id,
            "LOOKUP_CHANGE",
            actor=actor,
            before=before,
            after={
                "label": value.label,
                "description": getattr(value, "description", None),
                "is_active": bool(value.is_active),
            },
        )
        db.session.commit()
        return value

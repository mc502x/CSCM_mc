"""Controlled-vocabulary administration. docs/05-governance-handbook.md §3:
"Controlled vocabularies... are owned by Governance (Administrator role);
Engineers may propose new values, only an Administrator may activate one."
(Engineer proposals themselves — US-092 — are P2/not built; this covers the
Administrator side, US-091.)

Numeric ranges are immutable through this API once a vocabulary row exists
(BR-001: "Identifier + Functional System Group assignment is immutable") —
update() never touches range_start/range_end/sub_range_start/sub_range_end,
only code/label/description/is_active/sort_order."""

from typing import Any

from app.domain.errors import DomainError, NotFoundError
from app.extensions import db
from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup
from app.services.audit_service import AuditService
from app.services.lookup_service import VOCABULARY_MODELS, LookupService


class LookupAdminService:
    @staticmethod
    def create_value(vocabulary: str, data: dict, actor) -> object:
        model = VOCABULARY_MODELS.get(vocabulary)
        if model is None:
            raise ValueError(f"Unknown vocabulary: {vocabulary}")
        if model is LookupFunctionalSystemGroup:
            raise DomainError(
                "Functional System Groups are a fixed structural set "
                "(docs/05-governance-handbook.md §2) and cannot be created via this API."
            )

        code = data.get("code")
        label = data.get("label")
        if not code or not label:
            raise ValueError("code and label are required")

        existing = db.session.query(model).filter(model.code == code).first()  # type: ignore[attr-defined]
        if existing is not None:
            raise DomainError(f"{model.__name__} code '{code}' already exists.")

        if model is LookupFunctionalSubgroup:
            value = LookupAdminService._create_subgroup(data, code, label)
        else:
            kwargs = {
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
            value.id,
            "LOOKUP_CHANGE",
            actor=actor,
            after={"vocabulary": vocabulary, "code": code, "label": label},
        )
        db.session.commit()
        return value

    @staticmethod
    def _create_subgroup(data: dict, code: str, label: str) -> LookupFunctionalSubgroup:
        group_code = data.get("functional_system_group")
        sub_range_start = data.get("sub_range_start")
        sub_range_end = data.get("sub_range_end")
        if not group_code or sub_range_start is None or sub_range_end is None:
            raise ValueError(
                "functional_system_group, sub_range_start, and sub_range_end are required"
            )
        group = LookupService.get_by_code(LookupFunctionalSystemGroup, group_code)
        return LookupFunctionalSubgroup(
            functional_system_group_id=group.id,
            code=code,
            label=label,
            sub_range_start=sub_range_start,
            sub_range_end=sub_range_end,
            is_active=1,
            sort_order=data.get("sort_order", 0),
        )

    @staticmethod
    def update_value(vocabulary: str, value_id: int, data: dict, actor) -> object:
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
        before = {"label": value.label, "is_active": bool(value.is_active)}

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
            after={"label": value.label, "is_active": bool(value.is_active)},
        )
        db.session.commit()
        return value

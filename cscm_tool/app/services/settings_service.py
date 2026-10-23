"""Administrator-managed settings (table app_setting): SLA thresholds (I-08),
reviewer auto-assignment (I-30) and the capacity alert level (I-19).

Defaults live here in code so a fresh database needs no seed rows; a stored value
overrides its default. Each key has a validator, so a bad value can never be
saved (and therefore never has to be defended against at the point of use)."""

from collections.abc import Callable

from app.domain.authz import require_roles
from app.domain.errors import DomainError
from app.extensions import db
from app.models.operations import AppSetting
from app.services.audit_service import AuditService
from app.utils import utcnow_iso


def _positive_int(value: str) -> str:
    number = int(value)
    if number < 1 or number > 365:
        raise ValueError("must be a whole number between 1 and 365")
    return str(number)


def _percent(value: str) -> str:
    number = int(value)
    if number < 0 or number > 100:
        raise ValueError("must be a whole number between 0 and 100")
    return str(number)


def _boolean(value: str) -> str:
    if str(value).lower() in ("1", "true", "yes", "on"):
        return "1"
    if str(value).lower() in ("0", "false", "no", "off", ""):
        return "0"
    raise ValueError("must be true or false")


# key -> (default, validator, description)
SETTINGS: dict[str, tuple[str, Callable[[str], str], str]] = {
    "sla.review.amber_days": ("3", _positive_int, "Review stage turns amber after N business days"),
    "sla.review.red_days": ("5", _positive_int, "Review stage turns red after N business days"),
    "sla.approval.amber_days": (
        "2",
        _positive_int,
        "Approval stage turns amber after N business days",
    ),
    "sla.approval.red_days": ("3", _positive_int, "Approval stage turns red after N business days"),
    "reviewer.auto_assign": (
        "0",
        _boolean,
        "Assign the least-loaded Reviewer on Submit for Review",
    ),
    "health.capacity_alert_percent": (
        "15",
        _percent,
        "Alert when a subgroup's number band has at most N percent left",
    ),
    "health.capacity_alert_numbers": (
        "20",
        _positive_int,
        "...or at most N numbers left, whichever is reached first",
    ),
}


class SettingsService:
    @staticmethod
    def get(key: str) -> str:
        if key not in SETTINGS:
            raise KeyError(key)
        row = db.session.get(AppSetting, key)
        return row.value if row is not None else SETTINGS[key][0]

    @staticmethod
    def get_int(key: str) -> int:
        return int(SettingsService.get(key))

    @staticmethod
    def get_bool(key: str) -> bool:
        return SettingsService.get(key) == "1"

    @staticmethod
    def all() -> list[dict]:
        return [
            {
                "key": key,
                "value": SettingsService.get(key),
                "default": default,
                "description": description,
            }
            for key, (default, _validator, description) in SETTINGS.items()
        ]

    @staticmethod
    def update(values: dict, actor) -> list[dict]:
        require_roles(actor, "ADMINISTRATOR")
        cleaned: dict[str, str] = {}
        errors = []
        for key, raw in values.items():
            if key not in SETTINGS:
                errors.append(f"unknown setting '{key}'")
                continue
            try:
                cleaned[key] = SETTINGS[key][1](str(raw))
            except (TypeError, ValueError) as exc:
                errors.append(f"{key}: {exc}")
        for stage in ("review", "approval"):
            amber = int(
                cleaned.get(
                    f"sla.{stage}.amber_days", SettingsService.get(f"sla.{stage}.amber_days")
                )
            )
            red = int(
                cleaned.get(f"sla.{stage}.red_days", SettingsService.get(f"sla.{stage}.red_days"))
            )
            if amber > red:
                errors.append(f"sla.{stage}: amber threshold must not exceed the red threshold")
        if errors:
            raise DomainError("; ".join(errors))

        before = {key: SettingsService.get(key) for key in cleaned}
        for key, value in cleaned.items():
            row = db.session.get(AppSetting, key)
            if row is None:
                db.session.add(
                    AppSetting(key=key, value=value, updated_by=actor.id, updated_at=utcnow_iso())
                )
            else:
                row.value, row.updated_by, row.updated_at = value, actor.id, utcnow_iso()
        AuditService.log(
            "Settings", 0, "SETTINGS_CHANGE", actor=actor, before=before, after=cleaned
        )
        db.session.commit()
        return SettingsService.all()

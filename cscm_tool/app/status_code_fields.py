"""The fields of a revision that come from the generated controller programs (schema v4.1,
docs/06-data-dictionary.md sections 2c.1, 2d.1 and 2f; docs/03-srs.md FR-168).

One place names them, with the controller they apply to, so that the model, the service, the form,
the detail page, the API, the exports and the program import cannot disagree. A field that does not
apply to the controller of a code is stored as 0 (programs) or NULL (flags and parameters) and the
service rejects any other value for it (section 2f)."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text

from app.extensions import db

MAIN, HUB, BOTH = "MAIN", "HUB", "BOTH"

# (field, English label, controllers) - the labels are interface text and are translated.
MAIN_PROGRAMS: tuple[tuple[str, str], ...] = (
    ("converter_reset_program", "Converter Reset Program"),
    ("hydraulic_pump_program", "Hydraulic Pump Program"),
    ("gearbox_oil_pump_program", "Gearbox Oil Pump Program"),
    ("gearbox_oil_fan_program", "Gearbox Oil Fan Program"),
    ("gearbox_oil_heating_program", "Gearbox Oil Heating Program"),
    ("generator_fan_program", "Generator Fan Program"),
    ("generator_heating_program", "Generator Heating Program"),
    ("generator_bearing_lubrication_program", "Generator Bearing Lubrication Program"),
    ("rotor_bearing_lubrication_program", "Rotor Bearing Lubrication Program"),
    ("anemometer_heating_program", "Anemometer Heating Program"),
    ("medium_voltage_cb_program", "Medium Voltage Circuit Breaker Program"),
    ("tower_fan_program", "Tower Fan Program"),
    ("transformer_oil_pump_program", "Transformer Oil Pump Program"),
)
HUB_PROGRAMS: tuple[tuple[str, str], ...] = (
    ("pitch_error_program", "Pitch Error Program"),
    ("pitch_warning_program", "Pitch Warning Program"),
    ("rotor_brake_program", "Rotor Brake Program"),
)
# 0 / 1 / not captured
FLAGS: tuple[tuple[str, str, str], ...] = (
    ("zero_load_operation", "Zero Load Operation", MAIN),
    ("availability_calc", "Availability Calculation", BOTH),
    ("stop_program_40_flag", "Stop Program 40", HUB),
    ("stop_program_80_flag", "Stop Program 80", HUB),
    ("manual_operation_flag", "Manual Operation", HUB),
    ("automatic_operation_flag", "Automatic Operation", HUB),
    ("vane_position_flag", "Vane Position", HUB),
)
PARAMETERS: tuple[tuple[str, str, str], ...] = (
    ("operating_mode_mask", "Operating Mode Mask", BOTH),
    ("task_call_frequency", "Task Call Frequency", BOTH),
)

PROGRAM_FIELDS = tuple(f for f, _ in (*MAIN_PROGRAMS, *HUB_PROGRAMS))
FLAG_FIELDS = tuple(f for f, _l, _c in FLAGS)
PARAMETER_FIELDS = tuple(f for f, _l, _c in PARAMETERS)
NEW_FIELDS: tuple[str, ...] = (*PROGRAM_FIELDS, *FLAG_FIELDS, *PARAMETER_FIELDS)

APPLIES: dict[str, str] = {
    **{f: MAIN for f, _ in MAIN_PROGRAMS},
    **{f: HUB for f, _ in HUB_PROGRAMS},
    **{f: c for f, _l, c in FLAGS},
    **{f: c for f, _l, c in PARAMETERS},
}
LABELS: dict[str, str] = {
    **dict(MAIN_PROGRAMS),
    **dict(HUB_PROGRAMS),
    **{f: label for f, label, _c in FLAGS},
    **{f: label for f, label, _c in PARAMETERS},
}

MODE_BITS = {"MAIN": 20, "HUB": 6}  # the operating-mode mask is 20 bits on Main, 6 on Hub
MAX_MASK = (1 << 20) - 1
USER_GROUP_SLOTS = range(16)

_BINARY = re.compile(r"^[01]+$")


def applies_to(field: str, controller: str) -> bool:
    return APPLIES[field] in (BOTH, controller)


def mask_to_binary(mask: int | None, controller: str) -> str:
    """The mask as the generated program writes it: bits, padded to the controller's width."""
    if mask is None:
        return ""
    return format(mask, "b").zfill(MODE_BITS.get(controller, 20))


def parse_mask(value: Any) -> int | None:
    """A mask arrives as a bit string (form, program file) or as the number (API)."""
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError("The operating mode mask must be a number or a string of 0 and 1.")
    if isinstance(value, int):
        return value
    text_ = str(value).strip().removeprefix("2#")
    if not _BINARY.match(text_):
        raise ValueError("The operating mode mask must be a string of 0 and 1.")
    return int(text_, 2)


def normalise_user_groups(value: Any) -> dict | None:
    """The levels as {slot: {"read", "write"}}; the API sends a list of {"slot", ...} entries."""
    if value is None:
        return None
    if isinstance(value, list):
        out = {}
        for entry in value:
            if not isinstance(entry, dict) or "slot" not in entry:
                return {"?": {}}  # reported by validate()
            out[entry["slot"]] = {"read": entry.get("read"), "write": entry.get("write")}
        return out
    return value


def parse_levels(value: str) -> dict[int, dict[str, int]]:
    """ "1:1/5 2:1/10" -> {1: {"read": 1, "write": 5}, 2: {...}} (the form of the export column)."""
    out: dict[int, dict[str, int]] = {}
    for part in re.split(r"[\s;,]+", value.strip()):
        if not part:
            continue
        match = re.fullmatch(r"(\d+):(\d+)/(\d+)", part)
        if not match:
            raise ValueError(f"'{part}' is not a user group level like 1:1/5 (slot:read/write).")
        slot, read, write = (int(g) for g in match.groups())
        out[slot] = {"read": read, "write": write}
    return out


# audience field of the revision -> (slot of the user group, lookup table with the default levels)
AUDIENCE_SLOTS = {
    "development_access": (1, "lookup_development_access"),
    "sales_access": (2, "lookup_sales_access"),
    "tcc_access": (3, "lookup_tcc_access"),
    "service_access": (4, "lookup_service_access"),
    "turbine_operator_package_access": (5, "lookup_top_access"),
    "grid_operator_access": (6, "lookup_grid_operator_access"),
    "service_partner_access": (7, "lookup_service_partner_access"),
    "customer_access": (8, "lookup_customer_access"),
}


def fill_default_levels(revision: Any) -> None:
    """Section 2d.1: a named audience value brings the numbers it held on every code that carried
    it (`default_read_level`, `default_write_level` of the lookup); a slot that already has levels
    keeps them, and the Engineer may overwrite either."""
    levels = user_groups(revision)
    added = False
    for field, (slot, table) in AUDIENCE_SLOTS.items():
        value_id = getattr(revision, f"{field}_id")
        if value_id is None or slot in levels:
            continue
        statement = f"SELECT default_read_level, default_write_level FROM {table} WHERE id = :i"  # nosec B608  # the table names are the constants of AUDIENCE_SLOTS
        row = db.session.execute(text(statement), {"i": value_id}).first()
        if row is not None and row[0] is not None and row[1] is not None:
            levels[slot] = {"read": row[0], "write": row[1]}
            added = True
    if added:
        set_user_groups(revision, levels)


def _flag(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return 1 if value in (True, 1, "1", "on", "true", "True") else 0


# ----------------------------------------------------------------------------- validation
def validate(data: dict) -> list[dict]:
    """Type and range of the fields as sent; the controller rule is checked by the service."""
    errors: list[dict] = []

    def bad(field: str, message: str) -> None:
        errors.append({"field": field, "message": message})

    for field in PROGRAM_FIELDS:
        value = data.get(field)
        if value not in (None, "") and (
            isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 65535
        ):
            bad(field, f"{LABELS[field]} must be a whole number between 0 and 65535.")
    for field in FLAG_FIELDS:
        value = data.get(field)
        if value not in (None, "", True, False, 0, 1):
            bad(field, f"{LABELS[field]} must be true or false.")
    try:
        mask = parse_mask(data.get("operating_mode_mask"))
    except ValueError as exc:
        bad("operating_mode_mask", str(exc))
    else:
        if mask is not None and not 0 <= mask <= MAX_MASK:
            bad("operating_mode_mask", "The operating mode mask has at most 20 bits.")
    frequency = data.get("task_call_frequency")
    if frequency not in (None, "") and (
        isinstance(frequency, bool) or not isinstance(frequency, int) or frequency < 1
    ):
        bad("task_call_frequency", "The task call frequency must be a whole number of at least 1.")
    for slot, levels in (normalise_user_groups(data.get("user_groups")) or {}).items():
        try:
            number = int(slot)
            read, write = int(levels["read"]), int(levels["write"])
        except (KeyError, TypeError, ValueError):
            bad("user_groups", "A user group needs a slot, a read level and a write level.")
            continue
        if number not in USER_GROUP_SLOTS or not (0 <= read <= 255 and 0 <= write <= 255):
            bad("user_groups", "User group slots are 0 to 15 and the levels 0 to 255.")
    return errors


def check_controller(data: dict, controller: str) -> list[dict]:
    """Section 2f: a field that does not apply to the controller of the code holds no value."""
    errors = []
    for field in NEW_FIELDS:
        if applies_to(field, controller):
            continue
        value = data.get(field)
        if field in PROGRAM_FIELDS:
            used = bool(value)
        else:
            used = value not in (None, "")
        if used:
            errors.append(
                {
                    "field": field,
                    "message": f"{LABELS[field]} does not apply to the "
                    f"{'Main' if controller == MAIN else 'Hub'} Controller.",
                }
            )
    return errors


# ----------------------------------------------------------------------------- the revision
def apply(revision: Any, data: dict) -> None:
    """Writes the fields that `data` carries; a caller that does not know them (an API client of
    an older version, a spreadsheet import) leaves what the revision holds untouched."""
    for field in PROGRAM_FIELDS:
        if field in data:
            setattr(revision, field, int(data.get(field) or 0))
    for field in FLAG_FIELDS:
        if field in data:
            setattr(revision, field, _flag(data.get(field)))
    if "operating_mode_mask" in data:
        revision.operating_mode_mask = parse_mask(data.get("operating_mode_mask"))
    if "task_call_frequency" in data:
        frequency = data["task_call_frequency"]
        revision.task_call_frequency = int(frequency) if frequency not in (None, "") else None


def to_data(revision: Any) -> dict:
    data: dict[str, Any] = {field: getattr(revision, field) for field in PROGRAM_FIELDS}
    for field in FLAG_FIELDS:
        value = getattr(revision, field)
        data[field] = None if value is None else bool(value)
    data["operating_mode_mask"] = revision.operating_mode_mask
    data["task_call_frequency"] = revision.task_call_frequency
    data["user_groups"] = user_groups(revision)
    return data


def copy(source: Any, target: Any) -> None:
    for field in NEW_FIELDS:
        setattr(target, field, getattr(source, field))


# ----------------------------------------------------------------------------- user groups
def user_groups(revision: Any) -> dict[int, dict[str, int]]:
    """{slot: {"read": n, "write": n}} of a revision; empty when none were captured."""
    rows = sorted(revision.user_group_rows, key=lambda r: r.slot_row.slot)
    return {r.slot_row.slot: {"read": r.read_level, "write": r.write_level} for r in rows}


def set_user_groups(revision: Any, levels: dict | None) -> None:
    """Replaces the levels of a revision (`None` leaves them alone, `{}` clears them)."""
    levels = normalise_user_groups(levels)
    if levels is None:
        return
    db.session.execute(
        text("DELETE FROM status_code_revision_user_group WHERE status_code_revision_id = :r"),
        {"r": revision.id},
    )
    slot_ids: dict[int, int] = {
        row[0]: row[1]
        for row in db.session.execute(text("SELECT slot, id FROM lookup_user_group_slot"))
    }
    for slot, value in sorted((int(s), v) for s, v in levels.items()):
        db.session.execute(
            text(
                "INSERT INTO status_code_revision_user_group "
                "(status_code_revision_id, user_group_slot_id, read_level, write_level) "
                "VALUES (:r, :s, :rl, :wl)"
            ),
            {
                "r": revision.id,
                "s": slot_ids[slot],
                "rl": int(value["read"]),
                "wl": int(value["write"]),
            },
        )
    db.session.expire(revision, ["user_group_rows"])  # the relationship is read-only


def delete_user_groups(revision_id: int) -> None:
    """Called before a revision is deleted (a withdrawal, a deleted sandbox code)."""
    db.session.execute(
        text("DELETE FROM status_code_revision_user_group WHERE status_code_revision_id = :r"),
        {"r": revision_id},
    )


def copy_user_groups(source: Any, target: Any) -> None:
    set_user_groups(target, user_groups(source))


def slots() -> list[dict]:
    """The 16 slots with their labels, for the form and the detail page."""
    rows = db.session.execute(
        text(
            "SELECT slot, label, audience_code, is_active FROM lookup_user_group_slot ORDER BY slot"
        )
    )
    return [
        {"slot": slot, "label": label, "audience": audience, "active": bool(active)}
        for slot, label, audience, active in rows
    ]

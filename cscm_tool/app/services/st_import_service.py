# ruff: noqa: E501  (docstring lines)
"""Status code import from the generated Structured Text programs (`StCd_<n>.st`).

Docs: 03-srs.md FR-048o..FR-048w, 06-data-dictionary.md section 5a, 09-api-specification.md
section 6c, 10-ui-ux-specification.md screen S39. The reader itself is app/importers/stcd.py.

The flow has two steps so that nothing is created before a person has looked at it:

* **preview** - the uploaded files (several at once, a folder's worth, or one ZIP) are parsed and
  every program is checked against the catalogue. Nothing is written except the staged copy of the
  upload (instance/imports/staging/<token>/), which belongs to the uploading user and is removed
  after STAGING_HOURS;
* **confirm** - the programs the user ticked are re-checked (the catalogue may have changed in
  the meantime) and each becomes an ordinary Draft status code with its change request
  (cr_type IMPORT), exactly like a row of a CSV import (FR-048c): the import is a faster way to
  enter data, never a way around Cross-Domain Sign-Off, dual review or Chief Engineer approval.
  All change requests of one confirmation join one **change set** ("ST import #<job> ..."), so the
  whole batch is reviewed and decided together (I-11), and every program keeps its source file,
  SHA-256 and parsed attributes in `import_source_item`.

What a program becomes:

* the **number** the file carries is reserved for the code (`status_code.reserved_identifier`): the
  identifier issued at Submit for Review is exactly that number (NumberingService), and the group
  and subgroup follow from the subgroup band the number lies in;
* Hub Controller programs carry the *legacy* HC number; the new number comes from the mapping
  (MappingService; FR-191..FR-198);
* the **legacy number** (Main Controller: the old number in the header comment; Hub Controller: the
  number in the file name) is stored as `legacy_reference_number`. That one field is the whole
  legacy -> new mapping (LegacyMappingService); codes without one simply have no legacy
  counterpart - the new set is larger than the old one, so the mapping is never inverted;
* the attributes the catalogue already has are filled in; PrgIdx_GUi is stored when it is free; the
  user-group levels and the subsystem programs without a catalogue column yet stay in the parsed
  JSON of `import_source_item`.

What the programs do not carry comes from the **mapping** and nowhere else: the English title (checked
against the German name of the program with the glossary), the type (the status category), the up/down
counter, the eight named access levels (checked against the user-group numbers of the program), the
cause and directive (the remedy text) and the value of a parameter delay. A program whose number is not
in the mapping, or whose row has no type, is blocked; a row that the StCd Owner, the Chief Engineer and
an Administrator have not approved yet is used with a warning. The description is generated (a
catalogue description needs 10 characters and differs from the title) and names the file, the name in
the program, what is not in the program and the set condition."""

from __future__ import annotations

import io
import json
import re
import secrets
import shutil
import threading
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from flask import current_app
from sqlalchemy import text

from app import status_code_fields
from app.domain.authz import require_roles
from app.domain.errors import DomainError, ForbiddenError, NotFoundError
from app.extensions import db
from app.importers import glossary, stcd
from app.models.change_request import ChangeRequest
from app.models.import_job import ImportJob, ImportSourceItem
from app.models.lookup import (
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
    LookupTurbinePlatform,
)
from app.models.status_code import StatusCode
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.change_set_service import ChangeSetService
from app.services.import_service import ImportService, Issue, RowResult, changed_fields
from app.services.mapping_service import MappingRow, MappingService, MappingTable
from app.services.numbering_service import NumberingService
from app.services.status_code_service import StatusCodeService, ValidationFailed
from app.services.validation import MAX_REMEDY_CHARS, NO_VALUE, validate_revision_fields
from app.utils import utcnow_iso

STAGING_HOURS = 24
MAX_UPLOAD_FILES = 2000
MAX_UNZIPPED_BYTES = 50 * 1024 * 1024
CONTROLLER_CHOICES = ("auto", "MC", "HC")
_TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")
_DESCRIPTION_LIMIT = 4000

# ST subsystem program attribute -> catalogue field (the others are kept in the parsed JSON)
_PROGRAM_FIELDS = {
    "Azimut": "yaw_program",
    "ManReset": "manual_reset_program",
    "AutoReset": "auto_reset_program",
    "QConverter": "converter_reactive_power_program",
    "Brake": "brake_program",
    "ConverterGSC": "umrichterprogramm_gsc",
    "ConverterMSC": "umrichterprogramm_msc",
    "YawLub": "yaw_bearing_lubrication_program",
}
# the further subsystem programs of schema v4.1 (docs/06-data-dictionary.md section 2c.1)
_EXTRA_PROGRAM_FIELDS = {
    "ResetConverter": "converter_reset_program",
    "Hydraulic": "hydraulic_pump_program",
    "GearOilPump": "gearbox_oil_pump_program",
    "GearOilCooling": "gearbox_oil_fan_program",
    "GearHeating": "gearbox_oil_heating_program",
    "GenFan": "generator_fan_program",
    "GenHeating": "generator_heating_program",
    "GenoLub": "generator_bearing_lubrication_program",
    "RotBearLub": "rotor_bearing_lubrication_program",
    "VaneAneHeat": "anemometer_heating_program",
    "MeanVoltageCB": "medium_voltage_cb_program",
    "TowerFan": "tower_fan_program",
    "TrafoPump": "transformer_oil_pump_program",
    "PtErrOp": "pitch_error_program",
    "PtWarnOp": "pitch_warning_program",
    "RotorBrake": "rotor_brake_program",
}
_ALL_CATALOGUE_PROGRAM_FIELDS = tuple(_PROGRAM_FIELDS.values())
_ACCESS_FIELDS = (
    "development_access",
    "sales_access",
    "tcc_access",
    "service_access",
    "turbine_operator_package_access",
    "grid_operator_access",
    "service_partner_access",
    "customer_access",
)


class StagingError(NotFoundError):
    """The staged upload is unknown, expired or belongs to someone else."""


@dataclass
class Evaluated:
    """One program after checking: the row the screen shows, plus what confirm needs."""

    view: dict[str, Any]
    data: dict[str, Any] | None = None
    code: stcd.StatusCode | None = None
    sha256: str = ""
    prg_idx: int | None = None
    notes: list[str] = field(default_factory=list)
    action: str = "create"  # create | update | revise | restore
    status_code_id: int | None = None


# ------------------------------------------------------------------------------ formatting
def format_delay(ms: int | None) -> str | None:
    """A delay in the unit notation the catalogue uses (10ms, 5s, 2min); None for a variable."""
    if ms is None:
        return None
    if ms >= 60_000 and ms % 60_000 == 0:
        return f"{ms // 60_000}min"
    if ms >= 1_000 and ms % 1_000 == 0:
        return f"{ms // 1_000}s"
    return f"{ms}ms"


def format_window(seconds: int | None) -> str | None:
    """The 'repeated over the course' window: 86400 -> 1d, 7200 -> 2h, 90 -> 90s."""
    if not seconds or seconds < 1:
        return None
    for unit, size in (("d", 86_400), ("h", 3_600), ("min", 60)):
        if seconds >= size and seconds % size == 0:
            return f"{seconds // size}{unit}"
    return f"{seconds}s"


def _description(code: stcd.StatusCode, unresolved: list[str], differences: list[str]) -> str:
    """The comment of the Draft. What the program or the mapping does not give is listed (FR-189),
    before the set condition, so that a long condition can never cut it off."""
    program = code.number if code.controller == "MC" else code.legacy_number
    parts = [f"Imported from {Path(code.file).name} (program StCd_{program})."]
    if code.legacy_number is not None:
        parts.append(f"Legacy {code.controller} number {code.legacy_number}.")
    if code.name:
        parts.append(f"Name in the program: {code.name}.")
    if differences:
        parts.append("Mapping and program differ: " + "; ".join(differences) + ".")
    if unresolved:
        parts.append("Not resolved by the import: " + "; ".join(unresolved) + ".")
    head = " ".join(parts)
    if code.set_condition:
        room = _DESCRIPTION_LIMIT - len(head) - len(" Set condition: ")
        if room > 0:
            return head + " Set condition: " + code.set_condition[:room]
    return head[:_DESCRIPTION_LIMIT]


def _identifier_number(identifier: str) -> int:
    return int(identifier[len("StCd-") :])


# ------------------------------------------------------------------------------ staging
def _staging_root() -> Path:
    return Path(current_app.instance_path) / "imports" / "staging"


def _staging_dir(token: str) -> Path:
    if not _TOKEN_RE.match(token or ""):
        raise StagingError("Unknown preview. Upload the files again.")
    return _staging_root() / token


def _purge_old_staging() -> None:
    root = _staging_root()
    if not root.is_dir():
        return
    limit = time.time() - STAGING_HOURS * 3600
    for entry in root.iterdir():
        try:
            if entry.is_dir() and entry.stat().st_mtime < limit:
                shutil.rmtree(entry, ignore_errors=True)
        except OSError:
            continue


def expand_uploads(uploads: list[tuple[str, bytes]]) -> tuple[list[tuple[str, bytes]], list[str]]:
    """Plain files stay as they are; a .zip contributes every member with a known suffix.
    Returns (files, notes). Raises ValueError for an unusable upload."""
    files: list[tuple[str, bytes]] = []
    notes: list[str] = []
    total = 0
    for name, content in uploads:
        base = Path(name.replace("\\", "/")).name or "upload"
        if base.lower().endswith(".zip"):
            try:
                archive = zipfile.ZipFile(io.BytesIO(content))
            except zipfile.BadZipFile as exc:
                raise ValueError(f"{base} is not a readable ZIP archive.") from exc
            with archive:
                for info in archive.infolist():
                    member = Path(info.filename.replace("\\", "/")).name
                    if info.is_dir() or Path(member).suffix.lower() not in stcd.SUFFIXES:
                        continue
                    total += info.file_size
                    if total > MAX_UNZIPPED_BYTES:
                        raise ValueError(
                            f"{base} unpacks to more than {MAX_UNZIPPED_BYTES // (1024 * 1024)} MB."
                        )
                    if info.file_size > stcd.MAX_FILE_BYTES:
                        notes.append(f"{base}: {member} is larger than the file limit; skipped.")
                        continue
                    files.append((member, archive.read(info)))
        elif Path(base).suffix.lower() in stcd.SUFFIXES:
            files.append((base, content))
        else:
            notes.append(
                f"{base}: not a status code program file "
                f"({', '.join(sorted(stcd.SUFFIXES))}); skipped."
            )
        if len(files) > MAX_UPLOAD_FILES:
            raise ValueError(f"More than {MAX_UPLOAD_FILES} files in one upload.")
    if not files:
        raise ValueError("No StCd program files found. Upload .st files or a ZIP of them.")
    return files, notes


def _clean_options(options: dict | None) -> dict[str, Any]:
    options = dict(options or {})
    controller = str(options.get("controller") or "auto")
    if controller.lower() == "auto":
        controller = "auto"
    elif controller.upper() in ("MC", "HC"):
        controller = controller.upper()
    else:
        raise ValueError("controller must be auto, MC or HC")
    known = [p.code for p in db.session.query(LookupTurbinePlatform).filter_by(is_active=1)]
    platforms = options.get("platforms")
    if isinstance(platforms, str):
        platforms = [p.strip() for p in re.split(r"[;,\s]+", platforms) if p.strip()]
    platforms = list(platforms) if platforms else sorted(known)
    unknown = [p for p in platforms if p not in known]
    if unknown:
        raise ValueError("Unknown turbine platform: " + ", ".join(unknown))
    return {"controller": controller, "platforms": platforms}


# ------------------------------------------------------------------------------ evaluation
def _load_levels() -> dict[str, dict[str, tuple[int, str, int | None, int | None]]]:
    """Per audience field: the active named access levels by lower-case label, as (id, label, read,
    write). The numbers are the defaults of docs/06-data-dictionary.md section 9d.9; a level whose
    numbers differ from code to code has none."""
    out: dict[str, dict[str, tuple[int, str, int | None, int | None]]] = {}
    for field_name, (_slot, table) in status_code_fields.AUDIENCE_SLOTS.items():
        statement = (
            "SELECT id, label, default_read_level, default_write_level FROM "  # nosec B608
            + table
            + " WHERE is_active = 1"
        )
        out[field_name] = {
            r[1].lower(): (r[0], r[1], r[2], r[3]) for r in db.session.execute(text(statement))
        }
    return out


class _Catalogue:
    """What the catalogue already holds, loaded once per evaluation."""

    def __init__(self) -> None:
        rows = db.session.execute(
            text(
                "SELECT id, status_code_identifier, reserved_identifier FROM status_code "
                "WHERE status_code_identifier IS NOT NULL OR reserved_identifier IS NOT NULL"
            )
        ).all()
        self.by_identifier: dict[str, int] = {}
        for code_id, issued, reserved in rows:
            for value in (issued, reserved):
                if value:
                    self.by_identifier[value] = code_id
        self.identifier_of: dict[int, str] = {
            code_id: issued or reserved for code_id, issued, reserved in rows
        }
        self.legacy: dict[tuple[str, str], int] = {}
        for code_id, legacy, controller_type in db.session.execute(
            text(
                "SELECT sc.id, sc.legacy_reference_number, g.controller_type FROM status_code sc "
                "JOIN lookup_functional_system_group g ON g.id = sc.functional_system_group_id "
                "WHERE sc.legacy_reference_number IS NOT NULL AND sc.is_sandbox = 0"
            )
        ).all():
            self.legacy.setdefault(
                ("HC" if controller_type == "HUB" else "MC", str(legacy)), code_id
            )
        self.prg_idx: dict[int, int] = {
            value: code_id
            for code_id, value in db.session.execute(
                text(
                    "SELECT id, prg_idx FROM status_code "
                    "WHERE prg_idx IS NOT NULL AND is_sandbox = 0"
                )
            ).all()
        }
        self.levels = _load_levels()
        self.groups = {g.id: g for g in db.session.query(LookupFunctionalSystemGroup)}
        self.subgroups = {s.id: s for s in db.session.query(LookupFunctionalSubgroup)}

    def label(self, code_id: int) -> str:
        return self.identifier_of.get(code_id) or f"#{code_id}"


def _hub_numbers(table: MappingTable) -> dict[int, int]:
    return {
        r.legacy_number: r.new_number
        for r in table.rows
        if r.family == "HC" and r.legacy_number is not None
    }


def _evaluate(
    parsed: list[tuple[int, str, str, list[stcd.StatusCode]]],
    options: dict[str, Any],
    table: MappingTable,
) -> list[Evaluated]:
    """Checks every program. `parsed` is [(file index, name, sha256, programs)]."""
    catalogue = _Catalogue()
    hub_numbers = _hub_numbers(table)
    seen_identifier: dict[str, str] = {}
    seen_prg: dict[int, str] = {}
    seen_legacy: dict[tuple[str, int], str] = {}
    out: list[Evaluated] = []

    for file_index, name, sha, programs in parsed:
        for code in programs:
            if code.controller == "HC":
                stcd.apply_mapping(code, hub_numbers)
            out.append(
                _evaluate_one(
                    file_index,
                    name,
                    sha,
                    code,
                    options,
                    table,
                    catalogue,
                    seen_identifier,
                    seen_prg,
                    seen_legacy,
                )
            )
    return out


def _mapping_row(code: stcd.StatusCode, table: MappingTable) -> MappingRow | None:
    """The row of the mapping a program belongs to: a Main Controller program by its number, a Hub
    Controller program by its legacy number."""
    if code.controller == "HC":
        return table.for_hub(code.legacy_number) if code.legacy_number is not None else None
    return table.for_main(code.number)


def _evaluate_one(
    file_index: int,
    file_name: str,
    sha: str,
    code: stcd.StatusCode,
    options: dict[str, Any],
    table: MappingTable,
    catalogue: _Catalogue,
    seen_identifier: dict[str, str],
    seen_prg: dict[int, str],
    seen_legacy: dict[tuple[str, int], str],
) -> Evaluated:
    program = code.legacy_number if code.controller == "HC" else code.number
    view: dict[str, Any] = {
        "key": f"{file_index}:{program}",
        "file": file_name,
        "line": code.line,
        "program_number": program,
        "controller": code.controller,
        "identifier": code.identifier or None,
        "legacy_number": code.legacy_number,
        "name": code.name,
        "group": None,
        "subgroup": None,
        "prg_idx": code.prg_idx,
        "alarm_type": code.alarm_type,
        "category": None,
        "state": "blocked",
        "issues": [],
        "warnings": list(code.warnings),
        "existing": None,
    }
    issues: list[dict[str, str]] = view["issues"]
    warnings: list[str] = view["warnings"]
    item = Evaluated(view=view, code=code, sha256=sha)

    def problem(column: str, message: str) -> None:
        issues.append({"column": column, "message": message})

    if not code.identifier:
        problem("identifier", "; ".join(code.warnings) or "The program has no usable number.")
        warnings.clear()
        return item
    identifier = code.identifier
    number = _identifier_number(identifier)

    # Already in the catalogue: unchanged is not a failure; a changed program can update the Draft
    # or open a new revision of the code, and a code whose change request was withdrawn can be
    # restored from the file (FR-048x).
    row = _mapping_row(code, table)
    present = catalogue.by_identifier.get(identifier)
    if present is not None:
        _evaluate_existing(item, present, code, options, row, catalogue, table)
        return item
    if identifier in seen_identifier:
        problem(
            "identifier",
            f"{identifier} is also defined by {seen_identifier[identifier]} in this upload.",
        )
        return item
    seen_identifier[identifier] = f"{file_name} line {code.line}"

    band = NumberingService.band_of(number)
    if band is None:
        problem(
            "identifier",
            f"No numbering subgroup covers {identifier}. Controls Engineering must open a "
            "subgroup for this range first.",
        )
        return item
    group = catalogue.groups[band[0]]
    subgroup = catalogue.subgroups[band[1]]
    view["group"] = group.code
    view["subgroup"] = subgroup.code
    expected_controller = "HC" if group.controller_type == "HUB" else "MC"
    if expected_controller != code.controller:
        problem(
            "controller",
            f"{identifier} lies in the {group.code} range, which belongs to the "
            f"{expected_controller} numbering, but the program is a {code.controller} program.",
        )

    if code.legacy_number is not None:
        key = ("HC" if code.controller == "HC" else "MC", str(code.legacy_number))
        owner = catalogue.legacy.get(key)
        if owner is not None:
            problem(
                "legacy_reference_number",
                f"Legacy {code.controller} number {code.legacy_number} already belongs to "
                f"{catalogue.label(owner)}.",
            )
        elif (code.controller, code.legacy_number) in seen_legacy:
            problem(
                "legacy_reference_number",
                f"Legacy number {code.legacy_number} is also used by "
                f"{seen_legacy[(code.controller, code.legacy_number)]} in this upload.",
            )
        else:
            seen_legacy[(code.controller, code.legacy_number)] = f"{file_name} line {code.line}"

    if code.prg_idx is not None:
        prg_owner = catalogue.prg_idx.get(code.prg_idx)
        if prg_owner is not None:
            warnings.append(
                f"PrgIdx_GUi {code.prg_idx} is already used by {catalogue.label(prg_owner)}; "
                "it is not stored."
            )
        elif code.prg_idx in seen_prg:
            warnings.append(
                f"PrgIdx_GUi {code.prg_idx} is also used by {seen_prg[code.prg_idx]}; "
                "it is not stored."
            )
        elif 1 <= code.prg_idx <= 65535:
            seen_prg[code.prg_idx] = f"{file_name} line {code.line}"
            item.prg_idx = code.prg_idx
        else:
            warnings.append(f"PrgIdx_GUi {code.prg_idx} is outside 1..65535; it is not stored.")
    else:
        warnings.append("The program has no PrgIdx_GUi; enter it before the code can be released.")

    if row is None:
        other = table.by_new.get(number)
        if other is not None and code.controller == "MC":
            message = (
                f"{identifier} is a Hub Controller row in the mapping, but the program is a Main "
                "Controller program."
            )
        else:
            legacy = (
                f" (legacy {code.controller} number {code.legacy_number})"
                if code.legacy_number is not None
                else ""
            )
            message = (
                f"{identifier}{legacy} is not in the mapping. The title, the type and the access "
                "levels come from the mapping only: request the row under Mapping first (it needs "
                "the approval of the StCd Owner, the Chief Engineer and an Administrator)."
            )
        problem("mapping", message)
        return item
    _check_row(code, row, group, identifier, view, problem)
    data = _to_data(code, options, group, subgroup, view, row, catalogue.levels, table)
    item.data = data
    for error in validate_revision_fields(data):
        problem(error["field"], error["message"])
    if code.availability_group is None:
        problem("available_group", "The program has no availability group.")

    if not issues:
        view["state"] = "ready"
    return item


def _evaluate_existing(
    item: Evaluated,
    code_id: int,
    code: stcd.StatusCode,
    options: dict[str, Any],
    row: MappingRow | None,
    catalogue: _Catalogue,
    table: MappingTable,
) -> None:
    view = item.view
    view["existing"] = {
        "id": code_id,
        "identifier": catalogue.label(code_id),
        "lifecycle_state": None,
    }
    view["state"] = "exists"
    status_code = db.session.get(StatusCode, code_id)
    if status_code is None:
        return
    group = catalogue.groups[status_code.functional_system_group_id]
    subgroup = catalogue.subgroups[status_code.functional_subgroup_id]
    # the delay warnings of a program that already exists are not repeated on the screen
    data = _to_data(
        code, options, group, subgroup, {**view, "warnings": []}, row, catalogue.levels, table
    )
    view["category"] = data.get("status_category")
    current = StatusCodeService._repo.get_current_revision(code_id)
    if row is None and current is not None:
        # not in the mapping (imported before it existed): the code keeps what the mapping would
        # have given, it is not compared with an assumption
        for name in (
            "title",
            "description",
            "status_category",
            "up_down_counter",
            "remedy_text",
            "set_delay",
            "reset_delay",
        ):
            data[name] = getattr(current, name)
        for name in _ACCESS_FIELDS:
            data[name] = getattr(current, f"{name}_id")
        view["category"] = current.status_category
        view["warnings"].append(
            f"{view['identifier']} is not in the mapping; its title, type and access levels stay "
            "as they are."
        )
    item.status_code_id = code_id
    if current is None and row is None:
        view["state"] = "blocked"
        view["issues"].append(
            {
                "column": "mapping",
                "message": (
                    f"{view['identifier']} is not in the mapping, so the withdrawn code cannot be "
                    "restored: the title and the type come from the mapping only."
                ),
            }
        )
        return
    if current is None:
        # the change request was withdrawn: the code row is still there (its number is kept)
        item.data, item.action = data, "restore"
        view["state"], view["action"] = "restorable", "restore"
        view["existing"]["lifecycle_state"] = "WITHDRAWN"
        view["warnings"].append(
            f"The change request of {view['existing']['identifier']} was withdrawn; the number is "
            "kept. Restoring opens a new Draft on it."
        )
        return
    view["existing"]["lifecycle_state"] = current.lifecycle_status
    changes = changed_fields(current, data)
    view["changes"] = changes
    if not changes:
        return
    state = current.lifecycle_status
    item.data = data
    if state == "DRAFT":
        item.action = "update"
    elif state in ("APPROVED", "RELEASED"):
        item.action = "revise"
    else:
        view["state"] = "blocked"
        view["issues"].append(
            {
                "column": "identifier",
                "message": (
                    "The code is in review right now and cannot take a new revision."
                    if state in ("REVIEW", "PENDING_APPROVAL")
                    else f"The code is {state.title()} and cannot be revised."
                ),
            }
        )
        return
    view["state"], view["action"] = "changed", item.action


_AUDIENCE_NAMES = {
    "development_access": "Development",
    "sales_access": "Sales",
    "tcc_access": "TCC",
    "service_access": "Service",
    "turbine_operator_package_access": "Turbine Operator Package",
    "grid_operator_access": "Grid Operator",
    "service_partner_access": "Service Partner",
    "customer_access": "Customer",
}


def _named_access(
    code: stcd.StatusCode,
    row: MappingRow,
    levels: dict[str, dict[str, tuple[int, str, int | None, int | None]]],
    differences: list[str],
    unresolved: list[str],
) -> dict[str, int]:
    """The eight named access levels come from the mapping. The program carries the numbers of the
    levels (read and write per audience); where the named level has numbers of its own and the program
    gives other ones, the difference is listed and warned about - the numbers themselves are always
    kept with the Draft (FR-190)."""
    found: dict[str, int] = {}
    absent: list[str] = []
    for field_name, (slot, _table) in status_code_fields.AUDIENCE_SLOTS.items():
        label = _AUDIENCE_NAMES[field_name]
        named = row.access.get(field_name)
        if not named:
            absent.append(label)
            continue
        entry = levels.get(field_name, {}).get(named.lower())
        if entry is None:
            unresolved.append(
                f"{label} access: the mapping names '{named}', which is not an active level"
            )
            continue
        found[field_name] = entry[0]
        given = code.user_groups.get(slot) or {}
        if (
            entry[2] is not None
            and entry[3] is not None
            and "read" in given
            and "write" in given
            and (given["read"], given["write"]) != (entry[2], entry[3])
        ):
            differences.append(
                f"{label} access: the mapping says {named} (read {entry[2]} / write {entry[3]}), "
                f"the program has read {given['read']} / write {given['write']}"
            )
    if absent:
        unresolved.append("access levels not in the mapping: " + ", ".join(absent))
    return found


def _check_row(
    code: stcd.StatusCode,
    row: MappingRow,
    group: LookupFunctionalSystemGroup,
    identifier: str,
    view: dict[str, Any],
    problem: Any,
) -> None:
    """What the mapping row says about this program: usable at all, approved, in agreement with the
    program header and with the numbering band, and a title that matches the German name."""
    warnings: list[str] = view["warnings"]
    if row.status_type is None:
        problem(
            "status_category",
            f"The mapping has no type for {identifier}. Complete the row under Mapping first.",
        )
    if row.status not in ("APPROVED", "ISSUED"):
        warnings.append(
            f"The mapping row of {identifier} is {row.status.replace('_', ' ').lower()}: the "
            "number is not approved yet by the StCd Owner, the Chief Engineer and an Administrator."
        )
    if code.controller == "MC":
        header, mapped = code.legacy_number, row.legacy_number
        if header is not None and mapped is not None and header != mapped:
            problem(
                "legacy_reference_number",
                f"The program header gives legacy number {header}, the mapping gives {mapped} "
                f"for {identifier}.",
            )
        elif header is not None and mapped is None:
            warnings.append(
                f"The program header gives legacy number {header}; the mapping has none for "
                f"{identifier}."
            )
        elif header is None and mapped is not None:
            warnings.append(
                f"The mapping gives legacy number {mapped} for {identifier}; the program header "
                "has none."
            )
    if row.logical_node and row.logical_node != group.code:
        warnings.append(
            f"The mapping gives the logical node {row.logical_node}; the number range of "
            f"{identifier} belongs to {group.code}."
        )
    for message in glossary.check(code.name, row.description):
        warnings.append(f"Title and program name: {message}.")


def _delay(
    label: str,
    raw: str,
    ms: int | None,
    mapped: str | None,
    unresolved: list[str],
    differences: list[str],
    warnings: list[str],
) -> str:
    """The delay as the program gives it: a time; else - when the program names the parameter that
    sets it - the value the mapping knows for that parameter; else the name of the parameter; else the
    statement that the program has no timer. Never an assumed time."""
    if ms is not None:
        return format_delay(ms) or NO_VALUE
    if raw:
        if mapped:
            differences.append(
                f"{label} = {mapped} from the mapping (the program sets it with the parameter {raw})"
            )
            warnings.append(
                f"The {label} is set by the parameter {raw}; {mapped} is the value the mapping "
                "gives. Check it before release."
            )
            return mapped
        unresolved.append(
            f"{label} = {raw} (a variable or parameter; its value is not in the program or the "
            "mapping)"
        )
        warnings.append(
            f"The {label} is the parameter {raw}; the name is entered, "
            "look the value up before release."
        )
        return raw
    unresolved.append(f"{label}: the program has no timer")
    warnings.append(f'The program has no timer for the {label}; "{NO_VALUE}" is entered.')
    return NO_VALUE


def _remedy(row: MappingRow | None) -> str | None:
    """Cause and directive of the mapping as the remedy text; nothing when the mapping has neither."""
    if row is None:
        return None
    parts = []
    if row.cause:
        parts.append("Cause: " + row.cause)
    if row.directive:
        parts.append("Directive: " + row.directive)
    return "\n".join(parts)[:MAX_REMEDY_CHARS] or None


def _to_data(
    code: stcd.StatusCode,
    options: dict[str, Any],
    group: LookupFunctionalSystemGroup,
    subgroup: LookupFunctionalSubgroup,
    view: dict[str, Any],
    row: MappingRow | None,
    levels: dict[str, dict[str, tuple[int, str, int | None, int | None]]],
    table: MappingTable | None,
) -> dict[str, Any]:
    warnings: list[str] = view["warnings"]
    view["category"] = row.status_type if row else None
    # FR-189: nothing is assumed. A value is read from the program, taken from the mapping, or - when
    # neither has it - the name of the variable the program gives. What neither gives is listed in
    # the comment of the Draft (description).
    unresolved: list[str] = []
    differences: list[str] = []
    access = _named_access(code, row, levels, differences, unresolved) if row else {}
    for line in differences:
        if "access:" in line:
            warnings.append(line[0].upper() + line[1:] + ".")
    set_delay = _delay(
        "set delay",
        code.set_delay,
        code.set_delay_ms,
        row.parameter_set_delay if row else None,
        unresolved,
        differences,
        warnings,
    )
    reset_delay = _delay(
        "reset delay",
        code.reset_delay,
        code.reset_delay_ms,
        row.parameter_reset_delay if row else None,
        unresolved,
        differences,
        warnings,
    )
    not_given_no: list[str] = []
    if code.alarm is None:
        not_given_no.append("alarm")
    if code.snapshot is None:
        not_given_no.append("trigger snapshot")
    if "ZeroLoadPrg_ArBo" not in code.other:
        not_given_no.append("loadless spinning permitted")
    if row is not None and row.up_down_counter is None:
        not_given_no.append("up/down counter (not in the mapping)")
    if not_given_no:
        unresolved.append("not in the program, entered as No: " + ", ".join(not_given_no))
    missing_programs = [
        status_code_fields.LABELS.get(target, target.replace("_", " "))
        for source, target in _PROGRAM_FIELDS.items()
        if source not in code.programs
    ] + [
        status_code_fields.LABELS[target]
        for source, target in _EXTRA_PROGRAM_FIELDS.items()
        if source not in code.programs
        and status_code_fields.applies_to(target, group.controller_type)
    ]
    if missing_programs:
        unresolved.append("not in the program, entered as 0: " + ", ".join(missing_programs))

    related = []
    for number in code.depends_on:
        new_number = _dependency_number(code, number, table)
        if new_number is None:
            warnings.append(f"The set condition refers to StCd_{number}, which has no new number.")
        else:
            related.append(f"StCd-{new_number:05d}")
    data: dict[str, Any] = {
        "functional_system_group": group.id,
        "functional_subgroup": subgroup.id,
        "turbine_platforms": list(options["platforms"]),
        "title": (row.description if row else code.name)[:120],
        "description": _description(code, unresolved, differences),
        "software_version": None,
        "status_category": row.status_type if row else None,
        "available_group": code.availability_group,
        "alarm_flag": bool(code.alarm),  # None = not in the program, listed above
        "set_delay": set_delay,
        "reset_delay": reset_delay,
        "up_down_counter": bool(row.up_down_counter) if row else False,
        "trigger_snapshot": bool(code.snapshot),
        "loadless_spinning_permitted": bool(code.other.get("ZeroLoadPrg_ArBo")),
        "number_of_times_repeated": (
            code.max_repeats if code.max_repeats and code.max_repeats >= 1 else None
        ),
        "repeated_over_the_course": format_window(code.repeat_time_s) if code.max_repeats else None,
        "status_code_for_repeated_error": code.repeat_code,
        "legacy_reference_number": (
            str(code.legacy_number) if code.legacy_number is not None else None
        ),
        "remedy_text": _remedy(row),
        "affected_component": None,
        "related_status_codes": ", ".join(related)[:500] or None,
        "standard_references": None,
        "applies_from_version": None,
        "applies_to_version": None,
        "planned_effective_date": None,
        "planned_deprecation_date": None,
    }
    for source, target in _PROGRAM_FIELDS.items():
        data[target] = int(code.programs.get(source) or 0)
    for field_name in _ALL_CATALOGUE_PROGRAM_FIELDS:
        data.setdefault(field_name, 0)
    data.update(_generated_fields(code, group.controller_type, warnings))
    for field_name in _ACCESS_FIELDS:
        data[field_name] = access.get(field_name)
    if not code.name:
        warnings.append("The program has no name in its header comment.")
    return data


def _generated_fields(
    code: stcd.StatusCode, controller: str, warnings: list[str]
) -> dict[str, Any]:
    """What the generated program holds beyond the classic fields (schema v4.1): the further
    subsystem programs, the operating-mode mask, the task call frequency, two flags and the sixteen
    user-group levels. A value for a field that does not apply to the controller is dropped with a
    warning (docs/06-data-dictionary.md section 2f)."""
    data: dict[str, Any] = {f: 0 for f in status_code_fields.PROGRAM_FIELDS}
    for source, target in _EXTRA_PROGRAM_FIELDS.items():
        value = int(code.programs.get(source) or 0)
        if value and not status_code_fields.applies_to(target, controller):
            warnings.append(
                f"{source}PrgArUs is {value}, but {status_code_fields.LABELS[target]} does not "
                f"apply to the {'Hub' if controller == 'HUB' else 'Main'} Controller; "
                "it is left out."
            )
            value = 0
        data[target] = value
    for flag in status_code_fields.FLAG_FIELDS:
        data[flag] = None
    if status_code_fields.applies_to("zero_load_operation", controller):
        data["zero_load_operation"] = code.zero_load_operation
    data["availability_calc"] = code.availability_calc
    data["operating_mode_mask"] = status_code_fields.parse_mask(code.op_mode_bits or None)
    data["task_call_frequency"] = code.task_call_frequency
    data["user_groups"] = {
        slot: {"read": levels["read"], "write": levels["write"]}
        for slot, levels in code.user_groups.items()
        if "read" in levels and "write" in levels
    }
    return data


def _dependency_number(
    code: stcd.StatusCode, number: int, table: MappingTable | None
) -> int | None:
    """The new number of a program the set condition refers to. Main Controller programs refer to
    current numbers; a Hub Controller program refers to legacy numbers."""
    if code.controller == "MC":
        return number
    row = table.for_hub(number) if table is not None else None
    if row is not None:
        return row.new_number
    return None


# ------------------------------------------------------------------------------ the service
def _hc_flag(controller_choice: str) -> bool | None:
    return {"auto": None, "MC": False, "HC": True}[controller_choice]


def _mapping() -> MappingTable:
    return MappingService.table()


def _summary(items: list[Evaluated], file_count: int) -> dict[str, int]:
    states = [i.view["state"] for i in items]
    return {
        "files": file_count,
        "programs": len(items),
        "ready": states.count("ready"),
        "exists": states.count("exists"),
        "blocked": states.count("blocked"),
        "changed": states.count("changed"),
        "restorable": states.count("restorable"),
        "warnings": sum(len(i.view["warnings"]) for i in items),
        "with_legacy": sum(1 for i in items if i.view["legacy_number"] is not None),
        "without_legacy": sum(1 for i in items if i.view["legacy_number"] is None),
    }


class StImportService:
    # ------------------------------------------------------------------ preview
    @staticmethod
    def preview(
        uploads: list[tuple[str, bytes]], actor, options: dict | None = None
    ) -> dict[str, Any]:
        """Parses and checks the uploaded programs; writes only the staged copy."""
        require_roles(actor, "ADMINISTRATOR", "ENGINEER")
        opts = _clean_options(options)
        files, notes = expand_uploads(uploads)
        _purge_old_staging()

        token = secrets.token_hex(16)
        directory = _staging_dir(token)
        directory.mkdir(parents=True)
        manifest: dict[str, Any] = {
            "user_id": actor.id,
            "created": time.time(),
            "options": opts,
            "files": [],
        }
        parsed: list[tuple[int, str, str, list[stcd.StatusCode]]] = []
        file_errors: list[dict[str, str]] = []
        for index, (name, content) in enumerate(files):
            try:
                programs, sha = stcd.parse_bytes(content, name, _hc_flag(opts["controller"]))
            except stcd.StParseError as exc:
                file_errors.append({"file": name, "message": str(exc)})
                continue
            if not programs:
                file_errors.append({"file": name, "message": "No PROGRAM StCd_<n> found."})
                continue
            (directory / f"{index}.st").write_bytes(content)
            manifest["files"].append({"index": index, "name": name, "sha256": sha})
            parsed.append((index, name, sha, programs))
        if not parsed:
            shutil.rmtree(directory, ignore_errors=True)
            raise ValueError(
                "None of the files holds a status code program. "
                + "; ".join(f"{e['file']}: {e['message']}" for e in file_errors[:3])
            )
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        items = _evaluate(parsed, opts, _mapping())
        return {
            "token": token,
            "options": opts,
            "summary": _summary(items, len(parsed)),
            "items": [i.view for i in items],
            "file_errors": file_errors,
            "notes": notes,
            "expires_hours": STAGING_HOURS,
        }

    @staticmethod
    def _load_staged(token: str, actor) -> tuple[dict, list]:
        directory = _staging_dir(token)
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            raise StagingError("The preview has expired or is unknown. Upload the files again.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["user_id"] != actor.id:
            raise ForbiddenError("This preview belongs to another user.")
        if time.time() - manifest["created"] > STAGING_HOURS * 3600:
            shutil.rmtree(directory, ignore_errors=True)
            raise StagingError("The preview has expired. Upload the files again.")
        opts = manifest["options"]
        parsed = []
        for entry in manifest["files"]:
            content = (directory / f"{entry['index']}.st").read_bytes()
            programs, sha = stcd.parse_bytes(content, entry["name"], _hc_flag(opts["controller"]))
            if sha != entry["sha256"]:
                raise StagingError("A staged file changed after the preview. Upload again.")
            parsed.append((entry["index"], entry["name"], sha, programs))
        return manifest, parsed

    # ------------------------------------------------------------------ confirm
    @staticmethod
    def confirm(
        token: str,
        actor,
        selected: list[str] | None = None,
        *,
        change_set_name: str | None = None,
        asynchronous: bool | None = None,
    ) -> ImportJob:
        """Creates the Drafts for the chosen programs (`selected` = keys of the preview; None
        takes every program that is ready). The programs are checked again against the mapping
        as it is now."""
        require_roles(actor, "ADMINISTRATOR", "ENGINEER")
        manifest, parsed = StImportService._load_staged(token, actor)
        opts = manifest["options"]
        items = _evaluate(parsed, opts, _mapping())
        by_key = {i.view["key"]: i for i in items}
        if selected is None:
            chosen = [i for i in items if i.view["state"] == "ready"]
        else:
            unknown = [k for k in selected if k not in by_key]
            if unknown:
                raise ValueError("Not part of this preview: " + ", ".join(unknown[:5]))
            chosen = [by_key[k] for k in dict.fromkeys(selected)]
            not_ready = [
                i.view["key"]
                for i in chosen
                if i.view["state"] not in ("ready", "changed", "restorable")
            ]
            if not_ready:
                raise ValueError(
                    "These programs cannot be imported any more (already present or blocked): "
                    + ", ".join(not_ready[:5])
                    + ". Preview the files again."
                )
        if not chosen:
            raise ValueError("Nothing selected: tick at least one program that is ready.")
        job = ImportJob(
            requested_by=actor.id,
            source_format="ST",
            source_file_reference="",
            row_count=len(chosen),
            status="PENDING",
            import_mode="CREATE",
            created_at=utcnow_iso(),
        )
        db.session.add(job)
        db.session.commit()  # durable before per-program processing, like the CSV import

        import_dir = Path(current_app.instance_path) / "imports" / str(job.id)
        import_dir.mkdir(parents=True, exist_ok=True)
        used = {i.code.file for i in chosen if i.code is not None}
        staged = _staging_dir(token)
        for entry in manifest["files"]:
            if entry["name"] in used:
                shutil.copyfile(staged / f"{entry['index']}.st", import_dir / entry["name"])
        job.source_file_reference = str(import_dir)

        name = (change_set_name or "").strip() or f"ST import {job.id} ({utcnow_iso()[:10]})"
        change_set = ChangeSetService.create(
            name,
            f"Status codes imported from {len(used)} StCd file(s) by import job {job.id}.",
            None,
            actor,
        )
        job.change_set_id = change_set.id
        AuditService.log(
            "ImportJob",
            job.id,
            "IMPORT_STARTED",
            actor=actor,
            after={
                "source_format": "ST",
                "row_count": len(chosen),
                "mode": "CREATE",
                "files": sorted(used),
                "change_set_id": change_set.id,
            },
        )
        db.session.commit()
        shutil.rmtree(staged, ignore_errors=True)

        work = [
            {
                "key": i.view["key"],
                "file": i.code.file,  # type: ignore[union-attr]
                "sha256": i.sha256,
                "program_number": i.view["program_number"],
                "controller": i.view["controller"],
                "line": i.view["line"],
                "identifier": i.view["identifier"],
                "action": i.action,
                "status_code_id": i.status_code_id,
                "prg_idx": i.prg_idx,
                "data": i.data,
                "parsed": i.code.as_dict(),  # type: ignore[union-attr]
                "warnings": list(i.view["warnings"]),
            }
            for i in chosen
        ]
        threshold = current_app.config.get("IMPORT_ASYNC_ROW_THRESHOLD", 300)
        run_async = asynchronous if asynchronous is not None else len(work) > threshold
        if not run_async or current_app.config.get("IMPORT_ASYNC_INLINE"):
            return StImportService._process(job.id, work, actor)

        app = current_app._get_current_object()  # type: ignore[attr-defined]
        actor_id = actor.id

        def worker() -> None:
            with app.app_context():
                from app.auth.providers import AuthenticatedUser

                user = db.session.get(User, actor_id)
                if user is None:
                    return
                try:
                    StImportService._process(job.id, work, AuthenticatedUser.from_model(user))
                except Exception:  # noqa: BLE001  (the job row already records FAILED)
                    current_app.logger.exception("ST import job %s failed", job.id)
                finally:
                    db.session.remove()

        threading.Thread(target=worker, name=f"st-import-{job.id}", daemon=True).start()
        return job

    @staticmethod
    def discard(token: str, actor) -> None:
        """Removes a staged upload (the user left the preview)."""
        directory = _staging_dir(token)
        manifest_path = directory / "manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest["user_id"] != actor.id and actor.role_code != "ADMINISTRATOR":
                raise ForbiddenError("This preview belongs to another user.")
        shutil.rmtree(directory, ignore_errors=True)

    # ------------------------------------------------------------------ processing
    @staticmethod
    def _apply(item: dict, job_id: int, actor):
        """One program: a new Draft, the open Draft updated in place, or a new revision (of a code
        that is Approved or Released, or whose change request was withdrawn)."""
        action = item["action"]
        if action == "create":
            return StatusCodeService.create_draft(
                item["data"],
                actor,
                import_job_id=job_id,
                reserved_identifier=item["identifier"],
                prg_idx=item["prg_idx"],
            )
        current = StatusCodeService._repo.get_current_revision(item["status_code_id"])
        if action == "update":
            if current is None or current.lifecycle_status != "DRAFT":
                raise DomainError("The code is no longer an open Draft; preview the files again.")
            StatusCodeService.update_draft(current.id, item["data"], actor)
            return current
        revision = StatusCodeService.create_revision(item["status_code_id"], item["data"], actor)
        cr = db.session.query(ChangeRequest).filter_by(status_code_revision_id=revision.id).one()
        cr.import_job_id = job_id
        db.session.commit()
        return revision

    @staticmethod
    def _process(job_id: int, work: list[dict], actor) -> ImportJob:
        from sqlalchemy.exc import DBAPIError

        job = ImportService._load_job(job_id)
        job.status = "VALIDATING"
        db.session.commit()
        change_set_id = job.change_set_id

        results: list[RowResult] = []
        created = 0
        for index, item in enumerate(work, start=1):
            result = RowResult(row=index, identifier=item["identifier"])
            try:
                revision = StImportService._apply(item, job_id, actor)
                if item["action"] in ("create", "restore"):
                    MappingService.mark_issued(_identifier_number(item["identifier"]), actor)
                cr = (
                    db.session.query(ChangeRequest)
                    .filter_by(status_code_revision_id=revision.id)
                    .one()
                )
                if cr.change_set_id is None:  # a Draft updated in place may sit in another set
                    ChangeSetService.add_cr(change_set_id, cr.id, actor)
                db.session.add(
                    ImportSourceItem(
                        import_job_id=job_id,
                        status_code_id=revision.status_code_id,
                        source_file=Path(item["file"]).name,
                        source_sha256=item["sha256"],
                        program_number=item["program_number"],
                        controller=item["controller"],
                        source_line=item["line"],
                        parsed_json=json.dumps(item["parsed"], ensure_ascii=False, default=str),
                    )
                )
                db.session.commit()
                result.action = item["action"]
                result.warnings = item["warnings"]
                created += 1
            except (ValidationFailed, ValueError, DomainError, DBAPIError) as exc:
                db.session.rollback()
                result = RowResult(row=index, identifier=item["identifier"])
                if isinstance(exc, ValidationFailed):
                    result.issues = [
                        Issue(e["field"], item["identifier"], e["message"])
                        for e in exc.field_errors
                    ]
                else:
                    message = (
                        "The database refused the code: " + str(getattr(exc, "orig", exc))
                        if isinstance(exc, DBAPIError)
                        else str(exc)
                    )
                    result.issues = [Issue("identifier", item["identifier"], message)]
            except Exception:
                db.session.rollback()
                job = ImportService._load_job(job_id)
                job.status = "FAILED"
                job.created_count = created
                job.error_count = sum(1 for r in results if r.issues)
                job.completed_at = utcnow_iso()
                AuditService.log(
                    "ImportJob",
                    job.id,
                    "IMPORT_FAILED",
                    actor=actor,
                    after={"created_count": created, "failed_at_row": index},
                )
                db.session.commit()
                raise
            results.append(result)
            if index % 10 == 0 or index == len(work):
                job = ImportService._load_job(job_id)
                job.processed_count = len(results)
                db.session.commit()

        job = ImportService._load_job(job_id)
        errors = [r for r in results if r.issues]
        job.created_count = created
        job.error_count = len(errors)
        job.warning_count = sum(len(r.warnings) for r in results)
        job.processed_count = len(results)
        job.status = "COMPLETE"
        job.completed_at = utcnow_iso()
        if errors:
            ImportService._write_error_reports(Path(job.source_file_reference), errors, job)
        AuditService.log(
            "ImportJob",
            job.id,
            "IMPORT_COMPLETED",
            actor=actor,
            after={
                "source_format": "ST",
                "row_count": job.row_count,
                "created_count": created,
                "error_count": len(errors),
                "warning_count": job.warning_count,
                "change_set_id": change_set_id,
                "mode": "CREATE",
            },
        )
        db.session.commit()
        return job

    # ------------------------------------------------------------------ provenance
    @staticmethod
    def source_of(status_code_id: int) -> dict[str, Any]:
        """Where a code came from: file, hash, program and every attribute the file held."""
        item = (
            db.session.query(ImportSourceItem)
            .filter_by(status_code_id=status_code_id)
            .order_by(ImportSourceItem.id.desc())
            .first()
        )
        if item is None:
            raise NotFoundError("This status code was not imported from a program file")
        return {
            "import_job_id": item.import_job_id,
            "source_file": item.source_file,
            "source_sha256": item.source_sha256,
            "program_number": item.program_number,
            "controller": item.controller,
            "source_line": item.source_line,
            "attributes": json.loads(item.parsed_json),
        }

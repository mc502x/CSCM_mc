# 06. Data Dictionary — CSCM Tool

Conventions: **Required** = enforced not-null at both UI and API before the entity can leave Draft (for revision fields) or at all times (for structural fields). Datatypes are given in SQLite-native terms with the logical type in parentheses where useful (see 07-database-design.md for full DDL).

**Resolved in v4 — software version (decision D-01):** the legacy tool scopes the whole table by a software version (`SW_1_1_1_4.2MW`). The governed model is now the ordered vocabulary `lookup_controller_software_version`, an inclusive from/to **range per revision** (`applies_from_version_id`, `applies_to_version_id`, either end open) and the set of versions a **Release targets** (`release_target_version`); see §2 and §6. The free-text `software_version` column stays for legacy rows and is informational only.

**v4 (2026-10-23):** the tables and fields added by the improvement pack are marked *(v4)*; §13 lists every new table. `docs/artifacts/schema.sql` is the executable definition (59 tables, 14 triggers) and a test fails if a fresh database and an upgraded one differ.

**v4.1 (2026-10-23) — fields read from the generated controller programs:** 14 generated `StCd_*.st` programs (Main Controller 1000–1010, Hub Controller 14000, 14005 and 14025) were compared field by field with the status code workbooks (Main and Hub, Customer and Service exports, the 4XM "Rise0B" workbook and the Hub numbering workbook). Everything the workbooks contain matched the generated programs for all 14 codes, with one exception (`ROTOR_BREAK`, §2f). They also showed what the workbooks do not carry: the block identification `PrgIdx_GUi` (§1), further subsystem programs and Hub programs (§2c.1), the operating-mode mask and other per-code parameters (§2f), and the numeric user-group levels (§2d). Fields added from this comparison are marked *(v4.1)*; migration `c9e2a4b6d815` brings an older database up to them, and the existing library has no values for them until they are imported from the generated programs. **Since v4.9 the application stores, shows, copies, compares and exports all of them and the program import fills them (FR-168); the controller rule of §2f is enforced for the new fields.**

**Provenance note (2026-09-17):** the field set, real value vocabularies, and Functional Subgroup names in this revision are grounded in an actual export of the live status code library (`New Statuscode for sharing.xlsx`, 897 rows across 9 sheets, one per Functional System Group) and the legacy tool's screenshot supplied by the user. Fields whose exact business meaning could not be determined from the export alone (the numeric "program" reference fields, and the leading `*` marker on delay values) are flagged **semantics TBD** rather than guessed.

## 1. `status_code` (StatusCode identity)

| Field | Description | Datatype | Required | Default | Validation | Allowed Values | Example |
|---|---|---|---|---|---|---|---|
| `id` | Surrogate primary key | INTEGER (PK) | Yes | auto | system-generated | — | `1042` |
| `status_code_identifier` | Human-readable governed identifier (StCd) | TEXT | No while Draft; Yes from Review onward | `NULL` | `^StCd-\d{5}$` (or `^StCd-T\d{5}$` for sandbox); unique once non-null; allocated atomically at Draft→Review (05-governance-handbook.md §2) | — | `StCd-01232` |
| `functional_system_group_id` | Classification + numbering band | INTEGER (FK → lookup_functional_system_group) | Yes | — | must be `is_active = true` | see §9 | `WCNV` (1000–1999) |
| `functional_subgroup_id` | Sub-classification + numbering sub-band | INTEGER (FK → lookup_functional_subgroup) | **Yes — never optional** (corrected 2026-09-17; was mistakenly nullable in the prior revision) | — | must belong to the selected `functional_system_group_id`; must be `is_active = true` | see §9a | `Converter` (010xx) |
| `is_sandbox` | Test/sandbox flag | INTEGER (bool) | Yes | `0` | Administrator-only to set `true` | `0`, `1` | `0` |
| `platform_variant_of_status_code_id` | Optional pointer to the originating code this one was split from across Turbine Platforms | INTEGER (FK → status_code.id, nullable) | No | `NULL` | must reference a different Status Code | — | `988` |
| `legacy_reference_number` | Free-text pointer to the pre-migration status code number, for traceability during library import (06-data-dictionary.md §12) | TEXT | No | `NULL` | — | — | `3000` (legacy "Status Code Number" from the source system) |
| `prg_idx` *(v4.1)* | `PrgIdx_GUi`: the block identification the generated program writes to the controller's global variable on entry and restores on exit, so the controller knows which block was running. Entered manually by an engineer; the tool records, validates and audits it and never allocates it | INTEGER | No while Draft or not yet imported; **Yes from Review onward** | `NULL` | 1–65535 (the generated program declares it `UINT`); unique among non-sandbox codes (`ux_status_code_prg_idx`); frozen once a revision of the code is Released, Deprecated or Archived, except the first assignment NULL → value (`trg_prevent_prg_idx_change_after_release`); every set or change is audited with its before and after value | — | `14066` (Main 1000), `18926` (Hub 14000) |
| `reserved_identifier` *(v4.2)* | The number an imported `StCd_<n>.st` program already carries, held for this Draft: the identifier issued at Submit for Review is exactly this one (FR-048q, BR-023). Set only by the status code import, never through the API payload | TEXT | No | `NULL` | `StCd-NNNNN`; unique; may not equal the identifier of another code (service and triggers) | — | `StCd-01000` |
| `withdrawn_at` *(v4.9)* | Set when the last revision of the code was withdrawn (BR-026); only such a code can be deleted (erased in place, `deleted_at`), by an Administrator, and a restore from the program file clears it | TEXT (UTC timestamp) | No | NULL | set by the withdrawal, never through the API |
| `deleted_at` *(v4.9.2)* | Set when an Administrator deletes a withdrawn code: the row stays (no id is reused, the audit entries keep one meaning) but the identifier, the reserved number, the legacy number and `prg_idx` are cleared | TEXT (UTC timestamp) | No | NULL | set by the deletion, never through the API |
| `owner_id` | Accountable engineer | INTEGER (FK → user.id) | Yes | creator's id | active user, Engineer or Administrator role | — | `14` |
| `created_at` | Row creation timestamp (UTC) | TEXT (ISO-8601) | Yes | `now()` | system-generated | — | `2026-03-02T09:14:00Z` |

**Why Functional Subgroup is mandatory:** every one of the 897 rows in the real export carries a `Functional Group Name` (subgroup) value — there is no "group-only, no subgroup" case in production data, and the business explicitly confirmed a code must never be created without one. An Engineer selecting only a Functional System Group at creation time is therefore an incomplete Draft, not a valid one; the Functional Subgroup dropdown blocks progression exactly like any other mandatory field (10-ui-ux-specification.md §4).

**PrgIdx_GUi *(v4.1)*:** the value exists only in the generated programs, not in any workbook, so the existing library holds `NULL` until it is imported from them. "Required from Review" is enforced by the service layer (not yet wired in the application) and backed up in the database by `trg_require_prg_idx_for_review`, which stays inert until the setting `status_code.require_prg_idx` is `1`; set it once the library carries its values and the form collects the field. Observed values: Main 14066–14253 (codes 1000–1010), Hub 18926, 18931 and 18993 (codes 14000, 14005, 14025). The two ranges do not overlap, so uniqueness is checked across both controllers; whether Main and Hub share one ID space or are separate PLC projects is open, and other programs of the controller also write `PrgIdx_GUi`, so the tool can only guarantee uniqueness among status codes. All 14 values fit `base + (n − first) + 21 × ⌊(n − first) / 10⌋`, where n is the code's legacy number (3000… for Main, 14000… for Hub); that may serve as a suggestion or a warning, never as a rule, because the number is entered by hand.

## 2. `status_code_revision` — descriptive, classification, and timing fields

| Field | Description | Datatype | Required | Default | Validation | Allowed Values | Example |
|---|---|---|---|---|---|---|---|
| `id` | Surrogate primary key | INTEGER (PK) | Yes | auto | system-generated | — | `5031` |
| `status_code_id` | Parent Status Code | INTEGER (FK) | Yes | — | must reference existing status_code | — | `1042` |
| `revision_number` | Sequential revision counter per Status Code | INTEGER | Yes | `1` | monotonic, never reused | ≥ 1 | `2` |
| `is_current` | Flags the single "current" revision per code | INTEGER (bool) | Yes | `1` | exactly one `true` per `status_code_id` | `0`, `1` | `1` |
| `title` | Short human-readable name | TEXT | Yes | — | 1–120 chars; must not equal Description | — | `Frequency converter not ready` |
| `description` | Full technical description of the condition (maps to the real export's `Description` column, which in production doubles as the short title — CSCM Tool splits it into `title` + a longer `description` for clarity; see open item in 00-INDEX.md) | TEXT | Yes | — | 10–4000 chars | — | `Frequency converter is not in a ready state; the converter has not completed its pre-charge and self-check sequence.` |
| `status_category` | Nature of the status (corrected 2026-09-17: real data uses exactly three values, not the six-value FAULT/WARNING/SAFETY/OPERATIONAL/MAINTENANCE/INFORMATION set previously assumed) | TEXT (enum) | Yes | — | — | `ERROR`, `WARNING`, `INFO` | `ERROR` |
| `software_version` | Firmware/software version this revision is associated with | TEXT | No (see note) | `NULL` | `^\d+\.\d+(\.\d+)?$` when present | — | `1.1.1.4.2MW` |
| `available_group` | Availability-accounting code (corrected 2026-09-17: real data is a numeric code, not a four-letter A–D group) | INTEGER | Yes | — | must appear in `lookup_available_group`'s currently-observed set (soft-validated — see note below) | observed: 1,2,4,5,6,9,11–16,18,20–25,27,28,30,32 (labels TBD, see §9c) | `27` |
| `alarm_flag` | Whether the condition raises an operator-facing alarm (corrected 2026-09-17: real data is a plain boolean, not a four-value Alarm Behaviour enum) | INTEGER (bool) | Yes | `0` | — | `0`, `1` | `1` |
| `set_delay` | Debounce delay before the condition is set/raised, as free text with unit (corrected 2026-09-17: real data is not a plain seconds integer) | TEXT | Yes | — | `^\*?\d+(\.\d+)?\s?(ms\|s\|min\|MIN\|h\|d)$` | — | `10ms`, `*500ms`, `2min` |
| `reset_delay` | Minimum time the condition must be clear before it resets | TEXT | Yes | — | same pattern as `set_delay` | — | `2min`, `*0 ms` |
| `up_down_counter` | Whether this status uses an up/down occurrence counter rather than a simple set/clear (new field, 2026-09-17) | INTEGER (bool) | Yes | `0` | — | `0`, `1` | `0` |
| `trigger_snapshot` | Whether occurrence of this status triggers a diagnostic data snapshot (new field, 2026-09-17) | INTEGER (bool) | Yes | `0` | — | `0`, `1` | `1` |
| `loadless_spinning_permitted` | Whether loadless rotor spinning is permitted while this status is active (new field, 2026-09-17) | INTEGER (bool) | Yes | `0` | — | `0`, `1` | `1` |
| `owner_id` | Accountable engineer for this revision | INTEGER (FK → user.id) | Yes | inherited | active user, Engineer/Administrator | — | `14` |
| `lifecycle_status` | Current governance state | TEXT (enum) | Yes | `DRAFT` | must follow valid transitions | `DRAFT`,`REVIEW`,`PENDING_APPROVAL`,`APPROVED`,`RELEASED`,`DEPRECATED`,`ARCHIVED` | `PENDING_APPROVAL` |
| `created_by` | Engineer who authored this revision | INTEGER (FK → user.id) | Yes | current user | — | — | `14` |
| `created_at` | Revision creation timestamp | TEXT (ISO-8601) | Yes | `now()` | — | — | `2026-03-02T09:14:00Z` |
| `reviewer_signoff_by` / `_at` | Reviewer (Sub-PO for StCd) sign-off | INTEGER (FK → user.id) / TEXT | No | `NULL` | ≠ `created_by` | — | `22` |
| `admin_signoff_by` / `_at` | Administrator (Product Owner) sign-off | INTEGER (FK → user.id) / TEXT | No | `NULL` | ≠ `created_by` | — | `2` |
| `chief_engineer_approved_by` / `_date` | Chief Engineer final approval | INTEGER (FK → user.id) / TEXT | No | `NULL` | ≠ `created_by`, `reviewer_signoff_by`, `admin_signoff_by` | — | `31` |
| `effective_date` | Date the revision became Released | TEXT (ISO-8601) | No | `NULL` | set only at Release publish | — | `2026-03-15T00:00:00Z` |
| `deprecated_reason` | Why the code was deprecated | TEXT | Required if `lifecycle_status = DEPRECATED` | `NULL` | 10–2000 chars when present | — | — |
| `superseded_by_status_code_id` | Optional pointer to replacement code | INTEGER (FK → status_code.id) | No | `NULL` | must reference a different Status Code | — | `1090` |
| `row_version` *(v4)* | Optimistic-concurrency counter; increases on every save (FR-090) | INTEGER | Yes | `1` | a save naming an older `expected_row_version` is refused (409) | ≥ 1 | `3` |
| `updated_at` *(v4)* | Time of the last save | TEXT (ISO-8601) | No | `NULL` | system-generated; an older `expected_updated_at` is refused | — | `2026-10-20T08:00:00.000Z` |
| `remedy_text` *(v4)* | Recommended action for service staff (FR-131) | TEXT | No | `NULL` | ≤ 4000 chars | — | `Reset the converter, then check the DC-link fuse.` |
| `affected_component` *(v4)* | Subsystem or component concerned | TEXT | No | `NULL` | ≤ 200 chars | — | `DC link` |
| `related_status_codes` *(v4)* | Related codes, comma separated; soft-checked (FR-091) | TEXT | No | `NULL` | ≤ 500 chars; each `StCd-NNNNN` | — | `StCd-01040, StCd-01041` |
| `standard_references` *(v4)* | Applicable standards | TEXT | No | `NULL` | ≤ 1000 chars | — | `IEC 61400-25` |
| `applies_from_version_id` / `applies_to_version_id` *(v4)* | Inclusive software-version range the code applies to; either end open (D-01) | INTEGER (FK → lookup_controller_software_version) | No | `NULL` | the order is the vocabulary's `sort_order` | — | `4.1` … `4.3` |
| `planned_effective_date` / `planned_deprecation_date` *(v4)* | Planned dates, informational (FR-109, BR-021) | TEXT (`YYYY-MM-DD`) | No | `NULL` | ISO date; set by an Administrator, audited | — | `2027-03-31` |

## 2a. Field-to-Engineering-Domain Ownership

Principle (05-governance-handbook.md §6a); the v4 content fields (`remedy_text`, `affected_component`, `related_status_codes`, `standard_references`, the version range and the planned dates) have an "Any" owner and never gate Submit-for-Review. `title`, `description`, `status_category`, `available_group` are domain-agnostic ("Any"); timing fields (`set_delay`, `reset_delay`, `up_down_counter`, `trigger_snapshot`), the repeated-error fields (§2b), and the program reference fields (§2c) are owned by `CONTROLS`. The eight audience/access fields (§2d) are Governance-confirmed, following the same propose-by-Engineer/confirm-by-Administrator pattern as the old restricted `access_rights_id` field. *(v4.1)* `prg_idx`, the further program fields, the operation flags, the operating-mode mask, the task call frequency and the availability-calculation flag are owned by `CONTROLS` as well; the user-group levels (§2d) follow the audience fields.

## 2b. Repeated-Error Escalation Fields

| Field | Description | Datatype | Required | Default | Validation | Example |
|---|---|---|---|---|---|---|
| `number_of_times_repeated` | How many occurrences within the window (below) before escalation | INTEGER | No | `NULL` | ≥ 1 when set | `10` |
| `repeated_over_the_course` | The window duration, free text with unit | TEXT | No | `NULL` | `^\d+(\.\d+)?\s?(s\|min\|h\|d)$` | `1d` |
| `status_code_for_repeated_error` | The escalation code raised once the repeat threshold is hit | INTEGER | No | `NULL` | **Not a foreign key to `status_code`** — confirmed 2026-09-17 to reference a separate, unrelated numeric code pool outside StCd governance (e.g. a fixed system/SCADA alarm code). Stored and displayed as an opaque reference number; CSCM Tool does not validate it against any internal table. | `455` |

All three are optional together — a status code with no repeat-escalation behavior leaves all three `NULL`.

## 2c. Program Reference Fields (numeric, externally defined — semantics TBD)

These fields reference controller-firmware program/subroutine numbers maintained **outside** CSCM Tool (in the Main/Hub Controller codebase itself), not a CSCM Tool-governed vocabulary. CSCM Tool stores and soft-validates them against the currently-observed set below (a warning, not a hard block, since the firmware-side table can gain new program numbers CSCM Tool doesn't yet know about) rather than enforcing a closed lookup. **The descriptive meaning of each numeric code is not available from the source export and must be confirmed with Controls Engineering before these can be upgraded to labeled lookups.**

| Field | Description | Datatype | Required | Default | Observed values |
|---|---|---|---|---|---|
| `yaw_program` | Yaw subprogram reference | INTEGER | Yes | `0` | 0,1,3,5,10,13,15,20,30,50,70,240 |
| `manual_reset_program` | Manual reset subprogram reference | INTEGER | Yes | `0` | 0,5,10,20 |
| `auto_reset_program` | Automatic reset subprogram reference | INTEGER | Yes | `0` | 0,10,20,30 |
| `converter_reactive_power_program` | Converter reactive-power subprogram reference | INTEGER | Yes | `0` | 0,10,20 |
| `brake_program` | Brake subprogram reference (replaces the invented BP-NONE/BP-1…4 enum) | INTEGER | Yes | `0` | 0,20,50,52,60,75,170,180,190,... |
| `umrichterprogramm_gsc` | Converter program, grid-side converter (GSC) | INTEGER | Yes | `0` | 0,10,20,30 |
| `umrichterprogramm_msc` | Converter program, machine-side converter (MSC) | INTEGER | Yes | `0` | 0,6,10,15,20 |
| `yaw_bearing_lubrication_program` | Yaw bearing lubrication subprogram reference | INTEGER | Yes | `0` | 0,10 |

This replaces the prior revision's single `reset_program_id`/`brake_program_id` enum FKs entirely — real data has **two** distinct reset-program fields (manual and automatic), not one, and brake/converter/yaw programs are numeric passthroughs, not a small named enum.

### 2c.1 All program fields and where they come from *(v4.1)*

The generated programs hold one array per subsystem (`…PrgArUs[Idx]`); the 4XM workbook renamed them (sheet "Naming Conventions", `…Lev`). Each is a numeric reference into the controller firmware, 0 meaning the code does not act on that subsystem. **Applies to:** M = Main Controller, H = Hub Controller. Not-applicable fields stay 0 (§2f).

| Column | 4XM name | Generated array | Applies to | Notes |
|---|---|---|---|---|
| `manual_reset_program` | Manual Reset Program | `ManResetPrgArUs` | M, H | 0, 5, 10, 20 |
| `auto_reset_program` | Auto Reset Program | `AutoResetPrgArUs` | M, H | 10 = reset after the reset delay whatever the condition; 20 = reset once the set condition is gone; 30 = reset on the code's own reset condition; 0 = never. A reset is also held back while the brake program check (`CheckBP`) fails and, for codes with a repeat limit, once the limit is reached |
| `brake_program` | `BrkLev` (Main), "Stop Program" (Hub workbooks) | `BrakePrgArUs` | M, H | One field: the Hub "Stop Program" (0, 40, 80) matched `BrakePrgArUs` in all 3 Hub programs |
| `yaw_program` | `YwLev` | `AzimutPrgArUs` | M | |
| `converter_reactive_power_program` | `ConvQLev` | `QConverterPrgArUs` | M | |
| `umrichterprogramm_msc` | `ConvMscLev` | `ConverterMSCPrgArUs` | M | machine-side converter |
| `umrichterprogramm_gsc` | `ConvGscLev` | `ConverterGSCPrgArUs` | M | grid-side converter |
| `yaw_bearing_lubrication_program` | `YwBrgLuLev` | `YawLubPrgArUs` | M | |
| `converter_reset_program` *(v4.1)* | `ConvRstLev` | `ResetConverterPrgArUs` | M | |
| `hydraulic_pump_program` *(v4.1)* | `HyPmpLev` | `HydraulicPrgArUs` | M | |
| `gearbox_oil_pump_program` *(v4.1)* | `GbxOilPmpLev` | `GearOilPumpPrgArUs` | M | |
| `gearbox_oil_fan_program` *(v4.1)* | `GbxOilFanLev` | `GearOilCoolingPrgArUs` | M | |
| `gearbox_oil_heating_program` *(v4.1)* | `GbxOilHtLev` | `GearHeatingPrgArUs` | M | |
| `generator_fan_program` *(v4.1)* | `GnFanLev` | `GenFanPrgArUs` | M | |
| `generator_heating_program` *(v4.1)* | `GnHtLev` | `GenHeatingPrgArUs` | M | |
| `generator_bearing_lubrication_program` *(v4.1)* | `GnBrgLuLev` | `GenoLubPrgArUs` | M | |
| `rotor_bearing_lubrication_program` *(v4.1)* | `RotBrgLuLev` | `RotBearLubPrgArUs` | M | |
| `anemometer_heating_program` *(v4.1)* | `AneHtLev` | `VaneAneHeatPrgArUs` | M | |
| `medium_voltage_cb_program` *(v4.1)* | `MedCBLev` | `MeanVoltageCBPrgArUs` | M | the generated name says "Mean"; read as a mistranslation of Mittelspannung (medium voltage), to be confirmed |
| `tower_fan_program` *(v4.1)* | `TowFanLev` | `TowerFanPrgArUs` | M | |
| `transformer_oil_pump_program` *(v4.1)* | `TrfOilPmpLev` | `TrafoPumpPrgArUs` | M | |
| `pitch_error_program` *(v4.1)* | Pitch Error Program | `PtErrOpPrgArUs` | H | 0, 20 in the Hub workbook; 0 in all three programs read |
| `pitch_warning_program` *(v4.1)* | Pitch Warning Program | `PtWarnOpPrgArUs` | H | 0 in all three programs read |
| `rotor_brake_program` *(v4.1)* | `ROTOR_BREAK` (Hub service export) | `RotorBrakePrgArUs` | H | 20 for rotor overspeed (14000) in the generated program, while the export shows 0 for all 265 Hub rows: the export loses the value |

The 4XM sheet names a 20th entry `AvlLev` with the old name "Not Available"; no generated array corresponds to it and its meaning is unknown, so it is not modelled. The 13 further Main columns are optional in the sense that 0 is a valid value; no allowed-value list is known for them yet, so, like the existing program fields, they are stored and soft-validated only.

## 2d. Audience / Access Fields (replaces the single `access_rights_id` enum)

Corrected 2026-09-17 per explicit decision: each of the eight audiences in the real export is an **independent** field with its own lookup-backed vocabulary, not one shared "Access Rights" level. A status code can simultaneously carry different values for different audiences (e.g. `service_access = "Commissioning"` while `customer_access = "See only"`). Each Engineer-proposed value is confirmed or overridden at the Administrator's Review sign-off, following the same restricted-field pattern as before (04-domain-model.md §2.9).

| Field | Datatype | Required | Default | Lookup | Example |
|---|---|---|---|---|---|
| `development_access` | INTEGER (FK → lookup_development_access) | No | `NULL` | §9d.1 | `SCADA User` |
| `sales_access` | INTEGER (FK → lookup_sales_access) | No | `NULL` | §9d.2 | `See only` |
| `tcc_access` | INTEGER (FK → lookup_tcc_access) | No | `NULL` | §9d.3 | `Telenotdienst` |
| `service_access` | INTEGER (FK → lookup_service_access) | No | `NULL` | §9d.4 | `Service and Maintenance` |
| `turbine_operator_package_access` | INTEGER (FK → lookup_top_access) | No | `NULL` | §9d.5 | `Preventive Maintenance` |
| `grid_operator_access` | INTEGER (FK → lookup_grid_operator_access) | No | `NULL` | §9d.6 | `See only` |
| `service_partner_access` | INTEGER (FK → lookup_service_partner_access) | No | `NULL` | §9d.7 | `Ext. Service Provider` |
| `customer_access` | INTEGER (FK → lookup_customer_access) | No | `NULL` | §9d.8 | `Professional` |

**Visibility (v4, decision D-02):** every row of the eight access vocabularies (§9d) carries `audience_visible` (INTEGER 0/1, NOT NULL). An audience export contains a code only when the Administrator-confirmed value for that audience has `audience_visible = 1`; a code with no value for the audience is hidden; the seeded value `Covert` has `audience_visible = 0` (BR-016).

### 2d.1 Numeric user-group levels *(v4.1)*

The generated programs do not store the named audience values; they store a read level and a write level (BYTE) for each of 16 user-group slots (`UserGroupReadArBy[Idx, slot]`, `UserGroupWriteArBy[Idx, slot]`). **Slots 1–8 are the eight audiences in the order of the export columns** (`lookup_user_group_slot`): 1 Development, 2 Sales, 3 TCC, 4 Service, 5 Turbine Operator Package, 6 Grid Operator, 7 Service Partner, 8 Customer. This held wherever it could be checked: on 6 programs for all eight audiences (a `Covert` value is read level 50 in exactly the slot of its audience) and on all 11 Main programs for the Turbine Operator Package and Service Partner slots, where the write level follows the named value. Slot 13 is never written; slots 0 and 9–15 were 50/50 in every sample (slot 9 reads 1 on Main and 50 on Hub codes, so it may mean something) and stay unassigned until Controls Engineering names them.

Observed levels: read is 1 (readable) or 50 (no access); write is 50 (no write access) or one of 5, 10, 12, 15, 20. A named value does not always fix the number: `See only` is 1/50 and `Covert` 50/50 for every audience seen, `Preventive Maintenance` 1/10, `Troubleshooting` 1/15, `Ext. Service Provider` 1/15, `Customer after warranty Advanced` 1/10 and Development `Operation Control` 1/20 each held on every code that carried them, but `Service and Maintenance` was 20 on one Main code and 10 on another, and `Telenotdienst` 10 on one and 20 on another. So the levels are stored per revision in `status_code_revision_user_group` (one row per slot, `read_level` and `write_level` 0–255) and the eight audience fields stay the human-readable layer. `default_read_level` and `default_write_level` on the access lookups (§9d.9) pre-fill the numbers when a named value is chosen; the Engineer may override them, and a value without a default must be entered. The existing revisions get no rows: their numbers cannot be derived from the named values for every code, so they arrive with the import from the generated programs.

**Value normalization:** the raw export contains inconsistent casing (`See Only` vs `See only`) and one apparent typo (`ProfessionaProfessional`). The lookups in §9d.1–§9d.8 are seeded with the corrected, de-duplicated values; the typo is normalized to `Professional`.

## 2e. Technical Addressing Fields (derived, read-only)

| Field | Description | Datatype | Required | Default | Notes |
|---|---|---|---|---|---|
| `logical_node` | Controller addressing identifier | TEXT | Yes | derived | Always equals the parent Status Code's Functional System Group prefix (e.g. `WCNV`) — auto-populated, never independently entered; confirmed by the real export where this column exactly mirrors the sheet's group. |
| `node_value` | Controller addressing index | INTEGER | Yes | derived | Always equals the parent Functional System Group's `sort_order` (1–9) — auto-populated. |

Both fields exist in the real export as their own columns (presumably for direct firmware/SCADA tag generation) but carry no information beyond what the Functional System Group already encodes; CSCM Tool derives and displays them rather than accepting manual entry, to guarantee they can never drift out of sync with the group assignment.

## 2f. Main Controller and Hub Controller fields *(v4.1)*

The controller of a code is the `controller_type` (`MAIN` | `HUB`) of its Functional System Group. Compared field by field, the Main workbooks, the Hub workbooks and the generated programs of both controllers give this split.

| Fields | Main | Hub | Notes |
|---|---|---|---|
| Identity and classification (`title`, `description`, `status_category`, `available_group`, group and subgroup), `trigger_snapshot`, `set_delay`, `reset_delay`, `up_down_counter`, the repeat fields, `manual_reset_program`, `auto_reset_program`, `brake_program`, the eight audience fields, the user-group levels | yes | yes | `brake_program` is the Hub "Stop Program" (§2c.1). The repeat-escalation code is 9084–9090 on Main and 10050 on Hub |
| `alarm_flag` | yes | yes | the Hub generated programs carry it (FALSE in all 3) although no Hub workbook has the column; a Hub import therefore leaves it at 0 |
| `operating_mode_mask`, `task_call_frequency`, `availability_calc` | yes | yes | the mask is 20 bits on Main and 6 bits on Hub; `availability_calc` was TRUE on all 11 Main codes and FALSE on the 3 Hub codes (all Available Group 7); none of the three is in any workbook |
| `yaw_program`, `converter_reactive_power_program`, `umrichterprogramm_gsc`, `umrichterprogramm_msc`, `yaw_bearing_lubrication_program` and the 13 further subsystem programs (§2c.1) | yes | no | the Hub programs have no such arrays |
| `loadless_spinning_permitted`, `zero_load_operation` | yes | no | the Hub programs have no zero-load handling. `loadless_spinning_permitted` is `ZeroLoadPrg_ArBo`: the workbook value matched it on all 11 Main codes (FALSE only for 1002, 1009, 1010). `zero_load_operation` is `ZeroLoadOperation_ArBo` (may the code be set while zero-load operation is active; TRUE for all but 1008) and appears in no workbook |
| `pitch_error_program`, `pitch_warning_program`, `rotor_brake_program` | no | yes | |
| `stop_program_40_flag`, `stop_program_80_flag`, `manual_operation_flag`, `automatic_operation_flag`, `vane_position_flag` | no | yes | see below |
| `logical_node`, `node_value` | derived | derived | the Hub export has the group id (11, 12, 13) in its group sheet instead of a node value |

**Rules:** a field that does not apply to the controller of the code is stored as 0 (programs) or `NULL` (flags and parameters) and is not offered in the form; the service layer rejects any other value for it. The database stays permissive here, so a later controller generation can reuse a column without a schema change. Exports use the controller's own header (Hub: "Stop Program" for `brake_program`).

**The five Hub flags and the mask:** all three Hub programs read have `OpModeArDw := 2#111011` (five bits set, one clear) and all five flags True, and 244 of the 265 Hub codes in the workbook have all five True, which suggests the flags are decoded from five of the six bits. The bit order is not verified, so until it is the mask and the flags are captured independently and neither is derived from the other. The programs of the Hub codes with a different flag pattern would settle it: workbook numbers 7027, 10070, 12511, 13511, 13901 and 10250.

**Descriptive text:** the workbooks carry `Cause` on both controllers and `Directive` on the Hub; the tool has no column of either. Proposed mapping, to be confirmed: `Directive` → `remedy_text`, `Cause` → `description`. The generated programs carry the German short name in their header while the workbooks are English; `revision_translation` (§13) holds both languages.

## 3. `status_code_revision_platform` (Turbine Platform, multi-select)

At least one Turbine Platform must be selected before a revision can be submitted for Review.

| Field | Description | Datatype | Required | Default | Example |
|---|---|---|---|---|---|
| `id` | Surrogate PK | INTEGER | Yes | auto | `77` |
| `status_code_revision_id` | Parent revision | INTEGER (FK) | Yes | — | `5031` |
| `turbine_platform_id` | Applicable platform | INTEGER (FK → lookup_turbine_platform) | Yes | — | `3XM` |

## 4. `change_request`, `review_comment`, `domain_signoff`

Shape as in the prior revision (05-governance-handbook.md §7–§8 for the dual-review-then-Chief-Engineer-approval sequence these tables support), with these additions (2026-10-21, v4 2026-10-23):

- `change_request.change_set_id` *(v4)* (INTEGER, nullable, FK → `change_set`) — FR-124.

- `change_request.assigned_reviewer_id` (INTEGER, nullable, FK → `user`) — FR-039. An Administrator may assign, reassign, or unassign the Reviewer while the CR is in Draft/Review and the Reviewer has not yet signed; once set, only that Reviewer may record the Reviewer sign-off. The author can never be assigned (BR-005).
- `domain_signoff_request` (new table: `id`, `change_request_id`, `engineering_domain_id`, `requested_by`, `target_user_id` nullable, `created_at`; unique on CR + domain) — FR-028. The originating Engineer's explicit request for a pending domain's sign-off, optionally addressed to one Engineer holding that domain. It surfaces on the target's Dashboard and My Change Requests until a `domain_signoff` exists for that domain; an unaddressed request is visible to every Engineer holding the domain.

## 5. `import_job` (new — library import)

| Field | Description | Datatype | Required | Default | Validation | Example |
|---|---|---|---|---|---|---|
| `id` | Surrogate PK | INTEGER | Yes | auto | — | `12` |
| `requested_by` | Engineer or Administrator who initiated the import | INTEGER (FK → user.id) | Yes | current user | — | `14` |
| `source_format` | Format of the uploaded file; `ST` *(v4.2)* = generated `StCd_<n>.st` programs | TEXT (enum) | Yes | — | `CHECK IN ('CSV','XLSX','ST')` | `CSV`, `XLSX`, `ST` |
| `source_file_reference` | Path/pointer to the uploaded source file, retained for audit | TEXT | Yes | — | — | `/imports/12/source.csv` |
| `row_count` | Total rows in the source file | INTEGER | Yes | — | — | `134` |
| `status` | Job state | TEXT (enum) | Yes | `PENDING` | — | `PENDING`,`VALIDATING`,`COMPLETE`,`FAILED` |
| `created_count` | Number of rows successfully turned into Draft Change Requests | INTEGER | No | `0` | — | `128` |
| `error_count` | Number of rows that failed validation and were not imported | INTEGER | No | `0` | — | `6` |
| `error_report_reference` | Path/pointer to a downloadable per-row error report | TEXT | No | `NULL` | — | `/imports/12/errors.csv` |
| `created_at` | Job start timestamp | TEXT (ISO-8601) | Yes | `now()` | — | — |
| `completed_at` | Job completion timestamp | TEXT (ISO-8601) | No | `NULL` | — | — |
| `processed_count` *(v4)* | Rows processed so far (progress of a background job, FR-048n) | INTEGER | Yes | `0` | ≤ `row_count` | `60` |
| `warning_count` *(v4)* | Rows that imported with a warning (similar title, …) | INTEGER | Yes | `0` | — | `4` |
| `import_mode` *(v4)* | `CREATE` or `UPDATE` (FR-048k) | TEXT (enum) | Yes | `CREATE` | `CHECK IN ('CREATE','UPDATE')` | `UPDATE` |
| `error_report_xlsx_reference` *(v4)* | Path of the XLSX error report (FR-048m) | TEXT | No | `NULL` | — | `/imports/12/errors.xlsx` |
| `change_set_id` *(v4.2)* | The change set that holds the Drafts of a status code import from programs (FR-048t) | INTEGER (FK → change_set.id) | No | `NULL` | — | `7` |

**Governance note:** every row that successfully validates becomes a normal Draft `StatusCode`/`StatusCodeRevision`/`ChangeRequest` triple, exactly as if an Engineer had typed it in by hand — it still must pass Cross-Domain Sign-Off (if applicable), both Review sign-offs, and Chief Engineer approval before it can be Released. Import is a faster data-entry path, not a governance bypass (confirmed 2026-09-17; see 05-governance-handbook.md §6b).

## 5a. Status code import from generated programs *(v4.2)*

Docs: 03-srs.md §1.16, 05-governance-handbook.md §6b. The reader (`app/importers/stcd.py`) scans the text of each `PROGRAM StCd_<n>`; it never runs or compiles anything.

**What a program becomes.** The number the program carries becomes `status_code.reserved_identifier` (`StCd-` + five digits); the subgroup is the one whose band holds the number; the Drafts of one confirmation are collected in one `change_set` named on `import_job.change_set_id`. Hub Controller programs carry the *legacy* Hub number: it is stored as `legacy_reference_number`, and the new number comes from the numbering table (proposal 1, five digits, or proposal 2, inside the Main scheme).

| Program (file) | Catalogue field | Note |
|---|---|---|
| header `StCd: <legacy>, '<name>'` | `legacy_reference_number`, `title` | Main Controller only; a Hub program's legacy number is its file number |
| `StCdArUi[Idx]` | `reserved_identifier` | Main: the current number |
| `AvailabilityGroupArUs` | `available_group` | required |
| `AlarmArBo` | `alarm_flag` | |
| `SetTimer(PT := …)`, `ResetTimer(PT := …)` | `set_delay`, `reset_delay` | `T#10ms` → `10ms`, `T#120000ms` → `2min`; a variable (`StCd14000SetDelayGpTi`) or no timer → `0ms` with a warning |
| `MaxRepeatNbArBy`, `RepeatTimeArDw`, `RepeatStCdArUi` | `number_of_times_repeated`, `repeated_over_the_course` (`86400` s → `1d`), `status_code_for_repeated_error` | |
| `StCdWithSnap_Bo`, `ZeroLoadOperation_ArBo` | `trigger_snapshot`, `loadless_spinning_permitted` | |
| `AzimutPrgArUs`, `ManResetPrgArUs`, `AutoResetPrgArUs`, `QConverterPrgArUs`, `BrakePrgArUs`, `ConverterGSCPrgArUs`, `ConverterMSCPrgArUs`, `YawLubPrgArUs` | `yaw_program`, `manual_reset_program`, `auto_reset_program`, `converter_reactive_power_program`, `brake_program`, `umrichterprogramm_gsc`, `umrichterprogramm_msc`, `yaw_bearing_lubrication_program` | |
| other StCd programs named in the set condition | `related_status_codes` | Hub: legacy numbers translated to new ones |
| `PrgIdx_GUi` | `prg_idx` | stored only when free and 1–65535, otherwise a warning |
| everything else (user-group levels, remaining subsystem programs, operating-mode mask, …) | `import_source_item.parsed_json` | kept for the catalogue columns that wire them later (21-improvement-ideas.md) |
| *not in the file* | `status_category` (the uploader's choice for the batch), `description` (generated: file, legacy number, set condition), turbine platforms (the uploader's choice), the eight audience-access values (left empty) | |

**Provenance.** `import_source_item` holds one row per imported program: the file name, its SHA-256, program number and line, the controller and every parsed attribute as JSON. The files themselves are kept under `instance/imports/<job>/`.

**Legacy → new mapping.** There is no table of its own: the mapping is `status_code.legacy_reference_number` read with the Functional System Group's `controller_type` (`MAIN` → Main Controller, `HUB` → Hub Controller) and the identifier the code holds (`status_code_identifier`, or `reserved_identifier` while it is a Draft). A legacy number is unique per controller (the import blocks a second code with the same one). The direction is legacy → new only: the new library holds more codes than the old one, so a code without a legacy number is normal ("n/a") and nothing maps back (FR-048u).

**Guards.** The service checks the reservation first; the database backs it with the unique index `ux_status_code_reserved_identifier` and the triggers `trg_identifier_matches_reservation` (a reserved code can only be issued its own number), `trg_reservation_not_issued_elsewhere` (a reservation cannot be made for an identifier already issued) and `trg_identifier_not_reserved_elsewhere` (no code can be issued a number another code reserves).

## 6. `release` / `release_item`

`release` has the columns of `docs/artifacts/schema.sql`; *(v4)* `release_target_version` (`id`, `release_id`, `software_version_id`; unique per pair) records the controller software versions a Release is published for. It can be changed only while the Release is BUILDING (BR-007, BR-021).

## 7. `user` / `user_engineering_domain`

`user.email` *(v4.7)* is the stable identity of the person: it is entered when the account is created, stored in lower case, unique, and **cannot be changed** — the trigger `trg_user_email_immutable` aborts any update that changes it, and the service and the API refuse it first (FR-162). The Windows sign-in matches the identity of the gateway with this address (FR-163).

`user.ui_language` *(v4)* (TEXT, a two-letter lower-case language code, default `en`; the CHECK no longer lists the codes, the application decides which exist: `en`, `de`, `fr`, `hi`, `ka`, `ar`, `bn`, `mr`, `te`, `ta`, `gu`, `ur`, `kn`, `or`, `ml`, `pa`, `es`, `it`, `da`) is the interface language preference (FR-155, FR-157).

`user.deleted_at` *(v4.9)* (TEXT, UTC timestamp, NULL by default): set when an Administrator deletes an account that has history (BR-025). The user name, e-mail address and name are replaced (`deleted-<id>`, `deleted-<id>@deleted.invalid`, *Deleted user*), the password is destroyed and `is_active` is 0; the row stays so that every record and audit entry keeps its author. The list and every lookup of users leave such an account out. The trigger `trg_user_email_immutable` lets exactly this change of the address through.

**`user_password_history`** (added 2026-10-21): `id`, `user_id` (FK → `user`), `password_hash` (Argon2id hash of a retired password, never plaintext), `retired_at`. Written whenever a user's password is changed or reset; a new password is rejected if it matches the current one or any of the 4 most recently retired ones (the last 5 passwords, `11-security-architecture.md` §4).

## 8. `audit_log_entry` / `export_job`

`audit_log_entry` gains *(v4)* `prev_hash` and `entry_hash` (TEXT, 64 hex characters; the first row's `prev_hash` is 64 zeros, the literal `GENESIS`); `entry_hash` is SHA-256 — HMAC-SHA-256 when `AUDIT_HMAC_KEY` is set — over the canonical JSON of the row's other fields and `prev_hash` (AUD-074). Rows written before v4 are hashed by the migration.

`export_job.export_type` accepts `CSV`, `JSON`, `XLSX`, `PDF`, `SQLITE_BACKUP` and, since v4, `HTML`, `MD`, `ZIP`; `export_scope_type` is `CATALOGUE`, `FULL_DATABASE`, `RELEASE_NOTES` or `OFFLINE_BUNDLE`. v4 adds `sha256`, `size_bytes`, `row_count`, `profile_code`, `audience`, `language_code`, `software_version_code` and `manifest` (JSON text).

## 9. `lookup_functional_system_group`

**Important (2026-09-17): `code` is not a unique key.** The Hub Controller status code library (`HC Status Code Number.xlsx`, 264 rows) confirmed `WTUR` and `WROT` are each reused for a second, numerically distinct group — same thematic prefix, different status code range, confirmed explicitly by the business. Uniqueness is on `(code, range_start)`; always resolve a group by its numeric range, never by prefix alone (`artifacts/schema.sql`).

| code | label | range_start | range_end | Rows |
|---|---|---|---|---|
| `WCNV` | Converter & Grid Interface | 1000 | 1999 | 134 (2026-09-17 export) |
| `WGEN` | Generator System | 2000 | 2999 | 55 |
| `WNAC` | Meteorology & Nacelle Environment | 3000 | 3999 | 103 |
| `WROT` | Rotor & Pitch System | 4000 | 4999 | 165 |
| `WTOW` | Tower & Structure | 5000 | 5999 | 43 |
| `WTRF` | Transformer & MV System | 6000 | 6999 | 35 |
| `WTRM` | Drivetrain & Gearbox | 7000 | 7999 | 127 |
| `WYAW` | Yaw System | 8000 | 8999 | 33 |
| `WTUR` | Turbine Control & Operation | 9000 | 9999 | 202 |
| `WTUR` | Hub Controller Control System | 11000 | 11999 | 51 (Hub export) |
| `WROT` | Hub Controller Rotor & Pitch | 12000 | 12999 | 212 |
| `WPPD` | Wind Farm / Plant Dispatch | 13000 | 13999 | 1 |

**Confirmed reserved capacity (2026-09-17):** `10000–10999`, `14000–14999`, `15000–15999`, and `16000–16999` are explicitly free — deliberately available for a whole new Functional System Group, not an open question needing resolution (00-INDEX.md).

### 9.1 Administrator-Created Functional System Groups

New capability (2026-09-17), mirroring §9a.1 one level up: an Administrator can create a brand-new Functional System Group — code, label, and numeric range — into any free range above, without a schema change. The service layer validates the proposed range does not overlap any existing group's range and returns 409 naming the conflict if it does; a database trigger (`trg_prevent_group_overlap`, `artifacts/schema.sql`) backs this up. A new group can immediately have subgroups added underneath it via §9a.1.

## 9a. `lookup_functional_subgroup` — real names, from the live export

**Rule (2026-10-22):** the **first** subgroup of every Main Controller group covers the group's **first 200 numbers** — e.g. `050xx` Tower 5000–5199, `020xx` Generator 2000–2199 — so the later subgroups start at the next hundred pair (x200, …). The code prefixes (`010xx` …) are kept as stable identifiers for imports and legacy references even though each now spans two hundred-blocks. The Hub Controller groups keep their contiguous bands.

**Rule (2026-10-23) — Hub Controller bands and subgroup codes:** like the Main groups, every Hub subgroup is aligned to the hundreds digit of its prefix: `123xx` owns 12300–12399, and a band shorter than a hundred is named by its first ten with a digit in place of the second `x` (`1110x` is 11100–11149, `1115x` is 11150–11199, `1205x` starts at 12050). The same rule names the Main sub-bands of the 099xx hundred (`0990x` … `0999x`). A code has **no dash and no letter**: it is the digits of the first number of the band with `x` for the free positions, so a Hub code reads like a Main code (`110xx` next to `010xx`); migration `f6c8e0a2b459` renamed the earlier `11-1xxA`, `12-0xxB`, `099xx-a` and the like. The first seed copied the legacy export, which counts from x001 (so `12-3xx` was 12301–12400 and `11-0xx` was 11000–11100, 101 numbers); migration `a1d4f6b8c203` shifted each band down by one number. The *Observed usage* column below is the **legacy** numbering of the export — those numbers are kept in `legacy_reference_number`, they are not identifiers — and every observed row lies inside its aligned band. `test_hub_sub_bands_are_aligned_to_the_hundreds_of_their_prefix` and `test_subgroup_codes_have_no_dash_and_no_letter_after_the_x` keep this true.

**Correction (2026-09-17):** the subgroup names in the prior revision (sourced from a hand-typed summary table) did not match the authoritative row-level export, confirming the "Sub Group not named properly" issue raised by the business. The table below is built directly from the real `Functional Group Name` column of `New Statuscode for sharing.xlsx` and **supersedes** the earlier version. WTUR in particular has **nine** subgroups, not four, with six of them packed into narrow sub-bands within 9900–9999 rather than one hundred-block each.

| Subgroup Prefix | Group | Subgroup Name (real) | Declared sub-range | Observed usage |
|---|---|---|---|---|
| `010xx` | WCNV | Converter | 01000–01199 | 1000–1075 (76 rows) |
| `012xx` | WCNV | Grid | 01200–01299 | 1200–1257 (58 rows) |
| `020xx` | WGEN | Generator | 02000–02199 | 2000–2051 (52 rows) |
| `022xx` | WGEN | Protection | 02200–02299 | 2200–2202 (3 rows) |
| `030xx` | WNAC | Meteorology | 03000–03199 | 3000–3052 (53 rows) |
| `032xx` | WNAC | Nacelle | 03200–03299 | 3200–3249 (50 rows) |
| `040xx` | WROT | Rotor | 04000–04199 | 4000–4096 (97 rows) |
| `042xx` | WROT | Hot Air De-icing | 04200–04299 | 4200–4246 (47 rows) |
| `043xx` | WROT | Lighting | 04300–04399 | 4300–4304 (5 rows) |
| `044xx` | WROT | Blade Sensors | 04400–04499 | 4400–4415 (16 rows) |
| `050xx` | WTOW | Tower | 05000–05199 | 5000–5042 (43 rows) |
| `060xx` | WTRF | Switches | 06000–06199 | 6000–6007 (8 rows) |
| `062xx` | WTRF | Transformer | 06200–06299 | 6200–6226 (27 rows) |
| `070xx` | WTRM | Gearbox | 07000–07199 | 7000–7058 (59 rows) |
| `072xx` | WTRM | Drive train | 07200–07299 | 7200–7230 (31 rows) |
| `073xx` | WTRM | Hydraulics | 07300–07399 | 7300–7316 (17 rows) |
| `074xx` | WTRM | Brake | 07400–07499 | 7400–7419 (20 rows) |
| `080xx` | WYAW | Yaw | 08000–08199 | 8000–8032 (33 rows) |
| `090xx` | WTUR | System | 09000–09199 | 9001–9091 (91 rows) |
| `092xx` | WTUR | Control System | 09200–09299 | 9200–9258 (59 rows) |
| `093xx` | WTUR | Safety | 09300–09399 | 9300–9319 (20 rows) |
| `0990x` | WTUR | External | 09900–09929 | 9900–9908 (9 rows) |
| `0993x` | WTUR | Farm | 09930–09959 | 9930–9942 (13 rows) |
| `0996x` | WTUR | Feedback Control | 09960–09969 | 9960–9961 (2 rows) |
| `0997x` | WTUR | Interface | 09970–09979 | 9970–9970 (1 row) |
| `0998x` | WTUR | Power Management | 09980–09989 | 9980–9981 (2 rows) |
| `0999x` | WTUR | UPS | 09990–09999 | 9990–9994 (5 rows) |
| `110xx` | WTUR (11000–11999, Hub) | Control System | 11000–11099 | 11001–11036 (36 rows) |
| `1110x` | WTUR (11000–11999, Hub) | Field Bus | 11100–11149 | 11101–11108 (8 rows) |
| `1115x` | WTUR (11000–11999, Hub) | System | 11150–11199 | 11151–11157 (7 rows) |
| `1200x` | WROT (12000–12999, Hub) | Blade | 12000–12049 | 12001–12025 (25 rows) |
| `1205x` | WROT (12000–12999, Hub) | Batteries | 12050–12199 | 12051–12101 (51 rows) |
| `1220x` | WROT (12000–12999, Hub) | Pitch | 12200–12249 | 12201–12235 (35 rows) |
| `1225x` | WROT (12000–12999, Hub) | Pitch Control | 12250–12299 | 12251–12259 (9 rows) |
| `123xx` | WROT (12000–12999, Hub) | Pitch Drivers | 12300–12399 | 12301–12333 (33 rows) |
| `124xx` | WROT (12000–12999, Hub) | Pitch Converter | 12400–12499 | 12401–12445 (45 rows) |
| `125xx` | WROT (12000–12999, Hub) | Rotor | 12500–12599 | 12501–12514 (14 rows) |
| `130xx` | WPPD (13000–13999) | Wind Farm | 13000–13099 | 13001 (1 row) |

38 subgroups total (27 Main Controller + 11 Hub Controller, added 2026-09-17 from `HC Status Code Number.xlsx`). Note the subgroup prefix column now includes a disambiguating group tag where the group code alone (`WTUR`, `WROT`) is not unique (§9). **Reserved capacity, by design:** every hundred-block not listed above (e.g. `011xx` between Converter and Grid, `045xx`–`049xx` within Rotor & Pitch System, the large `9400xx`–`9899xx` span within Turbine Control & Operation, and everything past `12600` within the Hub Rotor & Pitch group) is deliberately unassigned, reserved for new subgroups added later (§9a.1). A code that already exists inside a currently-unassigned block (e.g. legacy `StCd-04960`, found earlier in the live 4XM codebase, sits in the unassigned `049xx` block) predates this taxonomy and needs formal reclassification before the mandatory-subgroup rule can apply to it retroactively.

### 9a.1 Administrator-Created Subgroups

New requirement (2026-09-17): an Administrator can create a new Functional Subgroup within any Functional System Group. The system validates the proposed `sub_range_start`/`sub_range_end` does not overlap any existing subgroup (active or inactive) in that group — overlap is rejected with a 409 (09-api-specification.md), and the Administrator must choose a genuinely free sub-range (typically one of the reserved blocks above). No alignment to hundreds-digit boundaries is enforced by the schema — the WTUR `0990x` … `0999x` sub-blocks above prove ten-number sub-ranges are legitimate — but the UI should visually suggest the next hundred-aligned free block as a sane default (10-ui-ux-specification.md).

**Inline-help text (NFR-007b, 2026-10-21):** every `lookup_*` table carries a nullable `description` column. The UI shows the selected option's description under each lookup-backed dropdown, or an explicit "no description available yet" note while it is NULL. Administrators maintain descriptions in Lookup Administration (audited as `LOOKUP_CHANGE`); the real wording for the 23 Available Group codes and the audience-access values still has to come from Controls Engineering.

## 9b. `lookup_turbine_platform`

`2XM`, `3XM`, `4XM`, extensible by an Administrator.

## 9c. `lookup_available_group`

Seeded with the 23 numeric codes currently observed in the export (1,2,4,5,6,9,11,12,13,14,15,16,18,20,21,22,23,24,25,27,28,30,32); **labels are TBD** — the source export carries only the numeric code, no description of what each availability group means. One row in the raw export contained a stray `\` value, treated as a data-quality artifact from the source spreadsheet, not a valid code, and excluded from the seed.

## 9d. Audience / Access Lookups (8 tables, real observed values)

Each shares the shape `id`, `code`, `label`, `is_active`, `sort_order`, `audience_visible` and, *(v4.1)*, `default_read_level` and `default_write_level` (§9d.9).

**9d.1 `lookup_development_access`:** `SCADA User`, `Department`, `Operation Control`, `See only`

**9d.2 `lookup_sales_access`:** `Sales`, `Covert`, `See only`

**9d.3 `lookup_tcc_access`:** `Telenotdienst`, `Telenotdienst-read`, `PMS Dispatcher`, `See only`

**9d.4 `lookup_service_access`:** `Commissioning`, `Service and Maintenance`, `See only`

**9d.5 `lookup_top_access`** (Turbine Operator Package): `Preventive Maintenance`, `Troubleshooting`, `Troubleshooting Advanced`, `Covert`, `See only`

**9d.6 `lookup_grid_operator_access`:** `Covert`, `See only`

**9d.7 `lookup_service_partner_access`:** `Service Partner`, `Ext. Service Provider`, `Customer after warranty Professional`, `Customer after warranty Advanced`, `Covert`, `See only`

**9d.8 `lookup_customer_access`:** `Standard`, `Advanced`, `Professional`, `Premium`, `Covert`, `See only`

**Open item (handled by decision D-02):** the exact meaning of `Covert` (appearing across several of these lookups) is not confirmed — it may be a mistranslation of "Covered" (i.e. included/in-scope) rather than its literal English sense; flagged for Controls Engineering confirmation before go-live, not guessed at here.

**9d.9 Default user-group levels *(v4.1)*:** seeded only where every code in the 14 generated programs that carried the named value showed the same numbers (§2d.1); all other values stay `NULL` and the level is entered per revision.

| Named value | Read | Write | Lookups |
|---|---|---|---|
| `See only` | 1 | 50 | all eight |
| `Covert` | 50 | 50 | sales, turbine operator package, grid operator, service partner, customer |
| `Operation Control` | 1 | 20 | development |
| `Preventive Maintenance` | 1 | 10 | turbine operator package |
| `Troubleshooting` | 1 | 15 | turbine operator package |
| `Ext. Service Provider` | 1 | 15 | service partner |
| `Customer after warranty Advanced` | 1 | 10 | service partner |

No default: `Service and Maintenance` and `Telenotdienst` (10 on one code, 20 on another), and the values seen on a single code only (`SCADA User` 5, `Department` 10, `Sales` 10, `PMS Dispatcher` 10, `Commissioning` 20, `Customer after warranty Professional` 12).

## 10. `lookup_engineering_domain`

`CONTROLS`, `ELECTRICAL`, `MECHANICAL`, `GRID`, `SAFETY`; extensible by an Administrator.

## 11. Export Formats

Since v4 an export may be shaped by an export profile, an audience, a language and a software version, can ship as a ZIP bundle with `MANIFEST.json` (and release notes), and the formats `HTML` (offline bundle) and `MD` (release notes) exist besides the four below (FR-100 … FR-111). Corrected 2026-09-17: **CSV, JSON, XLSX, and PDF** (adds XLSX; the prior revision listed only CSV/JSON/PDF). Every format is table/flat-row structured — one row per Status Code Revision with all fields as columns — including JSON, which is emitted as a flat array of row objects rather than a nested structure, mirroring the legacy tool's grid layout and the "Export for: Customer / Service" pattern observed in the legacy UI (which maps onto filtering by the relevant audience-access field, §2d).

## 12. Legacy Migration Traceability

The `legacy_reference_number` field (§1) exists specifically to carry the old "Status Code Number" from a source system (as seen in both the legacy UI screenshot and the `New Statuscode for sharing.xlsx` export's `Status Code Number` column) through the CSV/XLSX import process (§5), so every migrated code remains traceable back to where it came from without that old number ever being mistaken for a governed StCd identifier.

## 13. v4 Tables *(improvement pack, schema v4)*

All timestamps are ISO-8601 UTC text. FK = foreign key; "unique" lists the unique constraint. `docs/artifacts/schema.sql` has the exact DDL, CHECKs and indexes.

| Table | Fields | Rules |
|---|---|---|
| `lookup_controller_software_version` | `id`, `code` (unique), `label`, `description`, `is_active`, `sort_order` | `sort_order` is the release order used by ranges (FR-106) |
| `lookup_language` | `id`, `code` (unique), `label`, `description`, `is_active`, `sort_order`, `is_source` | exactly one source language (`en`); `de` seeded (D-03); `fr`, `hi`, `ka` added in v4.3, `ar` in v4.4 and `bn`, `mr`, `te`, `ta`, `gu`, `ur`, `kn`, `or`, `ml`, `pa` in v4.5 and `es`, `it`, `da` in v4.6, with Georgian moved to the end (FR-157); every `label` reads country letters, name, flag emoji (`GB English 🇬🇧`) |
| `revision_translation` | `id`, `status_code_revision_id`, `language_id`, `title`, `description`, `remedy_text`, `translation_status` (`DRAFT`\|`APPROVED`), `translated_by`, `translated_at`, `approved_by`, `approved_at` | unique per revision + language; `approved_by <> translated_by` (BR-018) |
| `export_profile` | `id`, `code` (unique), `name`, `description`, `columns` (JSON list of `{field, label}`), `language_code`, `audience`, `title_page`, `pdf_orientation` (`L`\|`P`), `is_active`, `sort_order`, `created_by`, `created_at` | seeded: service manual, SCADA tag list, customer list (FR-100) |
| `change_set` | `id`, `name` (unique), `description`, `target_software_version_id`, `status` (`OPEN`\|`CLOSED`), `created_by`, `created_at`, `closed_at` | FR-124 |
| `delegation` | `id`, `delegator_id`, `delegate_id`, `role_code` (`REVIEWER`\|`ADMINISTRATOR`\|`CHIEF_ENGINEER`), `valid_from`, `valid_to`, `created_by`, `created_at`, `revoked_at` | `delegator_id <> delegate_id`, `valid_to >= valid_from` (FR-125) |
| `notification` | `id`, `user_id`, `kind`, `message`, `link`, `change_request_id`, `dedupe_key`, `created_at`, `read_at`, `emailed_at` | `dedupe_key` is unique; it is built from user, CR, stage, level and day, so a reminder is created at most once per combination (FR-121) |
| `cr_attachment` | `id`, `change_request_id`, `filename`, `content_type`, `size_bytes`, `sha256`, `storage_path`, `description`, `uploaded_by`, `uploaded_at` | `size_bytes >= 0`; limits in FR-130 |
| `field_comment` | `id`, `change_request_id`, `field_name`, `author_id`, `comment_text` (1–2000), `created_at`, `resolved_by`, `resolved_at` | FR-127 |
| `review_checklist_item` | `id`, `functional_system_group_id` (NULL = all groups), `text` (3–300), `is_active`, `sort_order`, `created_at` | FR-128 |
| `cr_checklist_confirmation` | `id`, `change_request_id`, `checklist_item_id`, `item_text`, `confirmed_by`, `confirmed_at` | unique per CR + item; the confirmed wording is a copy, so later edits never rewrite history |
| `saved_search` | `id`, `user_id`, `name` (1–80), `definition` (JSON filters + columns), `created_at` | unique per user + name (FR-142) |
| `login_attempt` | `id`, `scope` (`IP`\|`USER`), `key`, `attempted_at` (epoch seconds, REAL) | rows older than 15 minutes are pruned (NFR-009) |
| `app_setting` | `key` (PK), `value`, `updated_by`, `updated_at` | keys and defaults: `sla.review.amber_days` 3, `sla.review.red_days` 5, `sla.approval.amber_days` 2, `sla.approval.red_days` 3, `reviewer.auto_assign` 0, `health.capacity_alert_percent` 15, `health.capacity_alert_numbers` 20; amber must not exceed red |
| `occurrence_import` | `id`, `source_label`, `period_start`, `period_end`, `imported_by`, `imported_at`, `row_count`, `unmatched_count` | `period_end >= period_start` (FR-143) |
| `code_occurrence` | `id`, `occurrence_import_id`, `status_code_id`, `occurrences` | `occurrences >= 0`; one row per code per import |
| `api_token` | `id`, `user_id`, `name` (1–80), `token_prefix`, `token_hash` (SHA-256), `scopes` (space separated), `expires_at`, `last_used_at`, `revoked_at`, `created_at` | the secret is never stored; at most 365 days (FR-144) |
| `webhook` | `id`, `name`, `url`, `secret`, `events`, `is_active`, `created_by`, `created_at`, `last_delivery_at`, `last_status` | target must be private or loopback (FR-146) |
| `webhook_delivery` | `id`, `webhook_id`, `event`, `payload`, `http_status`, `ok`, `error`, `delivered_at` | the outcome of every delivery |
| `hub_mc_mapping` | `id`, `hub_status_code_id`, `mc_status_code_id`, `created_by`, `created_at` | `hub_status_code_id <> mc_status_code_id`; one mapping per Hub code (FR-147) |
| `lookup_user_group_slot` *(v4.1)* | `id`, `slot` (unique, 0–15), `audience_code` (unique, NULL for an unassigned slot), `label`, `description`, `is_active`, `sort_order` | 16 rows; slots 1–8 are the eight audiences, the others are inactive (§2d.1) |
| `import_source_item` *(v4.2)* | `id`, `import_job_id`, `status_code_id`, `source_file`, `source_sha256`, `program_number`, `controller` (`MC`\|`HC`), `source_line`, `parsed_json` | unique per job, file and program; `source_sha256` is 64 characters (FR-048v) |
| `status_code_revision_user_group` *(v4.1)* | `id`, `status_code_revision_id`, `user_group_slot_id`, `read_level`, `write_level` | unique per revision and slot; both levels 0–255 (§2d.1) |
| `language_reviewer` *(v4.7)* | `id`, `user_id`, `language_code`, `assigned_by`, `assigned_at` | unique per user and language; the native speakers assigned to review one language of the interface (FR-164) |
| `translation_review` *(v4.7)* | `id`, `language_code`, `reviewer_id`, `status` (`OPEN` \| `COMPLETED`), `started_at`, `completed_at`, `fingerprint`, `string_count` | one review of one language by one reviewer; at most one `OPEN` review per language and reviewer (partial unique index `ux_translation_review_open`); `fingerprint` is that of the catalogue (shipped text plus overrides) the review started from |
| `translation_review_item` *(v4.7)* | `id`, `review_id`, `string_id`, `english`, `current_text`, `verdict` (`OK` \| `CHANGE` \| `UNCLEAR`), `proposal`, `comment`, `decision` (`PENDING` \| `ACCEPTED` \| `REJECTED` \| `NOTED`), `decided_by`, `decided_at`, `updated_at` | unique per review and string; proposal and comment at most 1,000 characters; a `CHANGE` needs a proposal (CHECK); a proposal without `current_text` translates a string that was missing |
| `translation_override` *(v4.7)* | `id`, `language_code`, `string_id`, `english`, `text`, `review_item_id`, `created_by`, `created_at` | unique per language and string; the text the application shows instead of the shipped one (1–1,000 characters); deleting the row restores the shipped text |
| `terminology_term` *(v4.9)* | `id`, `code`, `category` (`PRODUCT` \| `DATA` \| `STATE` \| `PROCESS` \| `ROLE` \| `AUDIENCE` \| `KEEP`), `english`, `definition`, `keep_english`, `is_active`, `created_by`, `created_at`, `updated_at` | unique `code` (lower-case letters, digits, hyphens); the technical nomenclature, one row per term (FR-166); `keep_english` marks a term that is never translated |
| `terminology_translation` *(v4.9)* | `id`, `term_id`, `language_code`, `text` (1–200 characters), `status` (`DRAFT` \| `APPROVED`), `note`, `proposed_by`, `proposed_at`, `approved_by`, `approved_at` | unique per term and language; a draft until a second person approves it (BR-018 applied to the terminology); the note is the reason of a send-back; approved exactly when `approved_at` is set |

Also *(v4)*: `lookup_functional_system_group.controller_type` (`MAIN` | `HUB`, default `MAIN`; Hub groups are those with `range_start >= 11000`, decision D-06), the `audience_visible` column on the eight access lookups, `change_request.change_set_id`, and the optional search index `status_code_fts` (+ `status_code_fts_vocab`, created by migration `f8b2d4e6a012` when the SQLite build has FTS5; `docs/artifacts/schema-fts5.sql`).

Also *(v4.1)*: `status_code.prg_idx` (§1), the 25 further columns of `status_code_revision` (§2c.1, §2f), `default_read_level` and `default_write_level` on the eight access lookups (§9d.9), the triggers `trg_prevent_prg_idx_change_after_release` and `trg_require_prg_idx_for_review`, and the setting `status_code.require_prg_idx` (default 0), which only the second trigger reads and which is not yet editable in the Administration screen.

Also *(v4.2)*: `status_code.reserved_identifier` (§1), `import_job.change_set_id` and the `ST` source format (§5), `import_source_item` (above, §5a) and the triggers `trg_identifier_matches_reservation`, `trg_reservation_not_issued_elsewhere`, `trg_identifier_not_reserved_elsewhere`.

Also *(v4.7)*: `user.email` is fixed once the account exists, enforced by the trigger `trg_user_email_immutable` (BEFORE UPDATE OF `email` ... aborts when the value changes; FR-162), and the four translation tables above; the Windows sign-in (FR-163) adds no column, it matches the identity with `user.email`.

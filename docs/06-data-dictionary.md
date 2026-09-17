# 06. Data Dictionary — CSCM Tool

Conventions: **Required** = enforced not-null at both UI and API before the entity can leave Draft (for revision fields) or at all times (for structural fields). Datatypes are given in SQLite-native terms with the logical type in parentheses where useful (see 07-database-design.md for full DDL).

**Open item — `software_version`:** the legacy tool's screenshot shows Software Version as a top-level dropdown filter (`SW_1_1_1_4.2MW`) scoping the entire status-code table view, and the row-level export we analyzed did not carry it as a per-row column — because the export itself was already scoped to one software version. Retained here as an optional per-revision field (its prior role in the v2 model) rather than silently dropped, but it may turn out to belong on `Release` instead (a "this Release is for software build X" scope), not on every revision. Flagged for confirmation before finalizing the schema.

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
| `owner_id` | Accountable engineer | INTEGER (FK → user.id) | Yes | creator's id | active user, Engineer or Administrator role | — | `14` |
| `created_at` | Row creation timestamp (UTC) | TEXT (ISO-8601) | Yes | `now()` | system-generated | — | `2026-03-02T09:14:00Z` |

**Why Functional Subgroup is mandatory:** every one of the 897 rows in the real export carries a `Functional Group Name` (subgroup) value — there is no "group-only, no subgroup" case in production data, and the business explicitly confirmed a code must never be created without one. An Engineer selecting only a Functional System Group at creation time is therefore an incomplete Draft, not a valid one; the Functional Subgroup dropdown blocks progression exactly like any other mandatory field (10-ui-ux-specification.md §4).

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

## 2a. Field-to-Engineering-Domain Ownership

Unchanged principle from the prior revision (05-governance-handbook.md §6a). `title`, `description`, `status_category`, `available_group` are domain-agnostic ("Any"); timing fields (`set_delay`, `reset_delay`, `up_down_counter`, `trigger_snapshot`), the repeated-error fields (§2b), and the program reference fields (§2c) are owned by `CONTROLS`. The eight audience/access fields (§2d) are Governance-confirmed, following the same propose-by-Engineer/confirm-by-Administrator pattern as the old restricted `access_rights_id` field.

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

**Value normalization:** the raw export contains inconsistent casing (`See Only` vs `See only`) and one apparent typo (`ProfessionaProfessional`). The lookups in §9d.1–§9d.8 are seeded with the corrected, de-duplicated values; the typo is normalized to `Professional`.

## 2e. Technical Addressing Fields (derived, read-only)

| Field | Description | Datatype | Required | Default | Notes |
|---|---|---|---|---|---|
| `logical_node` | Controller addressing identifier | TEXT | Yes | derived | Always equals the parent Status Code's Functional System Group prefix (e.g. `WCNV`) — auto-populated, never independently entered; confirmed by the real export where this column exactly mirrors the sheet's group. |
| `node_value` | Controller addressing index | INTEGER | Yes | derived | Always equals the parent Functional System Group's `sort_order` (1–9) — auto-populated. |

Both fields exist in the real export as their own columns (presumably for direct firmware/SCADA tag generation) but carry no information beyond what the Functional System Group already encodes; CSCM Tool derives and displays them rather than accepting manual entry, to guarantee they can never drift out of sync with the group assignment.

## 3. `status_code_revision_platform` (Turbine Platform, multi-select)

Unchanged from the prior revision. At least one Turbine Platform must be selected before a revision can be submitted for Review.

| Field | Description | Datatype | Required | Default | Example |
|---|---|---|---|---|---|
| `id` | Surrogate PK | INTEGER | Yes | auto | `77` |
| `status_code_revision_id` | Parent revision | INTEGER (FK) | Yes | — | `5031` |
| `turbine_platform_id` | Applicable platform | INTEGER (FK → lookup_turbine_platform) | Yes | — | `3XM` |

## 4. `change_request`, `review_comment`, `domain_signoff`

Unchanged in shape from the prior revision (05-governance-handbook.md §7–§8 for the dual-review-then-Chief-Engineer-approval sequence these tables support).

## 5. `import_job` (new — library import)

| Field | Description | Datatype | Required | Default | Validation | Example |
|---|---|---|---|---|---|---|
| `id` | Surrogate PK | INTEGER | Yes | auto | — | `12` |
| `requested_by` | Engineer or Administrator who initiated the import | INTEGER (FK → user.id) | Yes | current user | — | `14` |
| `source_format` | Format of the uploaded file | TEXT (enum) | Yes | — | — | `CSV`, `XLSX` |
| `source_file_reference` | Path/pointer to the uploaded source file, retained for audit | TEXT | Yes | — | — | `/imports/12/source.csv` |
| `row_count` | Total rows in the source file | INTEGER | Yes | — | — | `134` |
| `status` | Job state | TEXT (enum) | Yes | `PENDING` | — | `PENDING`,`VALIDATING`,`COMPLETE`,`FAILED` |
| `created_count` | Number of rows successfully turned into Draft Change Requests | INTEGER | No | `0` | — | `128` |
| `error_count` | Number of rows that failed validation and were not imported | INTEGER | No | `0` | — | `6` |
| `error_report_reference` | Path/pointer to a downloadable per-row error report | TEXT | No | `NULL` | — | `/imports/12/errors.csv` |
| `created_at` | Job start timestamp | TEXT (ISO-8601) | Yes | `now()` | — | — |
| `completed_at` | Job completion timestamp | TEXT (ISO-8601) | No | `NULL` | — | — |

**Governance note:** every row that successfully validates becomes a normal Draft `StatusCode`/`StatusCodeRevision`/`ChangeRequest` triple, exactly as if an Engineer had typed it in by hand — it still must pass Cross-Domain Sign-Off (if applicable), both Review sign-offs, and Chief Engineer approval before it can be Released. Import is a faster data-entry path, not a governance bypass (confirmed 2026-09-17; see 05-governance-handbook.md §6b).

## 6. `release` / `release_item`

Unchanged in shape from the prior revision.

## 7. `user` / `user_engineering_domain`

Unchanged in shape from the prior revision.

## 8. `audit_log_entry` / `export_job`

Unchanged shape from the prior revision except `export_job.export_type` now also accepts `XLSX` (§11) alongside `CSV`, `JSON`, `PDF`, and `SQLITE_BACKUP`.

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

**Correction (2026-09-17):** the subgroup names in the prior revision (sourced from a hand-typed summary table) did not match the authoritative row-level export, confirming the "Sub Group not named properly" issue raised by the business. The table below is built directly from the real `Functional Group Name` column of `New Statuscode for sharing.xlsx` and **supersedes** the earlier version. WTUR in particular has **nine** subgroups, not four, with six of them packed into narrow sub-bands within 9900–9999 rather than one hundred-block each.

| Subgroup Prefix | Group | Subgroup Name (real) | Declared sub-range | Observed usage |
|---|---|---|---|---|
| `010xx` | WCNV | Converter | 01000–01099 | 1000–1075 (76 rows) |
| `012xx` | WCNV | Grid | 01200–01299 | 1200–1257 (58 rows) |
| `020xx` | WGEN | Generator | 02000–02099 | 2000–2051 (52 rows) |
| `022xx` | WGEN | Protection | 02200–02299 | 2200–2202 (3 rows) |
| `030xx` | WNAC | Meteorology | 03000–03099 | 3000–3052 (53 rows) |
| `032xx` | WNAC | Nacelle | 03200–03299 | 3200–3249 (50 rows) |
| `040xx` | WROT | Rotor | 04000–04099 | 4000–4096 (97 rows) |
| `042xx` | WROT | Hot Air De-icing | 04200–04299 | 4200–4246 (47 rows) |
| `043xx` | WROT | Lighting | 04300–04399 | 4300–4304 (5 rows) |
| `044xx` | WROT | Blade Sensors | 04400–04499 | 4400–4415 (16 rows) |
| `050xx` | WTOW | Tower | 05000–05099 | 5000–5042 (43 rows) |
| `060xx` | WTRF | Switches | 06000–06099 | 6000–6007 (8 rows) |
| `062xx` | WTRF | Transformer | 06200–06299 | 6200–6226 (27 rows) |
| `070xx` | WTRM | Gearbox | 07000–07099 | 7000–7058 (59 rows) |
| `072xx` | WTRM | Drive train | 07200–07299 | 7200–7230 (31 rows) |
| `073xx` | WTRM | Hydraulics | 07300–07399 | 7300–7316 (17 rows) |
| `074xx` | WTRM | Brake | 07400–07499 | 7400–7419 (20 rows) |
| `080xx` | WYAW | Yaw | 08000–08099 | 8000–8032 (33 rows) |
| `090xx` | WTUR | System | 09000–09099 | 9001–9091 (91 rows) |
| `092xx` | WTUR | Control System | 09200–09299 | 9200–9258 (59 rows) |
| `093xx` | WTUR | Safety | 09300–09399 | 9300–9319 (20 rows) |
| `099xx` (a) | WTUR | External | 09900–09929 | 9900–9908 (9 rows) |
| `099xx` (b) | WTUR | Farm | 09930–09959 | 9930–9942 (13 rows) |
| `099xx` (c) | WTUR | Feedback Control | 09960–09969 | 9960–9961 (2 rows) |
| `099xx` (d) | WTUR | Interface | 09970–09979 | 9970–9970 (1 row) |
| `099xx` (e) | WTUR | Power Management | 09980–09989 | 9980–9981 (2 rows) |
| `099xx` (f) | WTUR | UPS | 09990–09999 | 9990–9994 (5 rows) |
| `11-0xx` | WTUR (11000–11999, Hub) | Control System | 11000–11100 | 11001–11036 (36 rows) |
| `11-1xxA` | WTUR (11000–11999, Hub) | Field Bus | 11101–11150 | 11101–11108 (8 rows) |
| `11-1xxB` | WTUR (11000–11999, Hub) | System | 11151–11200 | 11151–11157 (7 rows) |
| `12-0xx` | WROT (12000–12999, Hub) | Blade | 12001–12050 | 12001–12025 (25 rows) |
| `12-0xxB` | WROT (12000–12999, Hub) | Batteries | 12051–12200 | 12051–12101 (51 rows) |
| `12-2xx` | WROT (12000–12999, Hub) | Pitch | 12201–12250 | 12201–12235 (35 rows) |
| `12-2xxB` | WROT (12000–12999, Hub) | Pitch Control | 12251–12300 | 12251–12259 (9 rows) |
| `12-3xx` | WROT (12000–12999, Hub) | Pitch Drivers | 12301–12400 | 12301–12333 (33 rows) |
| `12-4xx` | WROT (12000–12999, Hub) | Pitch Converter | 12401–12500 | 12401–12445 (45 rows) |
| `12-5xx` | WROT (12000–12999, Hub) | Rotor | 12501–12600 | 12501–12514 (14 rows) |
| `13-0xx` | WPPD (13000–13999) | Wind Farm | 13001–13100 | 13001 (1 row) |

38 subgroups total (27 Main Controller + 11 Hub Controller, added 2026-09-17 from `HC Status Code Number.xlsx`). Note the subgroup prefix column now includes a disambiguating group tag where the group code alone (`WTUR`, `WROT`) is not unique (§9). **Reserved capacity, by design:** every hundred-block not listed above (e.g. `011xx` between Converter and Grid, `045xx`–`049xx` within Rotor & Pitch System, the large `9400xx`–`9899xx` span within Turbine Control & Operation, and everything past `12600` within the Hub Rotor & Pitch group) is deliberately unassigned, reserved for new subgroups added later (§9a.1). A code that already exists inside a currently-unassigned block (e.g. legacy `StCd-04960`, found earlier in the live 4XM codebase, sits in the unassigned `049xx` block) predates this taxonomy and needs formal reclassification before the mandatory-subgroup rule can apply to it retroactively.

### 9a.1 Administrator-Created Subgroups

New requirement (2026-09-17): an Administrator can create a new Functional Subgroup within any Functional System Group. The system validates the proposed `sub_range_start`/`sub_range_end` does not overlap any existing subgroup (active or inactive) in that group — overlap is rejected with a 409 (09-api-specification.md), and the Administrator must choose a genuinely free sub-range (typically one of the reserved blocks above). No alignment to hundreds-digit boundaries is enforced by the schema — the WTUR `099xx` sub-blocks above prove ten-number sub-ranges are legitimate — but the UI should visually suggest the next hundred-aligned free block as a sane default (10-ui-ux-specification.md).

## 9b. `lookup_turbine_platform`

Unchanged from the prior revision (`2XM`, `3XM`, `4XM`, extensible).

## 9c. `lookup_available_group`

Seeded with the 23 numeric codes currently observed in the export (1,2,4,5,6,9,11,12,13,14,15,16,18,20,21,22,23,24,25,27,28,30,32); **labels are TBD** — the source export carries only the numeric code, no description of what each availability group means. One row in the raw export contained a stray `\` value, treated as a data-quality artifact from the source spreadsheet, not a valid code, and excluded from the seed.

## 9d. Audience / Access Lookups (8 tables, real observed values)

Each shares the shape `id`, `code`, `label`, `is_active`, `sort_order`.

**9d.1 `lookup_development_access`:** `SCADA User`, `Department`, `Operation Control`, `See only`

**9d.2 `lookup_sales_access`:** `Sales`, `Covert`, `See only`

**9d.3 `lookup_tcc_access`:** `Telenotdienst`, `Telenotdienst-read`, `PMS Dispatcher`, `See only`

**9d.4 `lookup_service_access`:** `Commissioning`, `Service and Maintenance`, `See only`

**9d.5 `lookup_top_access`** (Turbine Operator Package): `Preventive Maintenance`, `Troubleshooting`, `Troubleshooting Advanced`, `Covert`, `See only`

**9d.6 `lookup_grid_operator_access`:** `Covert`, `See only`

**9d.7 `lookup_service_partner_access`:** `Service Partner`, `Ext. Service Provider`, `Customer after warranty Professional`, `Customer after warranty Advanced`, `Covert`, `See only`

**9d.8 `lookup_customer_access`:** `Standard`, `Advanced`, `Professional`, `Premium`, `Covert`, `See only`

**Open item:** the exact meaning of `Covert` (appearing across several of these lookups) is not confirmed — it may be a mistranslation of "Covered" (i.e. included/in-scope) rather than its literal English sense; flagged for Controls Engineering confirmation before go-live, not guessed at here.

## 10. `lookup_engineering_domain`

Unchanged from the prior revision (`CONTROLS`, `ELECTRICAL`, `MECHANICAL`, `GRID`, `SAFETY`).

## 11. Export Formats

Corrected 2026-09-17: **CSV, JSON, XLSX, and PDF** (adds XLSX; the prior revision listed only CSV/JSON/PDF). Every format is table/flat-row structured — one row per Status Code Revision with all fields as columns — including JSON, which is emitted as a flat array of row objects rather than a nested structure, mirroring the legacy tool's grid layout and the "Export for: Customer / Service" pattern observed in the legacy UI (which maps onto filtering by the relevant audience-access field, §2d).

## 12. Legacy Migration Traceability

The `legacy_reference_number` field (§1) exists specifically to carry the old "Status Code Number" from a source system (as seen in both the legacy UI screenshot and the `New Statuscode for sharing.xlsx` export's `Status Code Number` column) through the CSV/XLSX import process (§5), so every migrated code remains traceable back to where it came from without that old number ever being mistaken for a governed StCd identifier.

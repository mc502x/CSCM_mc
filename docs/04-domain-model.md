# 04. Domain Model Specification — CSCM Tool

## 1. Entity Overview

| Entity | Description | Ownership |
|---|---|---|
| `User` | A named system account, tagged with a Role and (for Engineers) one or more Engineering Domains | Administration |
| `Role` | Fixed enumeration: Administrator, Engineer, Reviewer, Chief Engineer, Viewer | Administration |
| `EngineeringDomain` | Lookup of engineering specialties (Controls, Electrical, Mechanical, Grid, Safety, ...) | Administration |
| `FunctionalSystemGroup` | Lookup of the nine numbering bands (05-governance-handbook.md §2) | Governance |
| `FunctionalSubgroup` | Lookup of sub-bands within a Functional System Group (real taxonomy seeded; **mandatory** on every StatusCode, never optional) | Governance |
| `TurbinePlatform` | Lookup of platforms a code applies to (multi-select) | Governance |
| `StatusCode` | Immutable identity for a governed status code (StCd identifier, allocated at Draft→Review) | Engineering |
| `StatusCodeRevision` | A specific versioned set of attribute values for a `StatusCode`, with its own lifecycle state | Engineering / Governance |
| `StatusCodeRevisionPlatform` | Join: which Turbine Platform(s) a revision applies to | Engineering |
| `PlatformVariantLink` | Cross-reference between independent Status Codes that represent the same condition on different platforms | Engineering |
| `ChangeRequest` | The workflow object that carries a `StatusCodeRevision` through Draft→Review→PendingApproval→Approved | Engineering / Governance |
| `ReviewComment` | A comment/decision attached to a `ChangeRequest`, tagged with which of the three decision roles it represents | Governance |
| `DomainSignoff` | Record of a second Engineer completing their Engineering Domain's fields on a Change Request | Engineering |
| `Release` | A named, versioned, immutable bundle of Released revisions | Governance |
| `ReleaseItem` | Join entity: which revisions belong to which Release | Governance |
| `AvailableGroup` | Soft-validated lookup of the numeric availability codes observed in production; labels TBD | Governance |
| Eight `*Access` lookups | Independent audience-visibility vocabularies — Development, Sales, TCC, Service, Turbine Operator Package, Grid Operator, Service Partner, Customer (06-data-dictionary.md §2d, §9d) | Governance |
| `ImportJob` | Record of a CSV/XLSX library import; produces Draft Change Requests, never bypasses governance | System / Engineering |
| `AuditLogEntry` | Immutable record of a state-changing action | System |
| `ExportJob` | Record of a generated export (catalogue or full-database), formats CSV/JSON/XLSX/PDF | System |

## 2. Entity Definitions

### 2.1 `User`
Attributes: `id`, `username`, `email`, `password_hash`, `full_name`, `role_id`, `is_active`, `created_at`, `last_login_at`, `failed_login_count`, `locked_until`. Relationships: one `User` has one `Role`. An Engineer-role `User` has zero or more `EngineeringDomain` tags (M:N via `user_engineering_domain`). One `User` authors many `StatusCodeRevision` (as `created_by`), records many `ReviewComment` decisions, owns many `StatusCode` (as `owner`).

### 2.2 `Role`
Fixed lookup: `ADMINISTRATOR`, `ENGINEER`, `REVIEWER`, `CHIEF_ENGINEER`, `VIEWER`. Not user-extensible in MVP. See 00-INDEX.md "Roles" and 05-governance-handbook.md §7 for organizational mapping and responsibilities.

### 2.3 `EngineeringDomain`
Lookup: `CONTROLS`, `ELECTRICAL`, `MECHANICAL`, `GRID`, `SAFETY` (seed set, Administrator-extensible). Used to route Cross-Domain Sign-Off (05-governance-handbook.md §6a) and to tag which fields on a `StatusCodeRevision` a given domain is responsible for.

### 2.4 `FunctionalSystemGroup`
Attributes: `id`, `code` (`WCNV`, `WGEN`, ...), `label`, `range_start`, `range_end`, `is_active`. Twelve seed rows per 00-INDEX.md's numbering table (nine Main Controller groups plus three Hub Controller groups added 2026-09-17). This lookup **replaces** the former `controller_type` field — it is now both a classification and the source of numeric allocation for `StatusCode.status_code_identifier`. **`code` is unique together with `range_start`, not on its own**: `WTUR` and `WROT` are each intentionally reused across a Main Controller group and a numerically distinct Hub Controller group (same thematic prefix, confirmed by the business), so any lookup by prefix alone is ambiguous — resolve by `(code, range_start)` or `id`.

### 2.5 `FunctionalSubgroup`
Attributes: `id`, `functional_system_group_id` (FK), `code`, `label`, `sub_range_start`, `sub_range_end`, `is_active`. Seeded with the real taxonomy supplied 2026-09-15 (06-data-dictionary.md §9a): each subgroup owns a 100-number sub-band aligned to the hundreds digit of the identifier (e.g. `010xx` = 01000–01099). Not every hundred-block in a group is currently assigned — unassigned blocks are deliberate reserved capacity for future subgroups, addable as a pure data change. Selecting a Functional Subgroup at creation time narrows numeric allocation to its sub-band; selecting only the Functional System Group (no subgroup) allocates from any number in the group's range not already claimed by a subgroup-scoped allocation, including reserved blocks.

### 2.6 `TurbinePlatform`
Attributes: `id`, `code` (`2XM`, `3XM`, `4XM`, ...), `label`, `is_active`. Administrator-managed, extensible (the business explicitly stated "minimum" 2XM/3XM/4XM, more will follow).

### 2.7 `StatusCode`
Represents the durable identity of a governed code. Attributes: `id`, `status_code_identifier` (`StCd-XXXXX`, nullable until first Review submission — see §4 lifecycle note), `functional_system_group_id` (FK), `functional_subgroup_id` (FK, **mandatory — corrected 2026-09-17, was nullable**), `is_sandbox` (bool, default false), `platform_variant_of_status_code_id` (nullable, see `PlatformVariantLink` §2.10), `legacy_reference_number` (nullable text, populated on library import — §2.18), `owner_id`, `created_at`. **Cardinality:** one `StatusCode` has many `StatusCodeRevision` (1:N); exactly one revision at a time is flagged `is_current = true` (BR-002). **Uniqueness:** `status_code_identifier` is unique once assigned. **Sandbox exception:** if `is_sandbox = true`, the identifier is drawn from an isolated `StCd-T#####` counter (05-governance-handbook.md §12) and the record is eligible for hard delete by an Administrator — the only entity in this schema with that property.

### 2.8 `StatusCodeRevision`
The versioned, governed record. Full field-by-field detail lives in 06-data-dictionary.md §2–§2e (grounded in a real 897-row export of the live library, 2026-09-17) — this section summarizes the categories rather than repeating every field, to avoid the two documents drifting apart:
- Identity/linkage: `id`, `status_code_id` (FK), `revision_number`, `is_current`.
- Descriptive/classification: `title`, `description`, `software_version` (nullable — open item, may belong on `Release` instead, see 06-data-dictionary.md), `status_category` (`ERROR`/`WARNING`/`INFO`), `available_group` (numeric, soft-validated — §2.15), `alarm_flag` (boolean, not a behaviour enum), `set_delay`/`reset_delay` (free text with unit).
- Behavioural flags: `up_down_counter`, `trigger_snapshot`, `loadless_spinning_permitted`.
- Repeated-error escalation (all optional together): `number_of_times_repeated`, `repeated_over_the_course`, `status_code_for_repeated_error` (opaque numeric reference to a separate, unrelated code pool — confirmed 2026-09-17, **not** a foreign key to `StatusCode`).
- Program references (numeric, externally defined by controller firmware, soft-validated — §2.15): `yaw_program`, `manual_reset_program`, `auto_reset_program`, `converter_reactive_power_program`, `brake_program`, `umrichterprogramm_gsc`, `umrichterprogramm_msc`, `yaw_bearing_lubrication_program`.
- Audience/access (governance-restricted, eight independent fields — see §2.9): `development_access`, `sales_access`, `tcc_access`, `service_access`, `turbine_operator_package_access`, `grid_operator_access`, `service_partner_access`, `customer_access`.
- Technical addressing (derived, read-only, not stored — §2e of 06-data-dictionary.md): `logical_node`, `node_value`.
- Governance/workflow: `owner_id`, `lifecycle_status` (7-state enum, 05-governance-handbook.md §4), `created_by`, `created_at`, `reviewer_signoff_by`/`_at`, `admin_signoff_by`/`_at`, `chief_engineer_approved_by`/`_date`, `effective_date`, `deprecated_reason`, `superseded_by_status_code_id`.
- **Cardinality:** many `StatusCodeRevision` : one `StatusCode` (N:1). One `StatusCodeRevision` : one `ChangeRequest` (1:1). One `StatusCodeRevision` : many `TurbinePlatform` (M:N via `status_code_revision_platform`). One `StatusCodeRevision` : zero-or-one `ReleaseItem`.
- **No subtype hierarchy**: Functional System Group on the parent `StatusCode` remains the sole classification axis; no per-type subtables.

### 2.9 Restricted Fields
The eight audience/access fields (§2.8) may each be set by the authoring Engineer as a **proposed** value but are not authoritative until the Administrator's mandatory Review sign-off (§2.12) confirms or overrides them — enforced at the service layer, not merely a UI convention (11-security-architecture.md §3). This replaces the single `access_rights_id` restricted field from the prior revision with eight independently-restricted fields, following the same propose-by-Engineer/confirm-by-Administrator-at-sign-off pattern.

### 2.10 `PlatformVariantLink`
Represented as the nullable self-referential `platform_variant_of_status_code_id` on `StatusCode` (not a separate join table, since it is a simple pointer, not M:N): when a code is renamed or functionally regenerated for a different Turbine Platform rather than simply extended to cover it, the new `StatusCode` is created as an **independent record** with its own `StCd` identifier, optionally pointing back to the originating code via this field, purely for navigability — it carries no lifecycle or approval semantics of its own (05-governance-handbook.md §2a).

### 2.11 `ChangeRequest`
Attributes: `id`, `status_code_revision_id` (FK, 1:1), `cr_type` (`NEW` | `REVISION` | `DEPRECATION`), `requested_by`, `justification`, `state` (mirrors the revision's lifecycle for Draft/Review/PendingApproval/Approved), `submitted_at`, `chief_engineer_decided_at`, `chief_engineer_decided_by`. **Cardinality:** 1:1 with `StatusCodeRevision`; 1:N with `ReviewComment`; 1:N with `DomainSignoff`.

### 2.12 `ReviewComment`
Attributes: `id`, `change_request_id`, `author_id`, `comment_text`, `decision` (`REVIEWER_APPROVE` | `REVIEWER_REJECT` | `ADMIN_APPROVE` | `ADMIN_REJECT` | `CHIEF_ENGINEER_APPROVE` | `CHIEF_ENGINEER_REJECT` | `NULL` for a plain comment), `created_at`. The `decision` enum's role-tagging is what lets the system verify both required Review sign-offs came from the correct, distinct roles (05-governance-handbook.md §7) rather than the same role acting twice.

### 2.13 `DomainSignoff`
Attributes: `id`, `change_request_id` (FK), `engineering_domain_id` (FK), `signed_off_by` (FK → User, must hold that domain), `signed_off_at`. A Change Request may only be submitted for Review once every domain tagged as required on its revision (derived from which domain-owned fields are still at their unset/default value — 06-data-dictionary.md §2a) has a corresponding `DomainSignoff` row (05-governance-handbook.md §6a).

### 2.14 `Release` / `ReleaseItem`
Unchanged in structure from v1 (07-database-design.md), scoped now by Functional System Group / Subgroup instead of Controller Type in `scope_filter`.

### 2.15 Lookup & Reference Entities
Corrected 2026-09-17 against real data — replaces the prior revision's `StatusCategory`/`AvailabilityGroup`/`BrakeProgram`/`ResetProgram`/`OperationalState`/`AccessRights`/`AlarmBehaviour` set entirely:
- `AvailableGroup` — soft-validated lookup of the numeric availability codes observed in production (currently 23 codes); labels not yet available from source data (06-data-dictionary.md §9c).
- Eight independent `*Access` lookups (Development, Sales, TCC, Service, Turbine Operator Package, Grid Operator, Service Partner, Customer) — real observed text values, replacing the single `AccessRights` enum (06-data-dictionary.md §9d).
- `status_category` and `alarm_flag` are plain `CHECK`-constrained columns (three values; boolean), not FK'd lookup tables — the real data doesn't support the richer enums assumed previously.
- The eight program-reference fields (`brake_program`, `yaw_program`, etc.) are **not** lookup-backed at all — they are numeric passthroughs to a controller-firmware-defined table CSCM Tool does not own (06-data-dictionary.md §2c).

### 2.16 `AuditLogEntry`
Unchanged shape. Notable addition: a `SANDBOX_DELETE` action captures the full pre-delete `StatusCode`/`StatusCodeRevision` snapshot in `before_value`, since this is the one case where the audited entity itself ceases to exist (12-audit-compliance.md §2).

### 2.17 `ExportJob`
Attributes unchanged, plus `export_scope_type` (`CATALOGUE` | `FULL_DATABASE`) — `FULL_DATABASE` exports are restricted to the Administrator role (08-system-architecture.md §6, FR-047). `export_type` now also accepts `XLSX` alongside `CSV`/`JSON`/`PDF`/`SQLITE_BACKUP` (new 2026-09-17).

### 2.18 `ImportJob`
New entity (2026-09-17). Attributes: `id`, `requested_by`, `source_format` (`CSV`|`XLSX`), `source_file_reference`, `row_count`, `status`, `created_count`, `error_count`, `error_report_reference`, `created_at`, `completed_at`. **Cardinality:** one `ImportJob` produces zero-or-more `ChangeRequest` rows (via `change_request.import_job_id`, tagged `cr_type = IMPORT`), each following the identical Draft-through-Approval path as a manually authored Change Request (05-governance-handbook.md §6b) — import creates work for the normal governance pipeline, it does not create a parallel one.

## 3. UML-Style Textual Class Diagram

```
+----------------+  1    N  +---------------------------+
|     User       |----owns--|        StatusCode          |
|----------------|          |-----------------------------|
| id, username    |          | id                          |
| role_id (FK)    |  1  N    | status_code_identifier      |  (StCd-XXXXX, nullable until Review)
| engineering_    |--tags--->| functional_system_group_id  |  (FK)
|   domains (M:N) |          | functional_subgroup_id      |  (FK, mandatory)
+----------------+          | is_sandbox                  |
                              | platform_variant_of_status_ |
                              |   code_id (self-FK, nullable)|
                              | owner_id (FK User)           |
                              +--------------+---------------+
                                             | 1
                                             N
                              +---------------------------------+
                              |     StatusCodeRevision            |
                              |------------------------------------|
                              | id / status_code_id (FK)           |
                              | revision_number / is_current       |
                              | title / description                |
                              | status_category / available_group / alarm_flag     |
                              | set_delay / reset_delay (free text + unit)          |
                              | up_down_counter / trigger_snapshot / loadless_...   |
                              | 8x program reference fields (numeric passthrough)   |
                              | development_access ... customer_access (8 fields) <-- restricted, Admin-confirmed
                              | lifecycle_status (7-state)          |
                              | created_by (FK User)                |
                              | reviewer_signoff_by/at              |
                              | admin_signoff_by/at                 |
                              | chief_engineer_approved_by/date     |
                              | effective_date / deprecated_reason  |
                              +----+------------------+-------------+
                                   | 1:1                | M:N
                        +----------v---------+  +-------v------------------+
                        |   ChangeRequest     |  | StatusCodeRevisionPlatform |
                        |---------------------|  | (join -> TurbinePlatform)  |
                        | id / cr_type         |  +----------------------------+
                        | requested_by (FK)     |
                        | state                 |
                        | chief_engineer_        |
                        |   decided_by/at        |
                        +---+----------------+---+
                            | 1:N            | 1:N
                +-----------v-----+  +-------v-----------+
                |  ReviewComment    |  |   DomainSignoff    |
                |-------------------|  |---------------------|
                | author_id (FK)     |  | engineering_domain_id (FK) |
                | decision (role-    |  | signed_off_by (FK User)     |
                |   tagged enum)      |  | signed_off_at                |
                +-------------------+  +-----------------------------+

+----------------+  1    N  +------------------+
|    Release     |----------|   ReleaseItem     |----> StatusCodeRevision (0..1 each)
+----------------+          +------------------+

+------------------------------+          +-------------------------------------------+
| Lookup: FunctionalSystemGroup |<--FK-----| StatusCode.functional_system_group_id      |
| Lookup: FunctionalSubgroup    |<--FK-----| StatusCode.functional_subgroup_id           |
| Lookup: TurbinePlatform       |<--M:N----| StatusCodeRevisionPlatform                  |
| Lookup: EngineeringDomain     |<--M:N----| User.engineering_domains, DomainSignoff     |
| Lookup: AvailableGroup (soft-validated, numeric, labels TBD)                           |
| Lookup x8: Development/Sales/TCC/Service/TOP/GridOperator/ServicePartner/Customer Access |
+------------------------------+----------+-------------------------------------------+

+-----------------------------------------+
| AuditLogEntry (append-only, no FK)       |
| entity_type/entity_id, action, actor_id, |
| occurred_at, before_value, after_value   |
+-----------------------------------------+

+------------------+
|   ExportJob       |
| export_scope_type: CATALOGUE | FULL_DATABASE (Administrator only)
+------------------+
```

## 4. Lifecycle Note (see 05-governance-handbook.md §4–§5 for full detail)

`Draft → Review → PendingApproval → Approved → Released → Deprecated → Archived`. The `status_code_identifier` is `NULL` throughout `Draft` and is allocated exactly once, atomically, at the Draft→Review transition (never before, never re-allocated).

## 5. Cardinality Summary

| Relationship | Cardinality |
|---|---|
| User → StatusCode (owner) | 1 : N |
| User → EngineeringDomain (tags) | M : N |
| FunctionalSystemGroup → FunctionalSubgroup | 1 : N |
| FunctionalSystemGroup → StatusCode | 1 : N |
| FunctionalSubgroup → StatusCode | 1 : N (mandatory — every StatusCode has exactly one) |
| ImportJob → ChangeRequest | 1 : N (via `cr_type = IMPORT`) |
| StatusCode → StatusCodeRevision | 1 : N |
| StatusCodeRevision → ChangeRequest | 1 : 1 |
| StatusCodeRevision → TurbinePlatform | M : N |
| StatusCode → StatusCode (platform_variant_of) | 0..1 : N (self-referential) |
| ChangeRequest → ReviewComment | 1 : N |
| ChangeRequest → DomainSignoff | 1 : N |
| Release → ReleaseItem | 1 : N |

## 6. Business Ownership Matrix

| Entity | Primary Business Owner | Secondary |
|---|---|---|
| StatusCode / StatusCodeRevision | Controls Engineering (Engineer role) | Governance (Reviewer/Administrator/Chief Engineer decide) |
| FunctionalSystemGroup / FunctionalSubgroup / TurbinePlatform / EngineeringDomain | Governance (Administrator) | Controls Engineering (proposes changes) |
| ChangeRequest / ReviewComment / DomainSignoff | Shared: Engineering initiates and cross-signs, Governance decides | — |
| Release / ReleaseItem | Governance (Administrator) | Technical Publications (consumer) |
| User / Role | Administrator | — |
| AuditLogEntry | System (immutable, with the sandbox-delete exception noted in §2.16) | Quality/Compliance (consumer) |
| ExportJob | System | Administrator (full-database), all roles per matrix (catalogue) |
| ImportJob | Engineering (initiates) | Governance (every resulting Draft still goes through the full review pipeline) |

# 06. Data Dictionary — CSCM Tool

Conventions: **Required** = enforced not-null at both UI and API before the entity can leave Draft (for revision fields) or at all times (for structural fields). Datatypes are given in SQLite-native terms with the logical type in parentheses where useful (see 07-database-design.md for full DDL).

## 1. `status_code` (StatusCode identity)

| Field | Description | Datatype | Required | Default | Validation | Allowed Values | Example |
|---|---|---|---|---|---|---|---|
| `id` | Surrogate primary key | INTEGER (PK) | Yes | auto | system-generated | — | `1042` |
| `status_code_identifier` | Human-readable governed identifier (StCd) | TEXT | No while Draft; Yes from Review onward | `NULL` | `^StCd-\d{5}$` (or `^StCd-T\d{5}$` for sandbox); unique once non-null; allocated atomically at Draft→Review (05-governance-handbook.md §2) | — | `StCd-01232` |
| `functional_system_group_id` | Classification + numbering band | INTEGER (FK → lookup_functional_system_group) | Yes | — | must be `is_active = true` | see §9 | `WCNV` (1000–1999) |
| `functional_subgroup_id` | Sub-classification + numbering sub-band | INTEGER (FK → lookup_functional_subgroup) | No | `NULL` | if set, must belong to the selected `functional_system_group_id` | see §9a (placeholder) | `Subgroup 1 (TBD)` |
| `is_sandbox` | Test/sandbox flag | INTEGER (bool) | Yes | `0` | Administrator-only to set `true` | `0`, `1` | `0` |
| `platform_variant_of_status_code_id` | Optional pointer to the originating code this one was split from across Turbine Platforms | INTEGER (FK → status_code.id, nullable) | No | `NULL` | must reference a different Status Code | — | `988` |
| `owner_id` | Accountable engineer | INTEGER (FK → user.id) | Yes | creator's id | active user, Engineer or Administrator role | — | `14` |
| `created_at` | Row creation timestamp (UTC) | TEXT (ISO-8601) | Yes | `now()` | system-generated | — | `2026-03-02T09:14:00Z` |

## 2. `status_code_revision` (the governed, versioned record)

| Field | Description | Datatype | Required | Default | Validation | Allowed Values | Example |
|---|---|---|---|---|---|---|---|
| `id` | Surrogate primary key | INTEGER (PK) | Yes | auto | system-generated | — | `5031` |
| `status_code_id` | Parent Status Code | INTEGER (FK) | Yes | — | must reference existing status_code | — | `1042` |
| `revision_number` | Sequential revision counter per Status Code | INTEGER | Yes | `1` | monotonic, never reused | ≥ 1 | `2` |
| `is_current` | Flags the single "current" revision per code | INTEGER (bool) | Yes | `1` | exactly one `true` per `status_code_id` | `0`, `1` | `1` |
| `title` | Short human-readable name (Engineering Domain: any) | TEXT | Yes | — | 1–120 chars; must not equal Description | — | `Converter Grid Undervoltage Trip` |
| `description` | Full technical description (Engineering Domain: any) | TEXT | Yes | — | 10–4000 chars | — | `Triggered when converter DC-link voltage falls below the configured threshold for more than 3 seconds during grid-connected operation.` |
| `status_category_id` | Classification (Engineering Domain: any) | INTEGER (FK → lookup_status_category) | Yes | — | must be `is_active = true` | see §9c | `FAULT` |
| `availability_group_id` | Availability accounting group (Engineering Domain: any) | INTEGER (FK → lookup_availability_group) | Yes | — | must be `is_active = true` | see §9d | `A` |
| `brake_program_id` | Braking program invoked, if any (Engineering Domain: CONTROLS) | INTEGER (FK → lookup_brake_program) | Yes | `BP-NONE` | must be `is_active = true` | see §9e | `BP-2` |
| `reset_program_id` | How the condition is cleared (Engineering Domain: CONTROLS) | INTEGER (FK → lookup_reset_program) | Yes | — | must be `is_active = true` | see §9f | `MANUAL` |
| `software_version` | Firmware/software version first valid for this code (Engineering Domain: CONTROLS) | TEXT | Yes | — | `^\d+\.\d+(\.\d+)?$` | — | `4.12.0` |
| `operational_state_id` | Turbine operational state (Engineering Domain: CONTROLS) | INTEGER (FK → lookup_operational_state) | Yes | — | must be `is_active = true` | see §9g | `STOPPED` |
| `access_rights_id` | **Restricted field** — who may act on this code operationally | INTEGER (FK → lookup_access_rights) | Yes | `SERVICE` | Engineer may propose; only authoritative once confirmed at the Administrator's Review sign-off (04-domain-model.md §2.9) | see §9h | `OEM_ONLY` |
| `delay_before_alarm_seconds` | Debounce delay before alarm (Engineering Domain: CONTROLS) | INTEGER | Yes | `0` | 0–3600; required > 0 if `alarm_behaviour_id = ESCALATING` | 0–3600 | `3` |
| `delay_before_reset_seconds` | Minimum clear time before auto-reset (Engineering Domain: CONTROLS) | INTEGER | Yes | `0` | 0–86400 | 0–86400 | `30` |
| `alarm_behaviour_id` | How the alarm presents/persists (Engineering Domain: CONTROLS) | INTEGER (FK → lookup_alarm_behaviour) | Yes | — | if `status_category_id = SAFETY`, must be `LATCHING` or `ESCALATING` | see §9i | `LATCHING` |
| `owner_id` | Accountable engineer for this revision | INTEGER (FK → user.id) | Yes | inherited | active user, Engineer/Administrator | — | `14` |
| `lifecycle_status` | Current governance state (05-governance-handbook.md §4) | TEXT (enum) | Yes | `DRAFT` | must follow valid transitions | `DRAFT`,`REVIEW`,`PENDING_APPROVAL`,`APPROVED`,`RELEASED`,`DEPRECATED`,`ARCHIVED` | `PENDING_APPROVAL` |
| `created_by` | Engineer who authored this revision | INTEGER (FK → user.id) | Yes | current user | — | — | `14` |
| `created_at` | Revision creation timestamp | TEXT (ISO-8601) | Yes | `now()` | — | — | `2026-03-02T09:14:00Z` |
| `reviewer_signoff_by` | Reviewer (Sub-PO for StCd) who signed off | INTEGER (FK → user.id, role=REVIEWER) | No | `NULL` | ≠ `created_by` | — | `22` |
| `reviewer_signoff_at` | Timestamp of Reviewer sign-off | TEXT (ISO-8601) | No | `NULL` | — | — | `2026-03-06T14:02:00Z` |
| `admin_signoff_by` | Administrator (Product Owner) who signed off | INTEGER (FK → user.id, role=ADMINISTRATOR) | No | `NULL` | ≠ `created_by` | — | `2` |
| `admin_signoff_at` | Timestamp of Administrator sign-off | TEXT (ISO-8601) | No | `NULL` | — | — | `2026-03-06T15:40:00Z` |
| `chief_engineer_approved_by` | Chief Engineer who approved | INTEGER (FK → user.id, role=CHIEF_ENGINEER) | No | `NULL` | ≠ `created_by`, ≠ `reviewer_signoff_by`, ≠ `admin_signoff_by` | — | `31` |
| `chief_engineer_approval_date` | Timestamp of Chief Engineer approval | TEXT (ISO-8601) | No | `NULL` | — | — | `2026-03-08T09:00:00Z` |
| `effective_date` | Date the revision became Released | TEXT (ISO-8601) | No | `NULL` | set only at Release publish | — | `2026-03-15T00:00:00Z` |
| `deprecated_reason` | Why the code was deprecated | TEXT | Required if `lifecycle_status = DEPRECATED` | `NULL` | 10–2000 chars when present | — | `Superseded by revised undervoltage threshold logic in v5.0.` |
| `superseded_by_status_code_id` | Optional pointer to replacement code | INTEGER (FK → status_code.id) | No | `NULL` | must reference a different Status Code | — | `1090` |

## 2a. Field-to-Engineering-Domain Ownership

Used to determine Cross-Domain Sign-Off requirements (05-governance-handbook.md §6a). "Any" means no cross-domain gate applies to that field.

| Field | Owning Domain |
|---|---|
| `title`, `description`, `status_category_id`, `availability_group_id` | Any |
| `brake_program_id`, `reset_program_id`, `software_version`, `operational_state_id`, `delay_before_alarm_seconds`, `delay_before_reset_seconds`, `alarm_behaviour_id` | CONTROLS |
| `access_rights_id` | Governance (Administrator-confirmed, not Engineer-domain-gated — see §2 restricted-field note) |

If the originating Engineer is not tagged with a field's owning domain, that domain is marked "pending" on the Change Request until a `DomainSignoff` from an Engineer holding that domain is recorded.

## 3. `status_code_revision_platform` (Turbine Platform, multi-select)

| Field | Description | Datatype | Required | Default | Validation | Allowed Values | Example |
|---|---|---|---|---|---|---|---|
| `id` | Surrogate PK | INTEGER | Yes | auto | — | — | `77` |
| `status_code_revision_id` | Parent revision | INTEGER (FK) | Yes | — | — | — | `5031` |
| `turbine_platform_id` | Applicable platform | INTEGER (FK → lookup_turbine_platform) | Yes | — | — | see §9b | `3XM` |

At least one Turbine Platform must be selected before a revision can be submitted for Review.

## 4. `change_request`

| Field | Description | Datatype | Required | Default | Validation | Allowed Values | Example |
|---|---|---|---|---|---|---|---|
| `id` | Surrogate PK | INTEGER | Yes | auto | — | — | `881` |
| `status_code_revision_id` | The revision this CR carries | INTEGER (FK, unique) | Yes | — | 1:1 with revision | — | `5031` |
| `cr_type` | Nature of the request | TEXT (enum) | Yes | — | — | `NEW`,`REVISION`,`DEPRECATION` | `REVISION` |
| `requested_by` | Author | INTEGER (FK → user.id) | Yes | current user | — | — | `14` |
| `justification` | Free-text reason for the change | TEXT | Yes for `REVISION`/`DEPRECATION` | `NULL` | 10–2000 chars when required | — | `Aligns threshold with updated converter vendor datasheet.` |
| `state` | Workflow state (mirrors revision lifecycle) | TEXT (enum) | Yes | `DRAFT` | — | `DRAFT`,`REVIEW`,`PENDING_APPROVAL`,`APPROVED`,`REJECTED`,`WITHDRAWN` | `PENDING_APPROVAL` |
| `submitted_at` | When moved Draft→Review (identifier allocated at this instant) | TEXT (ISO-8601) | No | `NULL` | — | — | `2026-03-04T10:00:00Z` |
| `chief_engineer_decided_at` | When Chief Engineer decided | TEXT (ISO-8601) | No | `NULL` | — | — | `2026-03-08T09:00:00Z` |
| `chief_engineer_decided_by` | Chief Engineer who decided | INTEGER (FK → user.id) | No | `NULL` | ≠ `requested_by` | — | `31` |

## 5. `review_comment`

| Field | Description | Datatype | Required | Default | Validation | Allowed Values | Example |
|---|---|---|---|---|---|---|---|
| `id` | Surrogate PK | INTEGER | Yes | auto | — | — | `3310` |
| `change_request_id` | Parent CR | INTEGER (FK) | Yes | — | — | — | `881` |
| `author_id` | Commenter | INTEGER (FK → user.id) | Yes | current user | — | — | `22` |
| `comment_text` | Comment content | TEXT | Yes | — | 1–4000 chars | — | `Please confirm this threshold against the latest datasheet revision.` |
| `decision` | Decision recorded with this comment, role-tagged so the system can verify both required Review sign-offs came from distinct roles | TEXT (enum) | No | `NULL` | required (non-null) for a decision-bearing action | `REVIEWER_APPROVE`,`REVIEWER_REJECT`,`ADMIN_APPROVE`,`ADMIN_REJECT`,`CHIEF_ENGINEER_APPROVE`,`CHIEF_ENGINEER_REJECT` | `ADMIN_APPROVE` |
| `created_at` | Timestamp | TEXT (ISO-8601) | Yes | `now()` | — | — | `2026-03-05T11:20:00Z` |

## 6. `domain_signoff`

| Field | Description | Datatype | Required | Default | Validation | Allowed Values | Example |
|---|---|---|---|---|---|---|---|
| `id` | Surrogate PK | INTEGER | Yes | auto | — | — | `410` |
| `change_request_id` | Parent CR | INTEGER (FK) | Yes | — | — | — | `881` |
| `engineering_domain_id` | Domain being signed off | INTEGER (FK → lookup_engineering_domain) | Yes | — | — | see §9j | `CONTROLS` |
| `signed_off_by` | Engineer providing the sign-off | INTEGER (FK → user.id) | Yes | current user | must hold `engineering_domain_id` per their `user_engineering_domain` tags | — | `19` |
| `signed_off_at` | Timestamp | TEXT (ISO-8601) | Yes | `now()` | — | — | `2026-03-03T08:00:00Z` |

## 7. `release` / `release_item`

Unchanged in shape from the original design; `scope_filter` on `release` now expresses Functional System Group / Subgroup rather than Controller Type, e.g. `{"functional_system_group":"WCNV"}`.

## 8. `user` / `user_engineering_domain`

| Field | Description | Datatype | Required | Default | Validation | Allowed Values | Example |
|---|---|---|---|---|---|---|---|
| `id` | Surrogate PK | INTEGER | Yes | auto | — | — | `14` |
| `username` | Login identifier | TEXT | Yes | — | unique; 3–40 chars | — | `j.mueller` |
| `email` | Contact email | TEXT | Yes | — | unique; valid email format | — | `j.mueller@example.com` |
| `password_hash` | Hashed credential | TEXT | Yes | — | bcrypt/argon2 hash | — | `$argon2id$...` |
| `full_name` | Display name | TEXT | Yes | — | 1–120 chars | — | `Jana Müller` |
| `role_id` | Assigned role | INTEGER (FK → lookup_role) | Yes | `VIEWER` | — | `ADMINISTRATOR`,`ENGINEER`,`REVIEWER`,`CHIEF_ENGINEER`,`VIEWER` | `ENGINEER` |
| `is_active` | Account enabled flag | INTEGER (bool) | Yes | `1` | — | `0`,`1` | `1` |
| `created_at` | Account creation timestamp | TEXT (ISO-8601) | Yes | `now()` | — | — | `2025-11-01T00:00:00Z` |
| `last_login_at` | Last successful login | TEXT (ISO-8601) | No | `NULL` | — | — | `2026-03-14T07:55:00Z` |
| `failed_login_count` | Consecutive failed logins | INTEGER | Yes | `0` | resets on success | — | `0` |
| `locked_until` | Lockout expiry | TEXT (ISO-8601) | No | `NULL` | — | — | `NULL` |

`user_engineering_domain` (join, Engineer-role users only): `id`, `user_id` (FK), `engineering_domain_id` (FK).

## 9. Controlled Vocabularies (Lookup Tables)

Shared shape: `id`, `code`, `label`, `description`, `is_active` (default `1`), `sort_order`.

### 9. `lookup_functional_system_group`
| code | label | range_start | range_end |
|---|---|---|---|
| `WCNV` | Converter / Grid Interface | 1000 | 1999 |
| `WGEN` | Generator | 2000 | 2999 |
| `WNAC` | Meteorology / Environment / Nacelle Monitoring | 3000 | 3999 |
| `WROT` | Pitch System / Hub | 4000 | 4999 |
| `WTOW` | Tower / Oscillation Monitoring | 5000 | 5999 |
| `WTRF` | Transformer / MV Switchgear | 6000 | 6999 |
| `WTRM` | Drive Train / Gearbox / Hydraulic System / Rotor Brake | 7000 | 7999 |
| `WYAW` | Yaw System | 8000 | 8999 |
| `WTUR` | Turbine Control / Safety / Operational States / SCADA | 9000 | 9999 |

### 9a. `lookup_functional_subgroup` — **PLACEHOLDER, pending Controls Engineering input**
Seeded generically as three even sub-bands per group, e.g. for `WCNV` (1000–1999): `WCNV-1 Subgroup 1 (TBD)` 1000–1332, `WCNV-2 Subgroup 2 (TBD)` 1333–1665, `WCNV-3 Subgroup 3 (TBD)` 1666–1999. The same pattern repeats for all nine groups. **Replace this table's data with the real subgroup taxonomy before go-live** — no schema change is needed to do so.

### 9b. `lookup_turbine_platform`
| code | label |
|---|---|
| `2XM` | 2XM Platform |
| `3XM` | 3XM Platform |
| `4XM` | 4XM Platform |

Extensible — Administrator may add further platforms.

### 9c. `lookup_status_category`
| code | label | Notes |
|---|---|---|
| `FAULT` | Fault | Turbine-stopping condition |
| `WARNING` | Warning | Non-stopping abnormal condition |
| `SAFETY` | Safety | Constrains `alarm_behaviour_id` |
| `OPERATIONAL` | Operational | Normal operating-state transition |
| `MAINTENANCE` | Maintenance | Maintenance-mode related |
| `INFORMATION` | Information | Informational/log-only |

### 9d. `lookup_availability_group`
| code | label |
|---|---|
| `A` | Group A — Full Stop |
| `B` | Group B — Partial Derate |
| `C` | Group C — Scheduled |
| `D` | Group D — No Impact |

### 9e. `lookup_brake_program`
| code | label | Notes |
|---|---|---|
| `BP-NONE` | No Brake Action | Default |
| `BP-1` | Soft Aerodynamic Brake | — |
| `BP-2` | Full Aerodynamic Brake | — |
| `BP-3` | Mechanical Brake Assist | — |
| `BP-4` | Emergency Brake | Requires `status_category_id ∈ {FAULT, SAFETY}` |

### 9f. `lookup_reset_program`
| code | label | Notes |
|---|---|---|
| `AUTO` | Automatic Reset | Requires `delay_before_reset_seconds > 0` |
| `MANUAL` | Manual Reset (Local) | — |
| `REMOTE` | Manual Reset (Remote/SCADA) | — |
| `SCHEDULED` | Scheduled Reset Window | — |

### 9g. `lookup_operational_state`
| code | label |
|---|---|
| `RUNNING` | Running |
| `STOPPED` | Stopped |
| `IDLE` | Idle |
| `FAULT` | Fault State |
| `MAINTENANCE` | Maintenance Mode |
| `POWER_CURTAILED` | Power Curtailed |

### 9h. `lookup_access_rights`
| code | label |
|---|---|
| `SERVICE` | Service Technician |
| `CUSTOMER` | Customer-Visible |
| `OEM_ONLY` | OEM Engineering Only |
| `LEVEL_1`–`LEVEL_4` | Tiered access levels |

### 9i. `lookup_alarm_behaviour`
| code | label | Notes |
|---|---|---|
| `LATCHING` | Latching | Requires explicit reset |
| `SELF_CLEARING` | Self-Clearing | — |
| `ESCALATING` | Escalating | — |
| `SILENT` | Silent (Log-Only) | Disallowed for `SAFETY` category |

### 9j. `lookup_engineering_domain`
| code | label |
|---|---|
| `CONTROLS` | Controls Engineering |
| `ELECTRICAL` | Electrical Engineering |
| `MECHANICAL` | Mechanical Engineering |
| `GRID` | Grid / Power Systems Engineering |
| `SAFETY` | Functional Safety Engineering |

## 10. `audit_log_entry`

Unchanged shape from v1 (`id`, `entity_type`, `entity_id`, `action`, `actor_id`, `occurred_at`, `before_value`, `after_value`, `ip_address`, `request_id`) — see 12-audit-compliance.md §2 for the updated action catalogue including `REVIEWER_SIGNOFF`, `ADMIN_SIGNOFF`, `CHIEF_ENGINEER_APPROVE`, `SANDBOX_CREATE`, `SANDBOX_DELETE`.

## 11. `export_job`

Unchanged shape, plus `export_scope_type` (`CATALOGUE` | `FULL_DATABASE`); `FULL_DATABASE` requires the Administrator role (08-system-architecture.md §6).

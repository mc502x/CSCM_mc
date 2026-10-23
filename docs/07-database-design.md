# 07. Database Design Document — CSCM Tool

## 1. Overview

MVP persistence is **SQLite** (single file, per C-001 in 03-srs.md), accessed exclusively through a repository layer (18-claude-code-implementation-guide.md) so a future migration to PostgreSQL requires no changes above the repository interface. The database runs on a local, on-premises server only — see 14-deployment-architecture.md §1 — and is itself the Master Database referenced throughout this package; no external upstream system exists. The full DDL is maintained at [artifacts/schema.sql](artifacts/schema.sql) (schema v4.9: 59 tables, 14 triggers; the optional search index is in [artifacts/schema-fts5.sql](artifacts/schema-fts5.sql)) and is the executable source of truth; this document explains the design decisions behind it.

## 2. Logical Schema

The logical model mirrors 04-domain-model.md. Key v2 decisions (delta from the original Controller-Type-based design):

- **Functional System Group replaces Controller Type entirely.** `status_code.functional_system_group_id` is now the sole classification and numbering axis; the *Controller Type* of v1 is gone as a numbering axis. (v4 re-introduces a `controller_type` flag `MAIN` | `HUB` on the group — not on the code — purely so Hub groups can be listed and consolidated into Main groups; it never influences numbering, decision D-06, §12.) `lookup_functional_system_group` carries the numeric range (`range_start`/`range_end`) that drives allocation (§7a).
- **Functional Subgroup is a child lookup, not a separate table per group.** One `lookup_functional_subgroup` table, FK'd to its parent group, holding a sub-range — this lets subgroups (the real taxonomy is seeded per 06-data-dictionary.md §9a) be added or amended later with a pure data change, never a schema migration. Unassigned hundred-blocks within a group's range are intentional reserved capacity, not gaps to be closed.
- **The identifier is nullable until Review.** `status_code.status_code_identifier` is `NULL` throughout Draft and is set exactly once, atomically, at the Draft→Review transition (07-database-design.md §7a) — this is why it is a plain `UNIQUE` column rather than `NOT NULL UNIQUE`: SQLite's `UNIQUE` constraint allows multiple `NULL`s by design, which is exactly the behavior needed (many concurrent Drafts, all with `NULL` identifiers, one real identifier per code from Review onward).
- **Turbine Platform is genuinely M:N.** `status_code_revision_platform` is a true join table (unlike the single-valued lookups), because a revision can legitimately apply to more than one platform.
- **Dual review is modeled as two nullable sign-off columns plus a role-tagged comment log**, not a generic "approvals" table — `reviewer_signoff_by/at` and `admin_signoff_by/at` are both on `status_code_revision` directly so the "has this revision cleared Review" check is a simple two-column NULL check, while `review_comment.decision` carries the full role-tagged history for audit purposes.
- **Chief Engineer approval is a third, independent set of columns** (`chief_engineer_approved_by/date`) plus `change_request.chief_engineer_decided_by/at`, kept structurally distinct from the Reviewer/Administrator sign-offs so segregation-of-duties checks (no overlap between author, reviewer, admin, chief engineer) are simple column comparisons, enforced redundantly at the `CHECK` constraint level (§4).
- **Sandbox status codes reuse the existing `status_code` table** (`is_sandbox` flag) rather than a parallel table, so the same lifecycle/validation code paths apply to sandbox testing as to real records — the only behavioral differences are numbering source, Release-eligibility (blocked by trigger, §5), and delete permission (also trigger-enforced).

## 3. Physical Schema

See [artifacts/schema.sql](artifacts/schema.sql) for full DDL. Summary of tables:

| Table | Purpose |
|---|---|
| `role` | 6-row role lookup (Administrator, Engineer, Reviewer, Chief Engineer, Viewer, StCd Owner) |
| `lookup_engineering_domain` | Engineer specialty tags, drives Cross-Domain Sign-Off |
| `lookup_functional_system_group` | 12-row numbering band lookup (9 Main Controller + 3 Hub Controller groups, §5a), with `controller_type` (v4) |
| `lookup_functional_subgroup` | Real sub-band lookup (38 seeded subgroups: 27 Main + 11 Hub), child of the above, with reserved capacity for more |
| `lookup_turbine_platform` | Multi-select platform lookup (2XM/3XM/4XM, extensible) |
| `lookup_available_group` | Soft-validated numeric availability codes, labels TBD (corrected 2026-09-17) |
| `lookup_development_access`, `lookup_sales_access`, `lookup_tcc_access`, `lookup_service_access`, `lookup_top_access`, `lookup_grid_operator_access`, `lookup_service_partner_access`, `lookup_customer_access` | Eight independent audience-access vocabularies, real observed values (corrected 2026-09-17, replaces the single `lookup_access_rights`) |
| `user`, `user_engineering_domain` | Accounts and their domain tags; the e-mail address cannot be changed (trigger, v4.7) |
| `language_reviewer`, `translation_review`, `translation_review_item`, `translation_override` *(v4.7)* | Native-speaker review of the interface translations: assignments, reviews, answers and proposals, accepted overrides (FR-164) |
| `terminology_term`, `terminology_translation` *(v4.9)* | The technical nomenclature: the terms of the controller and the workflow and their translation per language, a draft until a second person approves it (FR-166) |
| `status_code` | Governed identity, nullable identifier, sandbox flag |
| `status_code_revision` | Versioned governed content, dual-review + Chief Engineer approval columns |
| `status_code_revision_platform` | Revision ↔ Turbine Platform join |
| `change_request` | Workflow carrier for a revision |
| `review_comment` | Role-tagged comments/decisions on a CR |
| `domain_signoff` | Cross-Domain Sign-Off records |
| `user_password_history` | Hashes of retired passwords for the last-5 reuse rule |
| `domain_signoff_request` | Originating Engineer's request for a domain sign-off, optionally addressed to a named Engineer (FR-028) |
| `release`, `release_item` | Named, versioned export bundle and membership |
| `audit_log_entry` | Immutable action log |
| `export_job` | Export generation record: scope (CATALOGUE, FULL_DATABASE, RELEASE_NOTES, OFFLINE_BUNDLE), SHA-256, size, rows, profile, audience, language, software version, manifest (v4) |
| `lookup_controller_software_version`, `release_target_version` *(v4)* | Ordered software versions; the versions a Release targets (FR-106) |
| `lookup_language`, `revision_translation` *(v4)* | Content languages and per-revision translations (FR-110) |
| `export_profile` *(v4)* | Administrator-managed export column sets (FR-100) |
| `change_set` *(v4)* | Grouping of change requests for one software release (FR-124) |
| `delegation`, `notification`, `app_setting`, `login_attempt` *(v4)* | Out-of-office cover; in-app notices; Administrator settings; shared rate-limit counters |
| `cr_attachment`, `field_comment`, `review_checklist_item`, `cr_checklist_confirmation` *(v4)* | Evidence, field-level comments, review checklist and its confirmations |
| `saved_search`, `occurrence_import`, `code_occurrence` *(v4)* | Saved views; fleet-feedback counts |
| `api_token`, `webhook`, `webhook_delivery`, `hub_mc_mapping` *(v4)* | Machine access and Hub-to-Main mapping |
| `status_code_fts`, `status_code_fts_vocab` *(v4, optional)* | FTS5 search index and its vocabulary; absent where SQLite has no FTS5 (the search falls back to substring matching) |

Field-level detail of every table: 06-data-dictionary.md (§13 for the v4 tables).

## 4. Primary Keys, Foreign Keys, Constraints

Surrogate `INTEGER PRIMARY KEY` throughout; foreign keys enforced (`PRAGMA foreign_keys = ON` on every connection). Natural-key uniqueness: `status_code.status_code_identifier` (nullable-safe unique, §2). `status_code_revision (status_code_id, revision_number)` unique. Segregation-of-duties is enforced at three independent `CHECK` constraints on `status_code_revision`: `reviewer_signoff_by <> created_by`, `admin_signoff_by <> created_by`, and a compound check that `chief_engineer_approved_by` differs from all three of `created_by`, `reviewer_signoff_by`, and `admin_signoff_by`. `change_request.chief_engineer_decided_by <> requested_by` mirrors this at the workflow-object level.

## 5. Indexes & Enforced Invariants

| Index / Trigger | Enforces |
|---|---|
| `ux_revision_current_per_code` | Exactly one current revision per code |
| `ux_one_open_cr_per_code` (now spans `DRAFT`,`REVIEW`,`PENDING_APPROVAL`) | Only one open change per code at a time |
| `trg_prevent_edit_locked_revision` | No in-place edit of Approved/Released/Archived revisions |
| `trg_prevent_release_item_delete` | Published Release contents are immutable |
| `trg_prevent_sandbox_release` | A sandbox-flagged revision can never be inserted into `release_item` — hard-blocks the one dangerous path a sandbox code could otherwise take |
| `trg_audit_no_update` / `trg_audit_no_delete` (new 2026-10-21) | `audit_log_entry` is append-only at the database layer — any UPDATE or DELETE aborts, so not even a defect or direct SQL access through the application connection can rewrite history (FR-072, FR-073) |
| `trg_prevent_nonsandbox_delete` | `DELETE FROM status_code` is rejected unless `is_sandbox = 1` — the single, narrow exception to the no-hard-delete rule (05-governance-handbook.md §12) is enforced at the database layer, not only in application code |
| `ux_status_code_reserved_identifier`, `trg_identifier_matches_reservation`, `trg_reservation_not_issued_elsewhere`, `trg_identifier_not_reserved_elsewhere` *(v4.2)* | A number reserved by an imported program belongs to one code only and is issued to that code unchanged (BR-023) |
| `trg_prevent_subgroup_overlap` | A new `lookup_functional_subgroup` row is rejected if its sub-range overlaps an existing subgroup in the same group (06-data-dictionary.md §9a.1) |
| Unique constraints on `notification.dedupe_key`, `api_token.token_hash`, `hub_mc_mapping.hub_status_code_id`, `revision_translation (revision, language)`, `release_target_version (release, version)` *(v4)* | One reminder per user/CR/stage/level/day; no duplicate tokens; one MC replacement per Hub code; one translation per language; no duplicate targets |
| `CHECK (approved_by <> translated_by)` on `revision_translation`, `CHECK (delegator_id <> delegate_id)` on `delegation`, `CHECK (hub_status_code_id <> mc_status_code_id)` on `hub_mc_mapping` *(v4)* | BR-018, BR-017 and the mapping sanity rule at the database layer |
| `trg_prevent_group_overlap` (new 2026-09-17) | A new `lookup_functional_system_group` row is rejected if its range overlaps an existing group's range — lets an Administrator assign a whole new group into `10000–10999`/`14000–14999`/`15000–15999`/`16000–16999` safely (06-data-dictionary.md §9.1) |

## 5a. Hub Controller Groups & Non-Unique Prefixes (new 2026-09-17)

A real export of the Hub Controller status code library (`HC Status Code Number.xlsx`, 264 rows, range 11000–13999) revealed that Hub Controller content is **not** folded into the existing nine Main Controller groups — it gets three entirely new, numerically distinct groups (`WTUR` 11000–11999, `WROT` 12000–12999, `WPPD` 13000–13999), confirmed by the business as intentional and structurally identical to the existing model (each subdivides into real subgroups the same way, 06-data-dictionary.md §9a). The one design consequence: `WTUR` and `WROT` are each now deliberately reused across two different groups (one Main Controller, one Hub Controller), so `lookup_functional_system_group.code` **is no longer a unique key on its own** — uniqueness moved to `(code, range_start)`. Every seed-data join and every application-layer lookup of a group must resolve by `(code, range_start)` or by `id`, never by `code` alone; `artifacts/schema.sql`'s subgroup seed INSERT was rewritten with an explicit `group_range_start` disambiguator for exactly this reason.

## 6. Soft-Delete Strategy

No hard delete of governance-relevant data, **except** sandbox Status Codes, which may be permanently deleted by an Administrator (`trg_prevent_nonsandbox_delete` is the only thing that makes this possible at all — every other record is structurally undeletable). The service layer must write a `SANDBOX_DELETE` audit entry, capturing a full JSON snapshot of the record in `before_value`, in the same transaction as the delete, so the fact of creation-and-deletion survives even though the row does not (12-audit-compliance.md §2).

## 7. Versioning Strategy

Revisions are stored row-per-revision and a Release is published atomically. Optimistic concurrency on Draft edits is, since v4, real: `status_code_revision.row_version` (INTEGER, starts at 1, +1 on every save) and `updated_at` back the `expected_row_version` / `expected_updated_at` check of FR-090, and a stale save changes nothing. Two further points:

### 7a. Atomic Identifier Allocation

Allocating the `status_code_identifier` at Draft→Review is a single transaction that must be race-safe under SQLite's single-writer model: `BEGIN IMMEDIATE` acquires the write lock before reading the current max-allocated number in the target range/sub-range, guaranteeing no two concurrent submissions can be handed the same number. The allocation query is:

```sql
-- within functional_system_group (no subgroup selected)
SELECT COALESCE(MAX(CAST(SUBSTR(status_code_identifier, 6) AS INTEGER)), range_start - 1) + 1
FROM status_code sc
JOIN lookup_functional_system_group g ON g.id = sc.functional_system_group_id
WHERE sc.functional_system_group_id = :group_id
  AND sc.status_code_identifier IS NOT NULL
  AND CAST(SUBSTR(sc.status_code_identifier, 6) AS INTEGER) BETWEEN g.range_start AND g.range_end;

-- within a selected subgroup, bounded to its sub_range_start/sub_range_end instead
```

If the computed next number exceeds the (sub)range's upper bound, the service layer raises a capacity-exhausted domain error rather than allocating out of range — this is treated as an operational event requiring Administrator/Controls-Engineering attention (range exhaustion should be rare given 1000-number bands, but the system does not silently overflow into a neighboring group).

### 7b. Dual Sign-Off & Approval Atomicity

`Review → PendingApproval` is system-triggered, not user-triggered: the service method that records a Reviewer or Administrator sign-off checks, within the same transaction, whether the *other* required sign-off column is already non-null; if so, it also sets `lifecycle_status = 'PENDING_APPROVAL'` in that same write. This means the second sign-off action and the state transition are always one atomic operation — there is no window where both sign-offs exist but the state has not yet advanced.

## 8. Audit Strategy

One `audit_log_entry` per state-changing service call, in the same transaction. Action codes are listed in 12-audit-compliance.md §2. Since v4 a `before_flush` hook gives every new row `prev_hash` and `entry_hash` (the hash of the previous row's fields chained forward, §12); the append-only triggers stop in-application edits and the chain makes edits by someone *with database access* detectable.

## 9. Migration Path Beyond SQLite

The schema avoids SQLite-specific typing quirks and uses portable ISO-8601 text timestamps; what is SQLite-specific is inventoried in §12 and counted by CI. The PL/pgSQL equivalents of the triggers are to be produced at the time of a Phase 3 PostgreSQL migration (16-mvp-roadmap.md).

## 10. Locking and Transactions *(v4)*

SQLite runs in WAL mode (readers never block the writer) with a 15 s busy timeout, so a writer queues behind another instead of failing. Every write transaction starts with `BEGIN IMMEDIATE` (taking the write lock up front is what makes number allocation §7a, the audit chain §12 and the login rate limit race-safe across worker processes); read-only requests (GET/HEAD/OPTIONS not flagged as writing) use a plain deferred `BEGIN`. The time spent waiting for the write lock is measured and exported as the histogram `cscm_db_lock_wait_seconds` (FR-153). `PRAGMA foreign_keys = ON` is set on every connection. Both settings are applied only to SQLite connections (dialect guard in `app/__init__.py`).

## 11. Migrations *(v4)*

Alembic, one linear chain. The baseline executes `docs/artifacts/schema.sql` verbatim, so a fresh database is by construction the documented schema; later revisions are guarded (each step checks whether its change is already present) and idempotent, which is what lets the same chain upgrade both a v3 database and a fresh one.

| Revision | Purpose |
|---|---|
| `9dc07a07a48b` | initial schema from `schema.sql` |
| `b4d2f6a8c0e1` | reviewer assignment, domain sign-off requests, audit append-only triggers, lookup descriptions |
| `c5e7a9b1d3f2` | password history (last-5 reuse block) |
| `d6f8b0c2e4a3` | first subgroup of each Main Controller group covers the first 200 numbers |
| `e7a1c3d5f901` | **v4 schema**: improvement pack I-01 … I-36 (new tables and columns, widened `export_job`, audience visibility, language and profile seeds) |
| `f8b2d4e6a012` | **audit hash chain** (back-fills `prev_hash`/`entry_hash` with the append-only trigger temporarily dropped) and the **FTS5 index** (populated from existing revisions) |
| `a1d4f6b8c203` | **Hub sub-bands aligned to the hundreds** (each Hub subgroup shifted down by one number, e.g. Pitch Drivers 12301–12400 → 12300–12399; guarded; refuses to run if a code is already allocated outside its new band) |
| `c9e2a4b6d815` | **schema v4.1**: `status_code.prg_idx` (unique index, frozen-after-release trigger, optional required-from-Review trigger), the further Main and Hub revision columns, the 16 user-group slots with per-revision levels, default levels on the eight audience lookups; guarded and idempotent, existing rows keep `NULL` / 0 |
| `b3f5a7c9d124` | **schema v4.2**: `status_code.reserved_identifier` with its unique index and three guard triggers, `import_job` rebuilt for the `ST` source format and `change_set_id` (run with `legacy_alter_table` so `change_request` keeps pointing at it), the `import_source_item` provenance table; every step guarded |
| `d4a6c8e0f236` | **schema v4.3**: the role `STCD_OWNER`, the languages French, Hindi and Georgian with flags in their names, `user.ui_language` widened (the `user` table is rebuilt; foreign keys are switched off for the migration and checked at its end, `migrations/env.py`) |
| `e5b7d9f1a347` | **schema v4.4**: the language Arabic, language names as country letters, name, flag emoji; `user.ui_language` accepts six codes (second rebuild of `user`, same technique) |
| `f6c8e0a2b459` | **subgroup codes without letters or dashes**: `099xx-a` … `-f` become `0990x` … `0999x`, `11-0xx` becomes `110xx`, `12-0xxB` becomes `1205x` and so on (matched on group, range and old code) |
| `a7d9b1c3e560` | **schema v4.5**: ten more languages (Bengali … Punjabi) in the language lookup; `user.ui_language` becomes a two-letter code without a list (third and last rebuild of `user` for a language) |
| `b8e0c2d4f671` | **schema v4.6**: Spanish, Italian and Danish in the language lookup; Georgian moved to the end of the list (sort order 20) |
| `c9f1d3e5a782` | **schema v4.7**: the trigger `trg_user_email_immutable` — the e-mail address of a user can no longer be updated (FR-162); guarded, so it is created once |
| `d0a2e4f6b893` | **schema v4.7**: the translation review — `language_reviewer`, `translation_review` (with the partial unique index of the open review), `translation_review_item`, `translation_override` (FR-164) |
| `e1b3f5a7c904` | **schema v4.9**: the technical nomenclature — `terminology_term`, `terminology_translation` (FR-166) |

Tests keep this honest (`tests/integration/test_schema_upgrade.py`): a frozen copy of the v3 schema (`tests/fixtures/schema_d6f8b0c2e4a3.sql`) is filled with data and upgraded — data survives, defaults are sensible, `Covert` is hidden, Hub groups are `HUB`, old audit rows are chained and verify, the index is filled, an upgraded database has the same tables and columns as a fresh one, and the downgrade to v3 keeps the data. Before upgrading a live database the installer takes a verified backup (14-deployment-architecture.md §4).

## 12. Schema v4 and Portability *(v4)*

**What v4 adds** (details: 06-data-dictionary.md §13): the controller software version model (D-01), translations (D-03), export profiles, change sets, delegation, notifications, evidence, field comments and review checklist, saved searches, occurrence feedback, API tokens and webhooks, the Hub-to-Main mapping, Administrator settings, shared rate-limit counters, `audience_visible` on the access lookups (D-02), `controller_type` on the group (D-06), concurrency columns on the revision, and the audit hash chain.

**Audit hash chain (AUD-074).** `entry_hash = SHA-256(canonical JSON [entity_type, entity_id, action, actor_id, occurred_at, before_value, after_value, ip_address, request_id, prev_hash])`, HMAC-SHA-256 with `AUDIT_HMAC_KEY` when configured; the first row's `prev_hash` is 64 zeros. Verification walks the table in `id` order and reports the first row whose link or hash does not fit; a stored *anchor* (row count and head hash, written by each successful verification to `instance/audit_chain_anchor.json`) additionally exposes truncation at the end of the table. Migration and application share one canonical form (`app/audit_hash.py`), and a test proves the migrated hash equals the one the application would have written.

**Full-text search (FR-148).** `status_code_fts` (FTS5; title, description, remedy text, identifier) is maintained by four triggers (`trg_fts_revision_insert/update/delete`, `trg_fts_code_identifier`); ranking is `bm25` over the four columns, so a word in a short title outranks the same word buried in a long description; typo tolerance expands each word with close spellings from `status_code_fts_vocab`. It is optional derived data: without it the repository uses substring search.

**PostgreSQL readiness (NFR-014).** `python scripts/pg_readiness.py` inventories the SQLite-specific constructs in the schema, the migrations and the application code, with a porting note each, and `--check` compares the counts with `scripts/pg_baseline.json`: triggers (17 incl. FTS) and `RAISE(ABORT, …)` → PL/pgSQL; `strftime` defaults and `INTEGER PRIMARY KEY` → `TIMESTAMPTZ`/identity columns; FTS5 → `tsvector` + GIN; `BEGIN IMMEDIATE` → `SELECT … FOR UPDATE` on a counter row or `pg_advisory_xact_lock`; `GLOB`, `sqlite_master` and `PRAGMA` → regex / `information_schema`; the `sqlite3` module and the online-backup API (backups, the audit check on a backup file, the full-database export) → `pg_dump`-based equivalents. CI fails when SQLite-specific code grows, and when it shrinks until the baseline is lowered. The engine set-up is already guarded by dialect. **The application has not been run on PostgreSQL**; this is preparation, not a port.

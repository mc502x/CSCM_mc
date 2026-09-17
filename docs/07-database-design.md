# 07. Database Design Document — CSCM Tool

## 1. Overview

MVP persistence is **SQLite** (single file, per C-001 in 03-srs.md), accessed exclusively through a repository layer (18-claude-code-implementation-guide.md) so a future migration to PostgreSQL requires no changes above the repository interface. The database runs on a local, on-premises server only — see 14-deployment-architecture.md §1 — and is itself the Master Database referenced throughout this package; no external upstream system exists. The full DDL is maintained at [artifacts/schema.sql](artifacts/schema.sql) and is the executable source of truth; this document explains the design decisions behind it.

## 2. Logical Schema

The logical model mirrors 04-domain-model.md. Key v2 decisions (delta from the original Controller-Type-based design):

- **Functional System Group replaces Controller Type entirely.** `status_code.functional_system_group_id` is now the sole classification and numbering axis; there is no `controller_type` column anywhere in the schema. `lookup_functional_system_group` carries the numeric range (`range_start`/`range_end`) that drives allocation (§7a).
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
| `role` | 5-row role lookup (Administrator, Engineer, Reviewer, Chief Engineer, Viewer) |
| `lookup_engineering_domain` | Engineer specialty tags, drives Cross-Domain Sign-Off |
| `lookup_functional_system_group` | 9-row numbering band lookup |
| `lookup_functional_subgroup` | Real sub-band lookup (22 seeded subgroups), child of the above, with reserved capacity for more |
| `lookup_turbine_platform` | Multi-select platform lookup (2XM/3XM/4XM, extensible) |
| `lookup_available_group` | Soft-validated numeric availability codes, labels TBD (corrected 2026-09-17) |
| `lookup_development_access`, `lookup_sales_access`, `lookup_tcc_access`, `lookup_service_access`, `lookup_top_access`, `lookup_grid_operator_access`, `lookup_service_partner_access`, `lookup_customer_access` | Eight independent audience-access vocabularies, real observed values (corrected 2026-09-17, replaces the single `lookup_access_rights`) |
| `user`, `user_engineering_domain` | Accounts and their domain tags |
| `status_code` | Governed identity, nullable identifier, sandbox flag |
| `status_code_revision` | Versioned governed content, dual-review + Chief Engineer approval columns |
| `status_code_revision_platform` | Revision ↔ Turbine Platform join |
| `change_request` | Workflow carrier for a revision |
| `review_comment` | Role-tagged comments/decisions on a CR |
| `domain_signoff` | Cross-Domain Sign-Off records |
| `release`, `release_item` | Named, versioned export bundle and membership |
| `audit_log_entry` | Immutable action log |
| `export_job` | Export generation record, tagged CATALOGUE vs FULL_DATABASE |

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
| `trg_prevent_nonsandbox_delete` | `DELETE FROM status_code` is rejected unless `is_sandbox = 1` — the single, narrow exception to the no-hard-delete rule (05-governance-handbook.md §12) is enforced at the database layer, not only in application code |
| `trg_prevent_subgroup_overlap` | A new `lookup_functional_subgroup` row is rejected if its sub-range overlaps an existing subgroup in the same group (06-data-dictionary.md §9a.1) |
| `trg_prevent_group_overlap` (new 2026-09-17) | A new `lookup_functional_system_group` row is rejected if its range overlaps an existing group's range — lets an Administrator assign a whole new group into `10000–10999`/`14000–14999`/`15000–15999`/`16000–16999` safely (06-data-dictionary.md §9.1) |

## 5a. Hub Controller Groups & Non-Unique Prefixes (new 2026-09-17)

A real export of the Hub Controller status code library (`HC Status Code Number.xlsx`, 264 rows, range 11000–13999) revealed that Hub Controller content is **not** folded into the existing nine Main Controller groups — it gets three entirely new, numerically distinct groups (`WTUR` 11000–11999, `WROT` 12000–12999, `WPPD` 13000–13999), confirmed by the business as intentional and structurally identical to the existing model (each subdivides into real subgroups the same way, 06-data-dictionary.md §9a). The one design consequence: `WTUR` and `WROT` are each now deliberately reused across two different groups (one Main Controller, one Hub Controller), so `lookup_functional_system_group.code` **is no longer a unique key on its own** — uniqueness moved to `(code, range_start)`. Every seed-data join and every application-layer lookup of a group must resolve by `(code, range_start)` or by `id`, never by `code` alone; `artifacts/schema.sql`'s subgroup seed INSERT was rewritten with an explicit `group_range_start` disambiguator for exactly this reason.

## 6. Soft-Delete Strategy

Unchanged in principle from v1: no hard delete of governance-relevant data, **except** sandbox Status Codes, which may be permanently deleted by an Administrator (`trg_prevent_nonsandbox_delete` is the only thing that makes this possible at all — every other record is structurally undeletable). The service layer must write a `SANDBOX_DELETE` audit entry, capturing a full JSON snapshot of the record in `before_value`, in the same transaction as the delete, so the fact of creation-and-deletion survives even though the row does not (12-audit-compliance.md §2).

## 7. Versioning Strategy

Row-per-revision, atomic Release publish, and optimistic concurrency on Draft edits are unchanged in mechanism from v1 (07-database-design.md v1 §7). Two additions:

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

Unchanged in mechanism from v1 (one `audit_log_entry` per state-changing service call, same transaction). New action codes for the dual-review/approval/sandbox model are listed in 12-audit-compliance.md §2.

## 9. Migration Path Beyond SQLite

Unchanged in principle from v1 (07-database-design.md v1 §9) — the schema continues to avoid SQLite-specific typing quirks, uses portable ISO-8601 text timestamps, and keeps all four new triggers written in portable-intent SQL with documented PL/pgSQL equivalents to be produced at the time of a Phase 3 PostgreSQL migration (16-mvp-roadmap.md).

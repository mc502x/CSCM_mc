# 12. Audit & Compliance Specification — CSCM Tool

## 1. Purpose and Relationship to Other Logging

This document governs the **business audit trail** (`audit_log_entry`), the compliance record of truth for every governed change in CSCM Tool. Distinct from operational application/security logging (11-security-architecture.md §11).

## 2. Audit Events Catalogue

| Action Code | Entity | Trigger | Captures |
|---|---|---|---|
| `CREATE` | StatusCode, StatusCodeRevision, ChangeRequest | New Status Code created (05-governance-handbook.md §6) | full initial values, including Functional System Group/Subgroup and Turbine Platform(s) |
| `SANDBOX_CREATE` | StatusCode | Administrator creates a test/sandbox code | actor, isolated identifier allocated |
| `EDIT` | StatusCodeRevision | Draft field edit | before/after per changed field |
| `DOMAIN_SIGNOFF` | ChangeRequest, DomainSignoff | Second Engineer completes a required domain's fields | engineering domain, signer identity, timestamp |
| `SUBMIT_FOR_REVIEW` | ChangeRequest, StatusCode | Draft → Review; identifier allocated | actor, timestamp, allocated `status_code_identifier` |
| `REVIEWER_SIGNOFF` | ChangeRequest, StatusCodeRevision | Reviewer (Sub-PO for StCd) sign-off, approve or reject | reviewer identity, decision, comment reference |
| `ADMIN_SIGNOFF` | ChangeRequest, StatusCodeRevision | Administrator (Product Owner) sign-off, approve or reject; may confirm/override restricted fields | administrator identity, decision, comment reference, any restricted-field override |
| *(system)* Review → PendingApproval | StatusCodeRevision | Both required sign-offs now present | logged as part of whichever sign-off action was second |
| `CHIEF_ENGINEER_APPROVE` | ChangeRequest, StatusCodeRevision | PendingApproval → Approved | Chief Engineer identity, timestamp |
| `CHIEF_ENGINEER_REJECT` | ChangeRequest, StatusCodeRevision | PendingApproval → Draft | Chief Engineer identity, mandatory comment reference |
| `WITHDRAW` | ChangeRequest | Author cancels open CR | actor, timestamp |
| `COMMENT` | ReviewComment | Comment added without a decision | comment content reference |
| `RELEASE_CREATE` | Release | New Release container created | scope filter (Functional Group/Subgroup), actor |
| `RELEASE_ITEMS_SET` | Release | Candidate set confirmed/changed pre-publish | before/after item list |
| `RELEASE_PUBLISH` | Release, StatusCodeRevision (per item) | Publish action | publisher identity, effective date, item count |
| `DEPRECATE` | StatusCodeRevision | Released → Deprecated | reason, superseding code (if any), actor |
| `REINSTATE` | StatusCodeRevision | Deprecated → Released (exception path) | reason, actor |
| `ARCHIVE` | StatusCodeRevision | Deprecated → Archived | actor, retention-period check result |
| `SANDBOX_DELETE` | StatusCode | Administrator permanently deletes a sandbox code | **full pre-delete snapshot of the StatusCode and its revision(s) in `before_value`** — the one case where `entity_id` no longer resolves to a live row after this entry is written |
| `CATALOGUE_EXPORT` | ExportJob | Any catalogue export generated | requester, scope, format |
| `FULL_DATABASE_EXPORT` | ExportJob | Administrator generates a full raw database export/backup | requester (always Administrator), timestamp, file reference |
| `LOOKUP_CHANGE` | Lookup* (incl. Functional Group/Subgroup/Platform/Domain) | Controlled vocabulary value added/deactivated | before/after, actor |
| `SUBGROUP_CREATE` | FunctionalSubgroup | Administrator creates a new Functional Subgroup (new 2026-09-17) | group, code, label, sub-range, actor |
| `IMPORT_STARTED` / `IMPORT_COMPLETED` / `IMPORT_FAILED` | ImportJob | Library import lifecycle (new 2026-09-17) | requester, row_count, created_count, error_count |
| `USER_CREATE` / `USER_UPDATE` / `USER_DEACTIVATE` / `ROLE_CHANGE` / `DOMAIN_TAG_CHANGE` | User | Administration action | before/after, actor |
| `LOGIN_SUCCESS` / `LOGIN_FAILURE` / `LOGOUT` / `ACCOUNT_LOCKED` | User (session) | Authentication event | outcome, reason |
| `PASSWORD_CHANGE` / `PASSWORD_RESET` | User | Credential change | actor (self or Administrator) |

## 3. Retention Rules

| Data                                                                  | Minimum Retention                                                                                                                                                                                                    | Rationale                                                                                                   |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `audit_log_entry` rows                                                | 7 years, never purged by the application, **including every `SANDBOX_CREATE`/`SANDBOX_DELETE` pair** even after the underlying sandbox record is gone                                                                | 05-governance-handbook.md §12 makes the audit trail the only surviving evidence of a deleted sandbox record |
| Archived Status Codes and all revisions/CRs/comments/domain sign-offs | 7 years from archival, never hard-deleted                                                                                                                                                                            | Unchanged from v1                                                                                           |
| Published Releases                                                    | Indefinite, immutable                                                                                                                                                                                                | Unchanged from v1                                                                                           |
| Sandbox Status Codes themselves                                       | **No minimum retention** — this is the one entity category explicitly exempted from retention, since it is designed to be created and deleted freely by an Administrator for testing (05-governance-handbook.md §12) | The audit trail, not the record, is what is retained                                                        |
| Application/security logs                                             | 1 year                                                                                                                                                                                                               | Unchanged from v1                                                                                           |

No feature provides deletion of `audit_log_entry` rows, non-sandbox Status Codes, or published Releases.

## 4. Traceability Requirements

- **AUD-001** For any non-sandbox Status Code, the system shall produce a complete, chronologically ordered trace from `CREATE` through every `EDIT`, `DOMAIN_SIGNOFF`, `SUBMIT_FOR_REVIEW`, `REVIEWER_SIGNOFF`, `ADMIN_SIGNOFF`, `CHIEF_ENGINEER_APPROVE`/`REJECT`, `RELEASE_PUBLISH`, and any `DEPRECATE`/`ARCHIVE` event, with actor and timestamp at each step.
- **AUD-002** For any Release, the system shall list every included revision and, transitively, its full change history.
- **AUD-003** For any User, the system shall list every action they performed as `actor_id`.
- **AUD-004** For any deleted sandbox Status Code, the system shall be able to retrieve the `SANDBOX_CREATE` and `SANDBOX_DELETE` audit pair, including the full pre-delete snapshot, even though the live record no longer exists.

## 5. Change History Requirements

Unchanged in mechanism from v1: field-level `EDIT` entries batched per explicit Save, full historical content independently queryable via the row-per-revision model, audit log complements rather than replaces it.

## 6. Electronic Approval Rules

- `REVIEWER_SIGNOFF`, `ADMIN_SIGNOFF`, and `CHIEF_ENGINEER_APPROVE`/`REJECT` each constitute a distinct electronic approval record, bound to the deciding user's authenticated session, and each independently enforces segregation of duties (05-governance-handbook.md §7–§8, 11-security-architecture.md §3 SEC-011).
- The pairing of `audit_log_entry` and `review_comment` together constitute durable evidence of each decision; both are retained under the same 7-year minimum.
- No approval action can be back-dated or edited after the fact; all sign-off/approval timestamps are system-generated at the moment of the transaction.
- The automatic `Review → PendingApproval` transition (triggered by the second sign-off, 07-database-design.md §7b) is itself traceable: the audit entry for whichever sign-off action was second also records the resulting state change, so there is no silent/unaudited system-triggered transition anywhere in the lifecycle.

## 7. Compliance Controls Summary

| Control | Implementation |
|---|---|
| Segregation of duties (3 decision points) | 05-governance-handbook.md §7–§8, SEC-011, DB `CHECK` constraints (07-database-design.md §4) |
| Immutable audit trail | No delete/update endpoint exists; survives even sandbox record deletion (§3) |
| Immutable released data | `trg_prevent_edit_locked_revision`, atomic publish transaction |
| Sandbox isolation | `trg_prevent_sandbox_release` blocks any sandbox revision from ever reaching a Release; `is_sandbox` excluded from default search/export (09-api-specification.md §6) |
| Complete traceability | AUD-001–AUD-004 |
| Defined retention, with one explicit, narrow exception | §3 |
| Access control over audit data | Administrator (full), Reviewer/Chief Engineer (scoped); no role can write to it directly |
| Full-database export control | Administrator-only (SEC-015), itself audited (`FULL_DATABASE_EXPORT`) |

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
| `SUBMIT_FOR_REVIEW` | ChangeRequest, StatusCode | Draft → Review; identifier allocated | actor, timestamp, allocated `status_code_identifier`; *(v4.2)* `identifier_source` = `reserved` when the number came from an imported program (BR-023) |
| `REVIEWER_SIGNOFF` | ChangeRequest, StatusCodeRevision | Reviewer (Sub-PO for StCd) sign-off, approve or reject | reviewer identity, decision, comment id and text |
| `ADMIN_SIGNOFF` | ChangeRequest, StatusCodeRevision | Administrator (Product Owner) sign-off, approve or reject; may confirm/override restricted fields | administrator identity, decision, comment reference, any restricted-field override |
| *(system)* Review → PendingApproval | StatusCodeRevision | Both required sign-offs now present | logged as part of whichever sign-off action was second |
| `CHIEF_ENGINEER_APPROVE` | ChangeRequest, StatusCodeRevision | PendingApproval → Approved | Chief Engineer identity, timestamp |
| `CHIEF_ENGINEER_REJECT` | ChangeRequest, StatusCodeRevision | PendingApproval → Draft | Chief Engineer identity, mandatory comment reference |
| `DOMAIN_SIGNOFF_REQUEST` | ChangeRequest | Originating Engineer requests a domain sign-off (FR-028) | domain, optional target user |
| `REVIEWER_ASSIGN` | ChangeRequest | Administrator assigns/reassigns/unassigns the Reviewer (FR-039) | before/after assigned reviewer |
| `IDENTIFIER_OVERRIDE` | StatusCode | Administrator submits with a manual identifier (FR-021a) | identifier and mandatory documented reason |
| `WITHDRAW` | ChangeRequest | Author cancels open CR | actor, timestamp, and a snapshot in `before_value` of the discussion that would otherwise be deleted with the CR (every comment/decision with author and time, domain sign-offs, title, identifier) |
| `COMMENT` | ReviewComment | Comment added without a decision | comment id and full text |
| `RELEASE_CREATE` | Release | New Release container created | scope filter (Functional Group/Subgroup), actor |
| `RELEASE_ITEMS_SET` | Release | Candidate set confirmed/changed pre-publish | before/after item list |
| `RELEASE_DELETE` | Release | Administrator deletes an unpublished Release (BR-008) | before: name, version, candidate revision ids |
| `RELEASE_PUBLISH` | Release, StatusCodeRevision (per item) | Publish action | publisher identity, effective date, item count |
| `DEPRECATE` | StatusCodeRevision | Released → Deprecated | reason, superseding code (if any), actor |
| `REINSTATE` | StatusCodeRevision | Deprecated → Released (exception path) | reason, actor |
| `ARCHIVE` | StatusCodeRevision | Deprecated → Archived | actor, retention-period check result |
| `SANDBOX_DELETE` | StatusCode | Administrator permanently deletes a sandbox code | **full pre-delete snapshot of the StatusCode and its revision(s) in `before_value`** — the one case where `entity_id` no longer resolves to a live row after this entry is written |
| `CATALOGUE_EXPORT` | ExportJob | Any catalogue export generated | requester, scope, format |
| `FULL_DATABASE_EXPORT` | ExportJob | Administrator generates a full raw database export/backup | requester (always Administrator), timestamp, file reference |
| `LOOKUP_CHANGE` | Lookup* (incl. Functional Group/Subgroup/Platform/Domain) | Controlled vocabulary value added/deactivated | before/after, actor |
| `SUBGROUP_CREATE` | FunctionalSubgroup | Administrator creates a new Functional Subgroup (new 2026-09-17) | group, code, label, sub-range, actor |
| `IMPORT_STARTED` / `IMPORT_COMPLETED` / `IMPORT_FAILED` | ImportJob | Library import lifecycle (new 2026-09-17) | requester, row_count, created_count, error_count; *(v4.2)* for an import from programs also `source_format` `ST`, the file names and the `change_set_id` |
| `USER_CREATE` / `USER_UPDATE` / `USER_DEACTIVATE` / `ROLE_CHANGE` / `DOMAIN_TAG_CHANGE` | User | Administration action | before/after, actor |
| `USER_DELETE` *(v4.6)* | User | An account is deleted: removed when nothing points at it, erased when it has history (BR-025, AUD-076) | `before_value`: username, e-mail, full name, role, domain tags; `after_value`: `mode` (`removed` or `erased`), `references`; actor |
| `WITHDRAWN_CODE_DELETE` *(v4.9)* | StatusCode | An Administrator deletes a code whose change request was withdrawn; the row stays and gives up its numbers (BR-026, AUD-076) | `before_value`: identifier, reserved identifier, legacy number, PrgIdx_GUi, group, subgroup, withdrawal time; actor |
| `LOGIN_SUCCESS` / `LOGIN_FAILURE` / `LOGOUT` / `ACCOUNT_LOCKED` | User (session) | Authentication event; *(v4.7)* a Windows sign-in (FR-163) writes the same codes, with `method` = `windows`, the identity the gateway supplied and whether it came from the gateway or the developer simulation | outcome, reason |
| `LANGUAGE_REVIEWER_ASSIGN` / `LANGUAGE_REVIEWER_REMOVE` *(v4.7)* | LanguageReviewer | An Administrator or StCd Owner assigns a native speaker to a language or takes the assignment away (FR-164) | language, reviewer, actor |
| `TRANSLATION_REVIEW_COMPLETE` *(v4.7)* | TranslationReview | A reviewer completes the review of a language | language, fingerprint at start and at completion, strings, number of OK / CHANGE / UNCLEAR, actor |
| `TRANSLATION_PROPOSAL_DECIDE` *(v4.7)* | TranslationReviewItem | An Administrator or StCd Owner accepts, rejects or notes a proposal; an accepted one creates the override | `before`: language, string id, verdict; `after`: language, English text, `decision`, the text shown (accept); actor |
| `TRANSLATION_OVERRIDE_REMOVE` *(v4.7)* | TranslationOverride | An override is removed and the shipped text shows again | `before_value`: language, English text, removed text; actor |
| `TERM_CREATE` / `TERM_UPDATE` *(v4.9)* | TerminologyTerm | A manager adds a term or changes its English text, category, definition, *never translated* flag or state (FR-166) | `after`: code, English text, category; on an update also `before` and `approvals_reopened`; actor |
| `TERM_TRANSLATE` / `TERM_APPROVE` / `TERM_REJECT` *(v4.9)* | TerminologyTranslation | A translation of a term is proposed, approved by a second person or sent back with a note (FR-166, BR-018) | term code, language, text (the note on a send-back); `before` on a change; actor |
| `PASSWORD_CHANGE` / `PASSWORD_RESET` | User | Credential change | actor (self or Administrator) |
| `STEP_UP_SUCCESS` / `STEP_UP_FAILURE` *(v4)* | User | Password confirmation for a sensitive action (SEC-026) | actor, `purpose` (e.g. `RELEASE_PUBLISH`) — never the password |
| `PLANNED_DATES_SET` *(v4)* | StatusCodeRevision | Administrator stamps planned effective / deprecation dates (FR-109) | before/after dates |
| `RELEASE_TARGETS_SET` *(v4)* | Release | Target software versions set before publish (FR-106) | before/after version codes |
| `PACKAGE_REQUEST` / `PACKAGE_EXPORT` *(v4.10)* | ExportJob | A package of all languages and access levels was requested and finished (FR-174) | requester, release, scope, file count, SHA-256 |
| `OFFLINE_BUNDLE_EXPORT` / `RELEASE_NOTES_EXPORT` *(v4)* | ExportJob | Offline lookup bundle or release notes generated (FR-105, FR-108) | requester, release, SHA-256, options |
| `EXPORT_PROFILE_CREATE` / `EXPORT_PROFILE_UPDATE` *(v4)* | ExportProfile | Administrator changes an export profile (FR-100) | before/after columns, audience, language |
| `TRANSLATION_SAVE` / `TRANSLATION_APPROVE` / `TRANSLATION_CARRY_OVER` *(v4)* | StatusCodeRevision | Translation workflow (FR-110) | language, status, translator / approver |
| `DELEGATION_CREATE` / `DELEGATION_REVOKE` *(v4)* | Delegation | Out-of-office cover (FR-125) | delegator, delegate, role, dates |
| `CHANGE_SET_CREATE` / `CHANGE_SET_ADD_CR` / `CHANGE_SET_REMOVE_CR` / `CHANGE_SET_CLOSE` *(v4)* | ChangeSet | Change-set management (FR-124) | set, request, actor |
| `FIELD_COMMENT` / `FIELD_COMMENT_RESOLVE` *(v4)* | ChangeRequest | Field-level comment and its resolution (FR-127) | field, text, author / resolver |
| `CHECKLIST_ITEM_CREATE` / `CHECKLIST_ITEM_UPDATE` *(v4)* | ReviewChecklistItem | Administrator edits the review checklist (FR-128) | before/after |
| `ATTACHMENT_ADD` / `ATTACHMENT_DELETE` *(v4)* | ChangeRequest | Evidence attached or removed (FR-130) | file name, size, SHA-256, actor |
| `SETTINGS_CHANGE` *(v4)* | Settings | Administrator changes SLA, auto-assignment or capacity settings | before/after per key |
| `OCCURRENCE_IMPORT` *(v4)* | OccurrenceImport | Fleet-feedback counts imported (FR-143) | source, period, matched codes, unmatched rows |
| `API_TOKEN_CREATE` / `API_TOKEN_REVOKE` *(v4)* | ApiToken | Token issued or revoked (FR-144) | name, scopes, expiry — never the secret |
| `WEBHOOK_CREATE` / `WEBHOOK_UPDATE` *(v4)* | Webhook | Webhook registered, paused or resumed (FR-146) | name, URL, events, active flag |
| `HUB_MC_DRAFT_CREATE` / `HUB_BULK_DEPRECATION` *(v4)* | StatusCode, LookupFunctionalSystemGroup | Hub-to-Main consolidation (FR-147) | replaced Hub code; counts of requests created and skipped |
| `AUDIT_ARCHIVE` *(v4)* | AuditArchive | Old audit entries archived (AUD-073) | file name, count, first and last entry id, SHA-256, cutoff |

**Notes on the catalogue.** `REVIEWER_SIGNOFF`, `ADMIN_SIGNOFF` and the Chief Engineer codes are written per decision; `ACCOUNT_LOCKED` is written instead of `LOGIN_FAILURE` on the attempt that locks an account; `USER_DEACTIVATE` instead of `USER_UPDATE` when an account is switched off. `CATALOGUE_EXPORT` also covers profile / audience / language / bundle exports; its `after_value` records those options and the file's SHA-256. A delegate's decision entries carry `on_behalf_of` (BR-017). `tests/system/test_docs_consistency.py` fails if the application can write an action code that this table does not list.

## 3. Retention Rules

| Data                                                                  | Minimum Retention                                                                                                                                                                                                    | Rationale                                                                                                   |
| --------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `audit_log_entry` rows                                                | 7 years, never purged by the application, **including every `SANDBOX_CREATE`/`SANDBOX_DELETE` pair** even after the underlying sandbox record is gone                                                                | 05-governance-handbook.md §12 makes the audit trail the only surviving evidence of a deleted sandbox record |
| Archived Status Codes and all revisions/CRs/comments/domain sign-offs | 7 years from archival, never hard-deleted                                                                                                                                                                            | Standing rule                                                                                               |
| Published Releases                                                    | Indefinite, immutable                                                                                                                                                                                                | Standing rule                                                                                               |
| Sandbox Status Codes themselves                                       | **No minimum retention** — this is the one entity category explicitly exempted from retention, since it is designed to be created and deleted freely by an Administrator for testing (05-governance-handbook.md §12) | The audit trail, not the record, is what is retained                                                        |
| Application/security logs                                             | 1 year                                                                                                                                                                                                               | Standing rule                                                                                               |
| Audit archive files *(v4)* (`audit_archive_*.jsonl.gz` + `.sha256`)  | Same as the audit rows they copy: 7 years; the rows themselves also stay in the database                                                                                                                              | Archiving writes a copy and an `AUDIT_ARCHIVE` entry; nothing is deleted (AUD-073, BR-020)                  |
| Backups *(v4)*                                                        | The shipped schedule keeps 35 generations of verified nightly backups (14-deployment-architecture.md §6)                                                                                                              | Recoverability (NFR-012); a backup carries the same sensitivity as the database                              |

No feature provides deletion of `audit_log_entry` rows, non-sandbox Status Codes, or published Releases.

## 4. Traceability Requirements

- **AUD-001** For any non-sandbox Status Code, the system shall produce a complete, chronologically ordered trace from `CREATE` through every `EDIT`, `DOMAIN_SIGNOFF`, `SUBMIT_FOR_REVIEW`, `REVIEWER_SIGNOFF`, `ADMIN_SIGNOFF`, `CHIEF_ENGINEER_APPROVE`/`REJECT`, `RELEASE_PUBLISH`, and any `DEPRECATE`/`ARCHIVE` event, with actor and timestamp at each step.
- **AUD-002** For any Release, the system shall list every included revision and, transitively, its full change history.
- **AUD-003** For any User, the system shall list every action they performed as `actor_id`.
- **AUD-004** For any deleted sandbox Status Code, the system shall be able to retrieve the `SANDBOX_CREATE` and `SANDBOX_DELETE` audit pair, including the full pre-delete snapshot, even though the live record no longer exists.

- **AUD-072** (v4) No application path updates or deletes an `audit_log_entry`: there is no endpoint for it, and the triggers `trg_audit_no_update` / `trg_audit_no_delete` abort any attempt through the application connection (FR-072).
- **AUD-073** (v4) Entries older than the retention period (default 7 years) are archived — never deleted — by `flask audit-archive`: a gzip JSON-lines file with a `.sha256` file, plus an `AUDIT_ARCHIVE` entry naming the file, count, id range and hash. The next run continues after the last archived entry, so running it twice is harmless.
- **AUD-074** (v4) Each entry stores `prev_hash` and `entry_hash` (SHA-256, or HMAC-SHA-256 when `AUDIT_HMAC_KEY` is set) over its own fields and its predecessor's hash, written inside the same write transaction as the entry. Rows that existed before v4 were chained by the migration; a hash-less row after hashed rows is itself a failure.
- **AUD-075** (v4) The chain is verified on demand (`flask audit-verify`, Administrator UI and `POST /operations/audit-verify`) and weekly by the scheduler; a failure names the first bad entry and the reason (broken link, changed content, rows removed since the last verification — detected through the stored anchor), exits non-zero and shows as `broken` in the readiness probe; every backup is checked for chain integrity before it counts as verified (FR-150, FR-151).
- **AUD-076** (v4.6, changed in v4.9) Deleting a user writes `USER_DELETE` with the account's username, e-mail, name, role and domain tags before the account is removed or erased, the mode and the actor. The audit log itself is never modified: an account with history is erased in place (BR-025), so no earlier audit entry is left without its actor, and the hash chain still verifies. Deleting a withdrawn code writes `WITHDRAWN_CODE_DELETE` with what the code held (BR-026). The `WITHDRAW` snapshot of a change request also records what the code gave back to the catalogue (`released_to_the_catalogue`: reserved identifier, legacy number, PrgIdx_GUi, BR-026).
- **AUD-077** (v4.7) Reviewing translations is audited: assigning or removing a reviewer, completing a review, deciding on a proposal and removing an override each write one entry (`LANGUAGE_REVIEWER_ASSIGN`, `LANGUAGE_REVIEWER_REMOVE`, `TRANSLATION_REVIEW_COMPLETE`, `TRANSLATION_PROPOSAL_DECIDE`, `TRANSLATION_OVERRIDE_REMOVE`); the text of a decided proposal stays in its row and the text of a removed override is kept in the entry, so what the application showed in a language can always be reconstructed. The terminology (FR-166) is audited the same way (v4.9): adding or changing a term writes `TERM_CREATE` or `TERM_UPDATE`; proposing, approving and sending back a translation write `TERM_TRANSLATE`, `TERM_APPROVE` and `TERM_REJECT` with the term, the language and the text.

## 5. Change History Requirements

Field-level `EDIT` entries batched per explicit Save (v4: each save also increments `row_version`, so a lost update can be told from the entries), full historical content independently queryable via the row-per-revision model, audit log complements rather than replaces it.

## 6. Electronic Approval Rules

- `REVIEWER_SIGNOFF`, `ADMIN_SIGNOFF`, and `CHIEF_ENGINEER_APPROVE`/`REJECT` each constitute a distinct electronic approval record, bound to the deciding user's authenticated session, and each independently enforces segregation of duties (05-governance-handbook.md §7–§8, 11-security-architecture.md §3 SEC-011).
- The pairing of `audit_log_entry` and `review_comment` together constitute durable evidence of each decision; both are retained under the same 7-year minimum.
- *(v4)* Each of those approvals is preceded by a password confirmation (`STEP_UP_SUCCESS` with the purpose) by the same actor in the same request, so an unattended session cannot approve (SEC-026); a delegate's approval is recorded with `on_behalf_of`, and every approval remains bound to the delegate's own identity.
- No approval action can be back-dated or edited after the fact; all sign-off/approval timestamps are system-generated at the moment of the transaction.
- The automatic `Review → PendingApproval` transition (triggered by the second sign-off, 07-database-design.md §7b) is itself traceable: the audit entry for whichever sign-off action was second also records the resulting state change, so there is no silent/unaudited system-triggered transition anywhere in the lifecycle.

## 7. Compliance Controls Summary

| Control | Implementation |
|---|---|
| Segregation of duties (3 decision points) | 05-governance-handbook.md §7–§8, SEC-011, DB `CHECK` constraints (07-database-design.md §4) |
| Immutable audit trail | No delete/update endpoint exists; survives even sandbox record deletion (§3); append-only triggers (AUD-072) |
| Tamper-evident audit trail *(v4)* | Hash chain, anchor, weekly verification, archive that never deletes (AUD-073 … AUD-075) |
| Deliberate approvals *(v4)* | Step-up password, delegation audit with `on_behalf_of`, change-set decisions one audit entry per request |
| Immutable released data | `trg_prevent_edit_locked_revision`, atomic publish transaction |
| Sandbox isolation | `trg_prevent_sandbox_release` blocks any sandbox revision from ever reaching a Release; `is_sandbox` excluded from default search/export (09-api-specification.md §6) |
| Complete traceability | AUD-001–AUD-004, AUD-072–AUD-075 |
| Defined retention, with one explicit, narrow exception | §3 |
| Access control over audit data | Administrator (full), Reviewer/Chief Engineer (scoped); no role can write to it directly |
| Full-database export control | Administrator-only (SEC-015), itself audited (`FULL_DATABASE_EXPORT`) |

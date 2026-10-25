# 09. API Specification — CSCM Tool

Full machine-readable contract: [artifacts/openapi.yaml](artifacts/openapi.yaml) (OpenAPI 3.0.3, **v4.0.0**, 161 operations — field set corrected 2026-09-17 against a real export of the live status code library, extended 2026-10-23 by the improvement pack). A test (`test_openapi_conformance`) fails when the code and this contract differ, and the endpoint table in §7 is generated from the code (`scripts/gen_api_summary.py`). This document explains the conventions that apply across every endpoint.

## 1. Versioning

All endpoints are namespaced under `/api/v1`. The v2 documentation-package revision (this update) changes the *contract*, not the version prefix, since the application has not yet shipped — `/api/v1` remains correct for the first production release, which will already reflect this model. A genuinely breaking change post-launch requires `/api/v2`.

## 2. Authentication

MVP: session-cookie authentication (`cscm_session`, HttpOnly, Secure, SameSite=Strict), served entirely over the internal on-premises network. Future non-browser API consumers (documentation-generation tools, SCADA, software repositories — 08-system-architecture.md §6) will use a scoped, Administrator-issued API token (`Authorization: Bearer <token>`), still internal-network-only, never internet-exposed and never involving a cloud identity provider. Every endpoint requires authentication except `POST /auth/login`.

## 3. Authorization

Role-based across six roles (Administrator, StCd Owner, Engineer, Reviewer, Chief Engineer, Viewer), enforced identically whether the request originates from the server-rendered UI or a direct API call. The canonical permission matrix is 11-security-architecture.md §3. Segregation-of-duties is enforced server-side on all three decision endpoints:
- `POST /change-requests/{id}/reviewer-signoff` — 403 if `actor.id == change_request.requested_by`.
- `POST /change-requests/{id}/admin-signoff` — 403 if `actor.id == change_request.requested_by`.
- `POST /change-requests/{id}/chief-engineer-decide` — 403 if `actor.id` matches the requester, the Reviewer sign-off, or the Administrator sign-off on this CR.

`DELETE /status-codes/{id}` (sandbox deletion) additionally requires `status_code.is_sandbox == true`; the same endpoint against a non-sandbox record returns 403 regardless of role.

`POST /exports/full-database` (a `GET` before v4) requires the Administrator role and the Administrator's `current_password`; no other role can reach it (04-domain-model.md §2.17). Since v4 a *delegate* is admitted to the **decision** routes (`reviewer-signoff`, `admin-signoff`, `chief-engineer-decide`) when an active delegation covers the role (FR-125); no other route honours delegation.

## 4. Request/Response Conventions

JSON bodies, ISO-8601 UTC timestamps, lookup-backed fields returned/accepted by `code` string (`functional_system_group: "WCNV"`, `turbine_platforms: ["2XM","3XM"]`, etc.) rather than internal surrogate IDs. `status_code_identifier` is `null` in every response until the revision reaches `REVIEW` or later.

## 5. Error Handling

| HTTP Status | Meaning | Body |
|---|---|---|
| 400 | Malformed request | `Error` |
| 401 | Not authenticated | `Error` |
| 403 | Not authorized (role, segregation-of-duties, sandbox-only-delete, domain-signoff-wrong-domain); `error: step_up_required` / `step_up_failed` when a sensitive action lacks or mistypes the actor's password (FR-126); `account_locked` | `Error` |
| 404 | Resource does not exist | `Error` |
| 409 | Conflict — duplicate identifier (should not occur given atomic allocation, but guarded), optimistic-concurrency mismatch (`error: conflict`, a stale `expected_row_version` / `expected_updated_at`, FR-090), invalid state transition, open-CR-already-exists (BR-003), sandbox code added to a Release | `Error` |
| 422 | Semantically invalid input, OR required Cross-Domain Sign-Offs incomplete at Submit-for-Review | `ValidationErrorBody` |
| 429 | Rate limit exceeded (login attempts; shared by all worker processes, NFR-009) | `Error` |
| 503 | Readiness probe: database unreachable, schema not at the expected head, or audit chain broken (`GET /health/ready` only) | `Readiness` |
| 202 | *Success, not an error:* an import is accepted — finished for small files, processed in the background above the row threshold (FR-048n) | `ImportJob` |
| 304 | *Success, not an error:* `GET /changes` with a matching `If-None-Match` | — |
| 500 | Unexpected server error | `Error` |

## 6. Pagination, Filtering, Sorting

`page`/`page_size` envelope (default 50, maximum 200), `sort` with a `-` prefix for descending. Filters on `GET /status-codes`: `functional_system_group`, `functional_subgroup`, `turbine_platform`, `is_sandbox` (defaults to `false`, so sandbox records never appear in default search results — matching their exclusion from catalogues). Full-text search (`q`) covers `status_code_identifier`, `title`, `description`.

## 6a. Mandatory Fields on Creation (corrected 2026-09-17)

`POST /status-codes` requires both `functional_system_group` **and** `functional_subgroup` — the prior contract treated the subgroup as optional; real production data confirmed every status code carries one, so `StatusCodeCreate` now lists it in `required` (`artifacts/openapi.yaml`). A request omitting it returns 422, the same as any other missing mandatory field.

## 6b. Library Import

`POST /imports` accepts a CSV or XLSX file (`multipart/form-data`; since v4 also `mode=CREATE|UPDATE`, `dry_run=true` — a report that creates nothing, not even a job — and `async=true`). The answer is **202 Accepted** with the `ImportJob`: files up to the row threshold (default 300) are already finished when the response is sent (`status` `COMPLETE`), larger files or `async=true` are processed in a background worker and the job is polled; a dry run answers 200 with the per-row report. `GET /imports/template` returns the template (CSV or XLSX); `GET`/`POST /imports/reconciliation` return the migration progress (FR-048i … FR-048n). `GET /imports/{id}` polls status; `created_count`/`error_count` report progress, and `GET /imports/{id}/errors` downloads a per-row error report once the job completes. Every successfully validated row produces a normal Draft `ChangeRequest` (`cr_type=IMPORT`) that must still pass Cross-Domain Sign-Off, both Review sign-offs, and Chief Engineer approval — import never creates an Approved or Released record directly (05-governance-handbook.md §6b).

## 6c. Subgroup & Group Administration

`POST /lookups/functional-subgroups` (Administrator only) creates a new Functional Subgroup within an existing Functional System Group. The service layer validates the proposed `sub_range_start`/`sub_range_end` against every existing subgroup in that group and returns 409 with the conflicting subgroup's name on overlap; a non-overlapping request succeeds even without hundreds-digit alignment (06-data-dictionary.md §9a.1).

`POST /lookups/functional-system-groups` (Administrator only, new 2026-09-17) creates a brand-new Functional System Group into any currently free numeric range (`10000–10999`, `14000–14999`, `15000–15999`, `16000–16999`), validated for non-overlap against every existing group the same way (06-data-dictionary.md §9.1). No schema change is ever required for either operation.

## 6d. Status Code Import from Generated Programs (v4.2)

Two steps, so nothing is created before a person has looked (FR-048o … FR-048w). `POST /imports/st/preview` takes `multipart/form-data` with one or more `files` (`.st`, or one `.zip`) and the options `controller` (`auto`|`MC`|`HC`), `hc_proposal` (`1`|`2`), `default_category`, `alarm_type_categories` (JSON, alarm type → category) and `platforms`; it answers **200** with a `token`, a summary and one item per program (`key`, `identifier`, `legacy_number`, `controller`, `alarm_type`, `category`, `group`, `subgroup`, `state` = `ready`|`exists`|`blocked`, `issues`, `warnings`) and creates nothing but the caller's staged copy. `POST /imports/st` with `{token, selected?, categories?, change_set_name?, async?}` (`categories` sets the status category per item key, FR-181) creates the Drafts for the chosen items (default: all that are ready) and answers **202** with the `ImportJob` (`source_format` `ST`, `change_set_id`); an unknown, expired or foreign token is 404 or 403, nothing selected or a program that is no longer ready is 422. `GET /status-codes/{id}/import-source` returns the provenance of an imported code. `GET /legacy-mapping` (filters `controller`, `q`, `state`) and `GET /legacy-mapping/export` (`format=csv|xlsx`) give the legacy → new mapping for the internal roles; there is no reverse lookup (FR-048u).

## 7. Endpoint Summary

Generated from `docs/artifacts/openapi.yaml` and the access declared on each route (`python scripts/gen_api_summary.py --write`; a test fails if this table is out of date). "Who may call it" is the route-level gate; row-level rules — own change request, segregation of duties, sandbox-only delete, Released-only visibility for tokens and Viewers — are applied by the service layer (§3). Audit-relevant detail of each operation is in the OpenAPI description.

<!-- api-summary:start -->
| Method | Path | Purpose | Who may call it |
|---|---|---|---|
| POST | `/auth/windows` | Sign in with the Windows identity the authenticating gateway supplies (v4.7, FR-163): the header WINDOWS_AUTH_HEADER (default X-Remote-Us... | Public |
| POST | `/auth/login` | Authenticate and establish a session | Public |
| POST | `/auth/logout` | Invalidate current session | Any signed-in user |
| GET | `/auth/csrf-token` | Fetch the CSRF token to send as X-CSRFToken on every state-changing request | Public |
| GET | `/health` | Liveness probe (no authentication) | Public |
| GET | `/auth/me` | Current authenticated user | Any signed-in user |
| GET | `/users` | List users (Administrator only) | Administrator, StCd Owner |
| POST | `/users` | Create a user, including role and Engineering Domain tags (Administrator only) | Administrator |
| GET | `/users/{userId}` | Get a user | Administrator, StCd Owner |
| PATCH | `/users/{userId}` | Update a user, role, or Engineering Domain tags (Administrator only) | Administrator, StCd Owner |
| POST | `/users/me/change-password` | Change own password (policy enforced; other sessions are invalidated; FR-013) | Any signed-in user |
| POST | `/users/{userId}/force-reset-password` | Force a password reset for a user (Administrator only; invalidates their sessions; FR-014) | Administrator |
| GET | `/status-codes` | List/search status codes (current revision per code) | Any signed-in user; API token `catalogue:read` |
| POST | `/status-codes` | Create a new Status Code (Draft; no identifier assigned yet — functional_subgroup is mandatory, never optional) or a Sandbox Status Code... | Administrator, Engineer |
| GET | `/status-codes/{statusCodeId}` | Get current revision of a status code | Any signed-in user; API token `catalogue:read` |
| DELETE | `/status-codes/{statusCodeId}` | Permanently delete a Sandbox Status Code (Administrator only; blocked at the DB layer for any non-sandbox record) | Administrator |
| POST | `/status-codes/{statusCodeId}/deprecation-requests` | Open a Deprecation change request against a Released code (Administrator or Engineer) | Administrator, Engineer |
| POST | `/status-codes/{statusCodeId}/archive` | Archive a Deprecated code once the minimum retention period has elapsed (Administrator only; FR-051, BR-006) | Administrator |
| POST | `/status-codes/{statusCodeId}/reinstate` | Reinstate a Deprecated code to Released (Administrator only; exception path, reason required) | Administrator |
| GET | `/status-codes/{statusCodeId}/revisions` | Full revision history for a status code | Any signed-in user |
| POST | `/status-codes/{statusCodeId}/revisions` | Open a new Draft revision (change request) against an existing code | Administrator, Engineer |
| GET | `/status-codes/{statusCodeId}/revisions/{revisionA}/diff/{revisionB}` | Field-level diff between two revisions | Any signed-in user |
| PATCH | `/revisions/{revisionId}` | Edit a Draft revision's fields (Engineer, own CR only) | Administrator, Engineer |
| GET | `/change-requests` | List change requests (review/approval queues) | Working roles (not Viewer) and StCd Owner (read only) |
| GET | `/change-requests/{crId}` | Get change request detail (incl. comments and domain sign-offs) | Working roles (not Viewer) and StCd Owner (read only) |
| POST | `/change-requests/{crId}/submit` | Submit Draft for Review (Draft -> Review) | Administrator, Engineer |
| POST | `/change-requests/{crId}/reviewer-signoff` | Reviewer (Sub-PO for StCd) sign-off | Reviewer |
| POST | `/change-requests/{crId}/admin-signoff` | Administrator (Product Owner) sign-off | Administrator |
| POST | `/change-requests/{crId}/chief-engineer-decide` | Chief Engineer final Approval decision (PendingApproval -> Approved / Draft) | Chief Engineer |
| POST | `/change-requests/{crId}/withdraw` | Withdraw own Draft/Review/PendingApproval CR | Administrator, Engineer |
| POST | `/change-requests/{crId}/comments` | Add a comment without a decision, at any stage (Reviewer, Administrator, Chief Engineer; FR-038) | Administrator, Reviewer, Chief Engineer |
| PUT | `/change-requests/{crId}/reviewer-assignment` | Assign, reassign or (reviewer_id null) unassign the Reviewer (Administrator only; FR-039) | Administrator |
| POST | `/change-requests/{crId}/domain-signoff-requests` | The originating Engineer requests a pending domain's sign-off, optionally from one named Engineer holding that domain (FR-028) | Administrator, Engineer |
| GET | `/domain-signoff-requests` | Open domain sign-off requests awaiting the current Engineer (addressed to them, or open to their domains) | Engineer |
| GET | `/change-requests/{crId}/domain-signoffs` | List required and completed Cross-Domain Sign-Offs for a CR | Working roles (not Viewer) and StCd Owner (read only) |
| POST | `/change-requests/{crId}/domain-signoffs` | Record a Cross-Domain Sign-Off (actor must hold the named Engineering Domain) | Engineer |
| GET | `/users/{userId}/usage` | What the account has done in the tool (the rows of every other table that point at it) and whether a delete removes the account or erases... | Administrator, StCd Owner |
| POST | `/users/{userId}/delete` | Delete an account (Administrator, with the Administrator's own password) | Administrator |
| POST | `/change-requests/withdraw` | Withdraw several of your own open change requests in one call (FR-159) | Administrator, Engineer |
| GET | `/imports` | List import jobs | Administrator, Engineer |
| POST | `/imports` | Upload a CSV or XLSX status code library file | Administrator, Engineer |
| GET | `/imports/{importJobId}` | Get import job status, including created/error counts | Administrator, Engineer |
| GET | `/imports/{importJobId}/errors` | Download the per-row error report (row, column, value, problem, how to fix) for a completed import job (CSV, or XLSX with format=xlsx) | Administrator, Engineer |
| GET | `/releases` | List releases | Any signed-in user; API token `catalogue:read` |
| POST | `/releases` | Create a Release (Administrator only) | Administrator |
| GET | `/releases/{releaseId}` | Get release detail (incl. items) | Any signed-in user; API token `catalogue:read` |
| DELETE | `/releases/{releaseId}` | Delete an unpublished Release (Administrator only; BR-008) | Administrator |
| GET | `/releases/{releaseId}/candidates` | List Approved (non-sandbox) revisions matching the release's scope filter | Administrator |
| PUT | `/releases/{releaseId}/items` | Set the included revision set (pre-publish only; sandbox revisions are rejected) | Administrator |
| POST | `/releases/{releaseId}/publish` | Publish the release (atomic; Administrator only) | Administrator |
| GET | `/releases/{releaseId}/export` | Export a release catalogue as a flat table (role-scoped, per 11-security-architecture.md §3) | Any signed-in user; API token `catalogue:read` |
| GET | `/exports/released` | Export the current set of all Released (non-sandbox) status codes as a flat table (any authenticated role; FR-045) | Any signed-in user; API token `catalogue:read` |
| GET | `/exports/working-set` | Ad-hoc filtered working set in any lifecycle state (never sandbox), for the StCd Owner and the Administrator only (FR-046, FR-175) | Administrator, StCd Owner |
| POST | `/exports/full-database` | Export a full raw database backup (Administrator only) | Administrator |
| GET | `/lookups/{vocabulary}` | List active values of a controlled vocabulary | Any signed-in user |
| POST | `/lookups/{vocabulary}` | Add a value to a simple controlled vocabulary (Administrator only; functional groups/subgroups have their own endpoints) | Administrator |
| PATCH | `/lookups/{vocabulary}/{valueId}` | Relabel, describe (inline-help text), (de)activate or reorder a vocabulary value (Administrator only; values are never deleted) | Administrator |
| POST | `/lookups/functional-system-groups` | Create a brand-new Functional System Group (Administrator only), into any currently free range (10000-10999, 14000-14999, 15000-15999, 16... | Administrator |
| POST | `/lookups/functional-subgroups` | Create a new Functional Subgroup (Administrator only) | Administrator |
| GET | `/status-codes/next-available` | Preview (non-binding) the next available identifier for a Functional Group + Subgroup, for UI display only — not allocated until Submit f... | Administrator, Engineer |
| GET | `/audit-log` | Search audit log (Administrator; Reviewer/Chief Engineer read-only subset) | Administrator, Reviewer, Chief Engineer |
| GET | `/health/ready` | Readiness probe (no authentication, I-21): database reachable, schema at the expected Alembic head, newest audit rows chain correctly, la... | Public |
| GET | `/status-codes/similar` | Existing codes of a subgroup with a similar title ("did you mean to revise ...?", I-12) | Administrator, Engineer |
| GET | `/status-codes/{statusCodeId}/where-used` | Every other code whose current revision refers to this one (repeated-error pointer, related codes, supersession, platform variant) - I-04 | Working roles (not Viewer) and StCd Owner (read only) |
| GET | `/change-sets/{changeSetId}/readiness` | What still stops each Draft of the batch from being submitted, with the rule of the sample inspection (FR-180) | Working roles (not Viewer) and StCd Owner (read only) |
| POST | `/change-sets/{changeSetId}/bulk-edit` | Set the same status category, platforms, available group or access levels on the Drafts of the batch (FR-180); each Draft is saved on its... | Administrator, Engineer |
| POST | `/change-sets/{changeSetId}/bulk-submit` | Submit for review the Drafts of the batch that the caller wrote (FR-180); one that is not ready is reported with the reason | Administrator, Engineer |
| POST | `/change-sets/{changeSetId}/domain-signoffs` | Sign off an engineering domain on the Drafts of the batch (FR-180); more than a handful of codes need a passed `sample_id` | Administrator, Engineer |
| POST | `/change-sets/{changeSetId}/samples` | Draw the sample a bulk decision at `step` needs (FR-180) - stratified by subgroup, drawn for the caller, valid 24 hours | Working roles (not Viewer) |
| GET | `/change-sets/{changeSetId}/samples` | The samples drawn for the batch, newest first (FR-180) | Working roles (not Viewer) and StCd Owner (read only) |
| GET | `/change-sets/{changeSetId}/dossier.xlsx` | The change set as an XLSX dossier for an audit - codes with their decisions, samples with their verdicts, the audit entries (FR-180) | Working roles (not Viewer) and StCd Owner (read only) |
| GET | `/bulk-samples/{sampleId}` | One sample with its sampled codes and their verdicts (FR-180) | Working roles (not Viewer) and StCd Owner (read only) |
| PUT | `/bulk-samples/{sampleId}/items/{changeRequestId}` | Mark a sampled code OK or DEFECT (a defect needs a note); only by the person who drew the sample (FR-180) | Working roles (not Viewer) |
| POST | `/bulk-samples/{sampleId}/reject-defects` | Send back the codes of a failed sample that were found defective, with the note as the reason, and close the sample (FR-180) | Working roles (not Viewer) |
| GET | `/status-codes/{statusCodeId}/connections` | What suppresses this code, what it suppresses, what it requires and where it escalates, read from the imported programs, with the chain o... | Working roles (not Viewer) and StCd Owner (read only) |
| GET | `/status-codes/connections` | The causes with the codes they suppress (a tree), the escalation targets and what looks wrong in the connections between codes (FR-179) | Working roles (not Viewer) and StCd Owner (read only) |
| GET | `/status-codes/{statusCodeId}/family` | The code and its platform variants (I-25) | Any signed-in user |
| POST | `/status-codes/{statusCodeId}/platform-variants` | Copy the latest decided revision into a new Draft for another turbine platform, linked to the source (I-25) | Administrator, Engineer |
| PUT | `/status-codes/{statusCodeId}/planned-dates` | Set planned effective / deprecation dates on the current revision (I-27, Administrator) | Administrator |
| POST | `/status-codes/{statusCodeId}/mc-drafts` | Create a Main Controller Draft from a Hub Controller code (I-36) | Administrator, Engineer |
| GET | `/hub-consolidation/mapping` | Every Hub Controller code with its Main Controller replacement and how far that is (I-36) | Working roles (not Viewer) and StCd Owner (read only) |
| POST | `/hub-consolidation/deprecation-requests` | Open a deprecation request for every Released Hub code of a group whose MC replacement is Released (I-36, Administrator) | Administrator |
| GET | `/change-requests/stalled` | Requests waiting past their amber/red SLA threshold (I-08, Administrator) | Administrator |
| GET | `/change-requests/{crId}/sla` | How long the request has waited at its stage, in business days, and its SLA level (I-08) | Working roles (not Viewer) |
| POST | `/change-requests/{crId}/reviewer-assignment/auto` | Assign the least-loaded available Reviewer (I-30, Administrator) | Administrator |
| GET | `/reviewers/workload` | Open reviews per active, available Reviewer (I-30, Administrator) | Administrator |
| GET | `/change-requests/{crId}/field-comments` | Comments attached to single fields of the revision (I-23) | Working roles (not Viewer) |
| POST | `/change-requests/{crId}/field-comments` | Comment on one field while the CR is in Review or Pending Approval (I-23) | Administrator, Reviewer, Chief Engineer |
| POST | `/field-comments/{commentId}/resolve` | Mark a field comment resolved (the commenter, the CR author or an Administrator) | Working roles (not Viewer) |
| GET | `/review-checklist-items` | Active review-checklist items (I-23); Administrators may add include_inactive=true | Working roles (not Viewer) |
| POST | `/review-checklist-items` | Add a checklist item for one Functional System Group or all (Administrator) | Administrator |
| PATCH | `/review-checklist-items/{itemId}` | Edit or (de)activate a checklist item (Administrator) | Administrator |
| GET | `/change-requests/{crId}/review-checklist` | The checklist items that apply to the CR and the confirmations already recorded (I-23) | Working roles (not Viewer) |
| GET | `/change-requests/{crId}/attachments` | Evidence attached to the CR (I-13) | Working roles (not Viewer) |
| POST | `/change-requests/{crId}/attachments` | Attach evidence (author or Administrator, CR open) | Administrator, Engineer |
| GET | `/attachments/{attachmentId}` | Download evidence as an attachment (never rendered in the browser) | Working roles (not Viewer) |
| DELETE | `/attachments/{attachmentId}` | Remove evidence while the CR is still a Draft (uploader or Administrator) | Administrator, Engineer |
| GET | `/change-sets` | Change sets - groups of CRs shipping with one controller software release (I-11) | Working roles (not Viewer) and StCd Owner (read only) |
| POST | `/change-sets` | Create a change set (Administrator, Engineer, Chief Engineer) | Administrator, Engineer, Chief Engineer |
| GET | `/change-sets/{changeSetId}` | A change set with its CRs, their states and SLA levels | Working roles (not Viewer) and StCd Owner (read only) |
| POST | `/change-sets/{changeSetId}/change-requests` | Add an open CR to the set (its author or an Administrator) | Administrator, Engineer |
| DELETE | `/change-sets/{changeSetId}/change-requests/{crId}` | Take a CR out of the set | Administrator, Engineer |
| POST | `/change-sets/{changeSetId}/close` | Close the set (Administrator) | Administrator |
| POST | `/change-sets/{changeSetId}/decisions` | Decide several CRs of the set in one sitting | Administrator, Reviewer, Chief Engineer |
| GET | `/delegations` | Delegations you gave or received (Administrators see all). include_inactive=true adds ended and revoked ones | Working roles (not Viewer) |
| POST | `/delegations` | Name a delegate for a date range (I-16) | Administrator, Reviewer, Chief Engineer |
| DELETE | `/delegations/{delegationId}` | Revoke a delegation (the delegator or an Administrator) | Administrator, Reviewer, Chief Engineer |
| GET | `/notifications` | Your in-app notices (I-08), newest first | Any signed-in user |
| POST | `/notifications/read-all` | Mark all your notices as read | Any signed-in user |
| POST | `/notifications/{notificationId}/read` | Mark one notice as read | Any signed-in user |
| GET | `/settings` | Administrator-managed settings (SLA thresholds, reviewer auto-assignment, capacity alert level) with defaults | Administrator |
| PUT | `/settings` | Change settings (Administrator) | Administrator |
| GET | `/reports/catalogue-health` | Catalogue health and number-range capacity forecast (I-19) | Administrator, Reviewer, Chief Engineer |
| GET | `/reports/kpis` | The business-case KPIs - approval time, cross-domain turnaround, audit-trail completeness, queue ages, ownerless codes (I-10) | Administrator, Chief Engineer |
| GET | `/reports/occurrences` | Codes that never fire and the most frequent ones, from imported occurrence counts (I-28) | Administrator, Chief Engineer |
| GET | `/occurrence-imports` | Imported occurrence batches (I-28) | Administrator, Chief Engineer |
| POST | `/occurrence-imports` | Import occurrence counts per status code for a period (I-28): CSV/XLSX with the columns status_code_identifier and occurrences, aggregate... | Administrator, Chief Engineer |
| GET | `/operations/backup-status` | State and age of the last verified backup (I-09, Administrator) | Administrator |
| POST | `/operations/audit-verify` | Walk the audit-log hash chain now (I-18, Administrator). `ok:false` names the first bad row | Administrator |
| GET | `/imports/template` | Download the import template - exact headers (CSV) or headers, instructions and the lookup codes (XLSX) (I-05) | Administrator, Engineer |
| GET | `/imports/reconciliation` | Migration progress - legacy rows imported, in review, approved, released, retired and (with expected_total) still missing (I-05) | Administrator, Engineer |
| POST | `/imports/reconciliation` | Same report with the legacy master list uploaded so the missing legacy numbers are named | Administrator, Engineer |
| POST | `/imports/st/preview` | Status code import from generated StCd_<n>.st programs, step 1 (v4.2): upload several files or a ZIP; nothing is created | Administrator, Engineer |
| POST | `/imports/st` | Status code import from generated StCd_<n>.st programs, step 2 (v4.2): create the Drafts for the chosen programs of a preview | Administrator, Engineer |
| GET | `/status-codes/{statusCodeId}/import-source` | Where an imported status code came from - file, SHA-256, program and every attribute parsed from it, including those without a catalogue... | Working roles (not Viewer) |
| GET | `/legacy-mapping` | Legacy number -> new identifier for every code that carries a legacy number (v4.2) | Working roles (not Viewer) |
| GET | `/legacy-mapping/export` | The legacy -> new mapping as CSV (default) or XLSX, with the filters of the list (v4.2) | Working roles (not Viewer) |
| GET | `/export-profiles` | Export profiles - Administrator-managed column sets (I-02). include_inactive=true is honoured for Administrators | Any signed-in user |
| POST | `/export-profiles` | Create an export profile (Administrator) | Administrator |
| PATCH | `/export-profiles/{profileId}` | Change or deactivate an export profile (Administrator) | Administrator |
| GET | `/audiences` | The eight audiences an export can be scoped to (I-03) | Any signed-in user |
| GET | `/releases/{releaseId}/notes` | Release notes - added / changed (field-level diff) / deprecated against the previous published Release (I-06) | Any signed-in user |
| GET | `/releases/{releaseId}/offline-bundle` | One self-contained HTML lookup page for the Release, for use at the turbine without connectivity (I-24) | Any signed-in user |
| GET | `/releases/{releaseId}/exports` | Every export recorded for the Release with its SHA-256 (I-06) | Working roles (not Viewer) |
| PUT | `/releases/{releaseId}/target-versions` | Set the controller software versions a Release is published for (I-07, Administrator, before publish only) | Administrator |
| GET | `/releases/{releaseId}/baseline` | Counts of the complete baseline of a Release - every code valid as of it - by controller and platform (FR-173) | Any signed-in user |
| GET | `/releases/{releaseId}/readiness` | What is still missing before the documents of a Release are complete - translated codes per language and codes without confirmed access l... | Working roles (not Viewer) and StCd Owner (read only) |
| POST | `/releases/{releaseId}/packages` | Build the package of a published Release - the complete baseline in every language for every access level, with release notes and a manif... | Any signed-in user |
| GET | `/releases/{releaseId}/packages` | The packages built for a Release, newest first (FR-174) | Any signed-in user |
| GET | `/packages/{jobId}` | State and progress of a package (FR-174) | Any signed-in user |
| GET | `/packages/{jobId}/download` | Download the finished package as a ZIP (FR-174) | Any signed-in user |
| GET | `/exports/{jobId}/manifest` | The manifest recorded for an export (I-06) | Working roles (not Viewer) |
| POST | `/exports/verify` | Is this file one the system produced (I-06)? | Any signed-in user |
| GET | `/software-versions/matrix` | Which Released codes apply to a controller software version (I-07) | Any signed-in user |
| GET | `/software-versions/changes` | What was added, removed and changed between two software versions (I-07) | Any signed-in user |
| GET | `/revisions/{revisionId}/translations` | Translation status per language - MISSING, DRAFT or APPROVED (I-15) | Any signed-in user |
| PUT | `/revisions/{revisionId}/translations/{language}` | Save a translation as a DRAFT (Engineer, Administrator; source text must be Approved) | Administrator, Engineer |
| POST | `/revisions/{revisionId}/translations/{language}/approve` | Approve a translation - a light review by a Reviewer or Administrator other than the translator (I-15) | Administrator, Reviewer |
| POST | `/revisions/{revisionId}/translations/carry-over` | Copy the previous revision's translations as DRAFTs for languages this revision lacks | Administrator, Engineer |
| GET | `/translations/worklist` | Current Approved/Released codes still lacking an approved translation in a language (I-15) | Working roles (not Viewer) |
| GET | `/saved-searches` | Your saved status-code searches and the columns the list can show (I-26) | Any signed-in user |
| POST | `/saved-searches` | Save the filters and visible columns under a name (saving under an existing name replaces it) | Any signed-in user |
| DELETE | `/saved-searches/{searchId}` | Remove one of your saved searches | Any signed-in user |
| GET | `/api-tokens` | Machine API tokens (I-29, Administrator) | Administrator |
| POST | `/api-tokens` | Create a scoped, expiring token (max 365 days) | Administrator |
| DELETE | `/api-tokens/{tokenId}` | Revoke a token (Administrator) | Administrator |
| GET | `/webhooks` | Webhooks fired on release.published (I-29, Administrator) | Administrator |
| POST | `/webhooks` | Register a webhook | Administrator |
| PATCH | `/webhooks/{webhookId}` | Pause or resume a webhook | Administrator |
| GET | `/webhooks/{webhookId}/deliveries` | Recent deliveries of a webhook with their outcome | Administrator |
| GET | `/changes` | Change feed - releases, deprecations, reinstatements and archivals in audit order (I-29) | Any signed-in user; API token `changes:read` |
<!-- api-summary:end -->

Export file names follow `cscm_<kind>[_<label>]_YYYY-MM-DD_HH-MM.<ext>` (generation time, UTC): `released`, `release_<version label>`, `working-set_NOT_FOR_DISTRIBUTION`, `full-database-backup`, `release-notes_<version label>`, `offline-lookup_<version label>`. Non-API endpoints: `GET /metrics` (Prometheus text, §11) and the UI pages under `/`.

## 8. Idempotency & Concurrency

Optimistic concurrency on Draft edits is real since v4 (§10, FR-090) and publishing is idempotent (a second publish of a published Release is refused with 409). Identifier allocation on `POST /change-requests/{id}/submit` is race-safe by construction (07-database-design.md §7a) — two concurrent submissions in the same Functional Group/Subgroup can never receive the same number; the loser of the race simply receives the next number after, not an error.

## 9. Rate Limiting

`POST /auth/login` is rate-limited per IP (10 attempts in 5 minutes) and per username (5 in 15 minutes) independently; the counters are stored in the database, so they are shared by all worker processes and survive a restart (NFR-009).

## 10. v4 Conventions

**Step-up (FR-126).** The request body of `reviewer-signoff`, `admin-signoff`, `chief-engineer-decide`, `POST /releases/{id}/publish`, `POST /exports/full-database` and `POST /change-sets/{id}/decisions` carries `current_password`. Absent → 403 `step_up_required`; wrong → 403 `step_up_failed`. The check is audited and never logs the password.

**Concurrency (FR-090).** `PATCH /revisions/{id}` may carry `expected_row_version` and/or `expected_updated_at`; a stale value → 409 `conflict` and nothing is changed. Responses return `row_version` and `updated_at` so a client can send them back. Saves also return `warnings` — soft findings (unknown or retired references, similar titles) that never block (FR-091, FR-093).

**Export shaping (FR-100 … FR-111).** `GET /releases/{id}/export` and `GET /exports/released` accept `format` (`csv|json|xlsx|pdf`) and optionally `profile` (an export-profile code), `audience`, `language`, `strict_language=true`, `software_version` and `bundle=true` (a ZIP holding the data file, `MANIFEST.json` and release notes). `audience` is rejected on the unapproved working set. Every export response carries `X-Content-SHA256` (of the data file) and is recorded as an export job whose manifest is available at `GET /exports/{jobId}/manifest`; `POST /exports/verify` checks an uploaded file against recorded exports and an uploaded manifest. Release notes, the offline bundle and the export history are `GET /releases/{id}/notes`, `/offline-bundle` and `/exports`.

**API tokens (FR-144, SEC-027).** An Administrator creates a token (`POST /api-tokens`; the secret is returned once). It is sent as `Authorization: Bearer cscm_…` and is honoured only on `GET` operations whose row above names its scope (`catalogue:read`, `changes:read`), with Viewer-level visibility. It can never write; a revoked, expired or unknown token gets 401.

**Change feed (FR-145).** `GET /changes?since_id=<n>&limit=<1..500>` returns `{items, next_since_id, has_more}`; poll with the previous `next_since_id`. The response has a weak `ETag`; `If-None-Match` with the current value answers 304. Events: `code.released`, `code.deprecated`, `code.reinstated`, `code.archived`.

**Webhooks (FR-146, SEC-028).** A webhook registered for `release.published` receives `POST {"event": "release.published", "data": {release_id, name, version_label, published_at, item_count}}` with the headers `X-CSCM-Event` and `X-CSCM-Signature: sha256=<HMAC-SHA-256 of the body with the webhook secret>`. Targets must resolve to private or loopback addresses; redirects are not followed; the outcome of each delivery is listed at `GET /webhooks/{id}/deliveries`.

**Idempotent reads, paging.** List endpoints that return `items` follow §6; the change feed uses a cursor instead of pages.

## 11. Operational Endpoints (v4)

| Endpoint | Purpose | Access |
|---|---|---|
| `GET /api/v1/health` | Liveness | Public |
| `GET /api/v1/health/ready` | Readiness: database, schema head, newest audit rows, last verified backup. `200` with `status` `ok` or `degraded`, `503` with `unavailable`. Reveals no business data. | Public (internal network) |
| `GET /metrics` | Prometheus text: `cscm_http_requests_total`, `cscm_http_request_duration_seconds`, `cscm_db_lock_wait_seconds`, `cscm_change_requests`, `cscm_revisions`, `cscm_cr_waiting`, `cscm_backup_age_hours`, `cscm_backup_ok` | Allow-listed networks (`METRICS_ALLOWED_CIDRS`) or `Authorization: Bearer <METRICS_TOKEN>`; otherwise 403 (SEC-029) |

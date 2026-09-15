# 13. Test Strategy — CSCM Tool

## 1. Test Levels

Unchanged in structure from v1 (13-test-strategy.md v1 §1): Unit, Integration, System (API), Performance, Security, UAT — same tooling (`pytest`, temp-file SQLite, Flask test client, `locust`/`pytest-benchmark`, `bandit`/`pip-audit`/ZAP baseline).

## 2. Unit Tests

Minimum coverage target unchanged: 80% on `service/` and `validation/`. Required areas, updated for v2:
- Lifecycle transition validator: every legal transition in the 7-state model (05-governance-handbook.md §5) succeeds; every illegal transition (exhaustive pairwise) raises the correct domain exception.
- Identifier allocation: sequential within a Functional System Group's range; sequential within a Functional Subgroup's sub-band when selected; independence between groups; capacity-exhaustion behavior (07-database-design.md §7a); sandbox codes never draw from a real range.
- Dual sign-off logic: recording the first sign-off leaves state at `REVIEW`; recording the second (either order) atomically advances to `PENDING_APPROVAL`; a reject from either sign-off returns to `DRAFT` and clears both sign-off columns.
- Chief Engineer approval: segregation-of-duties check against all three of author, Reviewer sign-off, Administrator sign-off.
- Cross-Domain Sign-Off gating: Submit-for-Review blocked while any required domain lacks a `DomainSignoff`; unblocked once all present.
- Restricted-field handling: Engineer-proposed `access_rights_id` is not authoritative until `admin_signoff_at` is set.
- Cross-field rules (unchanged from v1): Safety category × Alarm Behaviour; Auto reset × delay > 0; Emergency Brake × Fault/Safety category.
- Sandbox delete: only permitted when `is_sandbox = true`; blocked for every other record, with the DB trigger as a second line of defense.

## 3. Integration Tests

- Repository layer against real (temp-file) SQLite: uniqueness of `status_code_identifier`, partial unique indexes (`is_current`, one-open-CR now spanning three states), all four triggers (`trg_prevent_edit_locked_revision`, `trg_prevent_release_item_delete`, `trg_prevent_sandbox_release`, `trg_prevent_nonsandbox_delete`).
- Full Change Request lifecycle: Draft → (domain sign-offs) → Review (identifier allocated) → (dual sign-off) → PendingApproval → Chief Engineer Approve → Approved → Release publish → Released.
- Atomic Release publish, including the sandbox-exclusion guarantee: attempt to add a sandbox revision to a Release candidate set and assert it is never offered as a candidate and, if forced via direct repository call in a test, is rejected by the trigger.
- Concurrent identifier allocation: two simulated concurrent submissions within the same Functional Subgroup never receive the same number (07-database-design.md §7a).
- Sandbox delete: full lifecycle create → delete, assert the row is gone, assert the `SANDBOX_CREATE` and `SANDBOX_DELETE` audit entries both exist and the latter's `before_value` contains a complete pre-delete snapshot.
- Audit log completeness: every new v2 action code (12-audit-compliance.md §2) produces exactly one audit entry per triggering call.

## 4. System (API) Tests

- Full request/response contract conformance against `artifacts/openapi.yaml` v2.0.0.
- Authorization matrix: five roles × every endpoint, including the three decision endpoints' segregation-of-duties checks and the sandbox-only-delete / Administrator-only-full-export restrictions.
- Identifier lifecycle via API: `status_code_identifier` is `null` in every response while Draft; becomes non-null only after `POST .../submit`; `GET /status-codes/next-available` never reserves a number (two sequential calls without an intervening submit return the same preview).
- Cross-Domain Sign-Off: a Submit attempt with an outstanding required domain returns 422 with a field error naming the missing domain; a matching-domain Engineer's `POST .../domain-signoffs` call from a non-matching domain returns 403.
- Export correctness: catalogue export never includes sandbox-flagged records even if explicitly requested; `GET /exports/full-database` returns 403 for every non-Administrator role.

## 5. Performance Tests

Unchanged targets from v1 (13-test-strategy.md v1 §5): p95 500ms search, p95 200ms single-record read, 5s CSV/JSON export, 15s PDF export, 50 concurrent users — re-validated against a synthetic dataset now distributed across all nine Functional System Groups to confirm identifier allocation contention does not create a hot-row bottleneck under concurrent submission load within a single popular group.

## 6. Security Tests

Unchanged mechanism from v1 (`bandit`, `pip-audit` in CI; ZAP baseline pre-release; manual OWASP checklist). Added: a specific manual check that no outbound network call in the codebase targets a public-cloud endpoint (11-security-architecture.md §12 "No-Cloud Verification Checklist") — grep-based CI check for known cloud SDK imports (e.g. `azure.*`, `boto3`, `google.cloud`) failing the build if found, since this is now a hard architectural constraint, not a preference.

## 7. User Acceptance Test Scenarios

- UAT-01: Engineer creates a new Status Code under Converter/Grid Interface (WCNV), sees no fixed identifier while Draft, submits for Review, and confirms an `StCd-01xxx` identifier appears immediately after submission.
- UAT-02: Reviewer and Administrator each sign off independently (in either order); the CR reaches PendingApproval automatically after the second sign-off, with no separate action required.
- UAT-03: Chief Engineer approves; the revision reaches Approved; Engineer sees the updated status on My Change Requests.
- UAT-04: Reviewer rejects with a comment; Engineer sees the comment, edits, resubmits; confirms the Administrator's prior sign-off (if any) was cleared and must be re-given.
- UAT-05: An Electrical-domain Engineer creates a Generator-group (WGEN) code, is blocked from submitting due to outstanding Controls-domain fields, requests sign-off, a Controls-domain Engineer completes and signs off, and submission then succeeds.
- UAT-06: Administrator builds and publishes a Release from Approved codes, confirms an Approved-but-excluded candidate remains Approved, and confirms no sandbox code ever appears as a candidate.
- UAT-07: Viewer searches and exports the current Released catalogue filtered to a single Functional System Group.
- UAT-08: Administrator creates a sandbox Status Code, exercises it through Draft/Review/PendingApproval for training purposes, confirms it can never be added to a real Release, and permanently deletes it, then confirms via Audit Log Search that both the creation and deletion are retained with a full snapshot.
- UAT-09: Any user attempts (via UI and via direct API call) to sign off or approve their own submission at each of the three decision points and is blocked in every case.
- UAT-10: Administrator performs a full-database export; confirms no other role can reach that action.

## 8. Full Test Matrix

| ID | Level | Area | Scenario | Priority |
|---|---|---|---|---|
| TC-001 | Unit | Lifecycle | All valid 7-state transitions succeed | P1 |
| TC-002 | Unit | Lifecycle | All invalid transitions rejected (exhaustive pairwise) | P1 |
| TC-003 | Unit | Validation | Each mandatory field rejects null/empty | P1 |
| TC-004 | Unit | Numbering | Identifier format `^StCd-\d{5}$` / `^StCd-T\d{5}$` enforced | P1 |
| TC-005 | Unit | Validation | Safety category blocks Self-Clearing/Silent alarm behaviour | P1 |
| TC-006 | Unit | Validation | Auto reset requires delay_before_reset_seconds > 0 | P2 |
| TC-007 | Unit | Numbering | Sequential allocation per Functional System Group range | P1 |
| TC-008 | Unit | Numbering | Sequential allocation per Functional Subgroup sub-band, independent of siblings | P1 |
| TC-009 | Unit | SoD | Reviewer sign-off by requester raises domain error | P1 |
| TC-009a | Unit | SoD | Administrator sign-off by requester raises domain error | P1 |
| TC-009b | Unit | SoD | Chief Engineer approval by requester/reviewer/admin raises domain error | P1 |
| TC-010 | Integration | Uniqueness | Duplicate `status_code_identifier` rejected at DB layer | P1 |
| TC-011 | Integration | Concurrency | One current revision per code enforced under concurrent writes | P1 |
| TC-012 | Integration | Concurrency | Only one open (Draft/Review/PendingApproval) CR per code | P1 |
| TC-013 | Integration | Immutability | Trigger blocks edit of Approved/Released/Archived revision | P1 |
| TC-014 | Integration | Release | Atomic publish: partial failure rolls back fully | P1 |
| TC-014a | Integration | Release | Sandbox revision can never be inserted into release_item | P1 |
| TC-015 | Integration | Audit | Every v2 state-changing action produces exactly one audit entry | P1 |
| TC-015a | Integration | Audit | Sandbox delete produces SANDBOX_DELETE with full before_value snapshot | P1 |
| TC-016 | System | Auth | Login lockout after 5 failed attempts, clears after 15 min | P1 |
| TC-017 | System | Auth | Session expires after 30 min idle | P2 |
| TC-018 | System | AuthZ | Full 5-role × endpoint permission grid | P1 |
| TC-018a | System | AuthZ | Sandbox delete: 403 for non-Administrator and for non-sandbox records | P1 |
| TC-018b | System | AuthZ | Full-database export: 403 for every non-Administrator role | P1 |
| TC-019 | System | AuthZ | Direct API call cannot bypass SoD at any of the three decision points | P1 |
| TC-020 | System | Domain Sign-Off | Submit blocked with 422 while a required domain is unsigned | P1 |
| TC-021 | System | Domain Sign-Off | Sign-off attempt from a non-matching domain returns 403 | P1 |
| TC-022 | System | Search | Full-text search matches status_code_identifier, title, description | P2 |
| TC-023 | System | Export | Catalogue export never includes sandbox-flagged records | P1 |
| TC-024 | Performance | Search | p95 ≤ 500ms at 20,000 revisions across all 9 groups | P2 |
| TC-025 | Performance | Numbering | Concurrent submission within one popular group does not breach identifier-allocation latency target | P2 |
| TC-026 | Security | Injection | XSS payload in Description/comment fields is escaped on render | P1 |
| TC-027 | Security | Injection | SQL injection probe on search filter has no effect | P1 |
| TC-028 | Security | CSRF | State-changing request without CSRF token rejected | P1 |
| TC-029 | Security | No-Cloud | CI grep check fails the build on any cloud-SDK import | P1 |
| TC-030 | UAT | End-to-end | UAT-01 through UAT-10 (§7) | P1 |

## 9. Test Environments

Unchanged from v1 (§9): local, CI, staging, production, all on-premises per the deployment constraint.

## 10. Definition of "Test Complete" for a Release

Unchanged in structure from v1 (§10): all P1 cases pass, coverage threshold met, security checklist clean, at least one full UAT pass signed off.

# 13. Test Strategy — CSCM Tool

## 1. Test Levels

Unit, Integration, System (API), Performance, Security, UAT — tooling: `pytest`, in-memory or file SQLite, the Flask test client, `schemathesis`/`hypothesis` for contract and property tests, timing tests without coverage tracing for performance, `black`/`ruff`/`mypy`/`bandit`/`pip-audit` as gates. Since v4 the suite is verified three ways (§11) and every requirement id must be accounted for (§12).

## 2. Unit Tests

Minimum coverage target: 80% on `service/` and `validation/`. Required areas, updated for v2:
- Lifecycle transition validator: every legal transition in the 7-state model (05-governance-handbook.md §5) succeeds; every illegal transition (exhaustive pairwise) raises the correct domain exception.
- Identifier allocation: sequential within a Functional System Group's range; sequential within a Functional Subgroup's sub-band when selected; independence between groups; capacity-exhaustion behavior (07-database-design.md §7a); sandbox codes never draw from a real range.
- Dual sign-off logic: recording the first sign-off leaves state at `REVIEW`; recording the second (either order) atomically advances to `PENDING_APPROVAL`; a reject from either sign-off returns to `DRAFT` and clears both sign-off columns.
- Chief Engineer approval: segregation-of-duties check against all three of author, Reviewer sign-off, Administrator sign-off.
- Cross-Domain Sign-Off gating: Submit-for-Review blocked while any required domain lacks a `DomainSignoff`; unblocked once all present.
- Restricted-field handling: each Engineer-proposed audience-access field (development/sales/tcc/service/turbine-operator-package/grid-operator/service-partner/customer, corrected 2026-09-17) is not authoritative until `admin_signoff_at` is set.
- Field-format rules (corrected 2026-09-17, replacing the retired Safety-category/Alarm-Behaviour and Auto-reset/delay cross-field rules, neither of which the real data model supports): `set_delay`/`reset_delay` match the `^\*?\d+(\.\d+)?\s?(ms|s|min|MIN|h|d)$` pattern; `status_category` is restricted to `ERROR`/`WARNING`/`INFO`; Functional Subgroup must belong to the selected Functional System Group; at least one Turbine Platform is selected.
- Sandbox delete: only permitted when `is_sandbox = true`; blocked for every other record, with the DB trigger as a second line of defense.

## 3. Integration Tests

- Repository layer against real (temp-file) SQLite: uniqueness of `status_code_identifier`, partial unique indexes (`is_current`, one-open-CR now spanning three states), all eight triggers (`trg_prevent_edit_locked_revision`, `trg_prevent_release_item_delete`, `trg_prevent_sandbox_release`, `trg_prevent_nonsandbox_delete`, `trg_prevent_subgroup_overlap`, `trg_prevent_group_overlap`, `trg_audit_no_update`, `trg_audit_no_delete`) and the four FTS triggers.
- Full Change Request lifecycle: Draft → (domain sign-offs) → Review (identifier allocated) → (dual sign-off) → PendingApproval → Chief Engineer Approve → Approved → Release publish → Released.
- Atomic Release publish, including the sandbox-exclusion guarantee: attempt to add a sandbox revision to a Release candidate set and assert it is never offered as a candidate and, if forced via direct repository call in a test, is rejected by the trigger.
- Concurrent identifier allocation: two simulated concurrent submissions within the same Functional Subgroup never receive the same number (07-database-design.md §7a).
- Sandbox delete: full lifecycle create → delete, assert the row is gone, assert the `SANDBOX_CREATE` and `SANDBOX_DELETE` audit entries both exist and the latter's `before_value` contains a complete pre-delete snapshot.
- Audit log completeness: every new v2 action code (12-audit-compliance.md §2) produces exactly one audit entry per triggering call.

## 4. System (API) Tests

- Full request/response contract conformance against `artifacts/openapi.yaml` v4.0.0 (161 operations; every operation of the code is in the contract and every unauthenticated call is 401, except the documented public routes).
- Authorization matrix: six roles × every endpoint, including the three decision endpoints' segregation-of-duties checks and the sandbox-only-delete / Administrator-only-full-export restrictions.
- Identifier lifecycle via API: `status_code_identifier` is `null` in every response while Draft; becomes non-null only after `POST .../submit`; `GET /status-codes/next-available` never reserves a number (two sequential calls without an intervening submit return the same preview).
- Cross-Domain Sign-Off: a Submit attempt with an outstanding required domain returns 422 with a field error naming the missing domain; a matching-domain Engineer's `POST .../domain-signoffs` call from a non-matching domain returns 403.
- Export correctness: catalogue export never includes sandbox-flagged records even if explicitly requested; `POST /exports/full-database` returns 403 for every non-Administrator role.

## 5. Performance Tests

Targets: p95 500ms search, p95 200ms single-record read, 5s CSV/JSON export, 15s PDF export, 50 concurrent users — re-validated against a synthetic dataset now distributed across all nine Functional System Groups to confirm identifier allocation contention does not create a hot-row bottleneck under concurrent submission load within a single popular group.

## 6. Security Tests

`bandit` and `pip-audit` in CI (§11 gates); ZAP baseline pre-release; manual OWASP checklist. Since v4 also: the route inventory (every route declares its access and the declared role list is what each of the five roles actually gets), step-up, token and webhook tests, audience leakage tests, attachment hardening and the no-egress lifecycle test. Added: a specific manual check that no outbound network call in the codebase targets a public-cloud endpoint (11-security-architecture.md §12 "No-Cloud Verification Checklist") — grep-based CI check for known cloud SDK imports (e.g. `azure.*`, `boto3`, `google.cloud`) failing the build if found, since this is now a hard architectural constraint, not a preference.

## 7. User Acceptance Test Scenarios

- UAT-01: Engineer creates a new Status Code under Converter & Grid Interface (WCNV), sees no fixed identifier while Draft, submits for Review, and confirms an `StCd-01xxx` identifier appears immediately after submission.
- UAT-02: Reviewer and Administrator each sign off independently (in either order); the CR reaches PendingApproval automatically after the second sign-off, with no separate action required.
- UAT-03: Chief Engineer approves; the revision reaches Approved; Engineer sees the updated status on My Change Requests.
- UAT-04: Reviewer rejects with a comment; Engineer sees the comment, edits, resubmits; confirms the Administrator's prior sign-off (if any) was cleared and must be re-given.
- UAT-05: An Electrical-domain Engineer creates a Generator-group (WGEN) code, is blocked from submitting due to outstanding Controls-domain fields, requests sign-off, a Controls-domain Engineer completes and signs off, and submission then succeeds.
- UAT-06: Administrator builds and publishes a Release from Approved codes, confirms an Approved-but-excluded candidate remains Approved, and confirms no sandbox code ever appears as a candidate.
- UAT-07: Viewer searches and exports the current Released catalogue filtered to a single Functional System Group.
- UAT-08: Administrator creates a sandbox Status Code, exercises it through Draft/Review/PendingApproval for training purposes, confirms it can never be added to a real Release, and permanently deletes it, then confirms via Audit Log Search that both the creation and deletion are retained with a full snapshot.
- UAT-09: Any user attempts (via UI and via direct API call) to sign off or approve their own submission at each of the three decision points and is blocked in every case.
- UAT-10: Administrator performs a full-database export; confirms no other role can reach that action.
- UAT-11 (new 2026-09-17): Engineer uploads a CSV library file; confirms every valid row becomes a Draft requiring the full sign-off/approval cycle (none land as Approved/Released), and the error report correctly lists rows that failed validation.
- UAT-12 (new 2026-09-17): Engineer attempts to create a Status Code without selecting a Functional Subgroup; confirms Submit is blocked. Administrator creates a new Functional Subgroup in a reserved block, then successfully overlaps-tests a conflicting range and receives a clear, non-destructive error (the form retains the entered name).
- UAT-13 (new 2026-09-17): Engineer deliberately submits an incomplete New Status Code form; confirms the resulting validation error leaves every already-entered field intact (no reset), and confirms every classification dropdown shows an inline description for its selected option.

## 8. Full Test Matrix

| ID | Level | Area | Scenario | Priority |
|---|---|---|---|---|
| TC-001 | Unit | Lifecycle | All valid 7-state transitions succeed | P1 |
| TC-002 | Unit | Lifecycle | All invalid transitions rejected (exhaustive pairwise) | P1 |
| TC-003 | Unit | Validation | Each mandatory field rejects null/empty | P1 |
| TC-004 | Unit | Numbering | Identifier format `^StCd-\d{5}$` / `^StCd-T\d{5}$` enforced | P1 |
| TC-005 | Unit | Validation | `set_delay`/`reset_delay` reject a value not matching the unit pattern (e.g. `10minutes`, `abc`) | P1 |
| TC-006 | Unit | Validation | `status_category` rejects any value outside ERROR/WARNING/INFO | P1 |
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
| TC-030 | UAT | End-to-end | UAT-01 through UAT-13 (§7) | P1 |
| TC-031 | Unit | Validation | Status Code create rejected (422) with no functional_subgroup | P1 |
| TC-032 | Integration | Lookups | New subgroup insert rejected on sub-range overlap (trigger + service layer) | P1 |
| TC-033 | System | Import | Import job creates Drafts only; none reach Approved/Released without normal sign-offs | P1 |
| TC-034 | System | Import | Invalid rows produce a downloadable error report and create nothing | P1 |
| TC-035 | System | Export | XLSX export produces the same flat row set as CSV/JSON for the same scope | P2 |
| TC-036 | System | UI/UX | A rejected (422) form submission never clears previously entered field values | P1 |
| TC-037 | Integration | Lookups | New Functional System Group insert rejected on range overlap (trigger + service layer) | P1 |
| TC-038 | Integration | Security / SoD | Step-up password required and audited on every sensitive action; delegation grants decision actions only and keeps segregation of duties (`test_step_up_and_delegation`) | P1 |
| TC-039 | Integration | Data integrity | Stale Draft save refused with 409; reference, duplicate and where-used warnings; platform variants; planned dates; remedy fields; capacity hint (`test_content_integrity`) | P1 |
| TC-040 | Integration | Review aids | Field comments, review checklist, evidence attachments (hardening), change sets, reviewer balancing (`test_review_aids`) | P1 |
| TC-041 | Integration | Workflow | SLA ageing in business days, stalled requests, notices and reminders (idempotent), KPIs (`test_sla_and_notifications`) | P2 |
| TC-042 | Integration | Publication | Profiles and wrapped PDF, audience scoping, manifests / bundles / verification, release notes, software versions, translations, offline bundle (`test_publication`) | P1 |
| TC-043 | Integration | Import | Template, dry run, update mode, reconciliation, error reports, background job on a real file database (`test_import_toolkit`) | P1 |
| TC-044 | Integration | Operations | Audit hash chain (edit / remove / truncate detected, key, archive), verified backups and restore, CLI jobs, readiness, metrics gating, log file (`test_audit_chain_and_ops`) | P1 |
| TC-045 | Integration | Migration | Upgrade of a v3 database keeps data, hashes old audit rows, fills the index, matches a fresh schema, downgrades (`test_schema_upgrade`) | P1 |
| TC-046 | Integration | Integration / reports | API tokens, change feed with ETag, signed webhooks, saved searches, fleet feedback, catalogue health, KPIs, Hub-to-Main consolidation (`test_integrations_and_reports`) | P2 |
| TC-047 | Integration | Search / help | Ranked, typo-tolerant search and its substring fallback; help content complete and consistent with the glossary (`test_search_and_help`) | P2 |
| TC-048 | System | AuthZ | Route inventory: every route declares access, anonymous callers are refused, declared roles equal enforced roles for all six roles (`test_route_inventory`) | P1 |
| TC-049 | System | i18n / a11y | German catalogue complete and every other language complete (FR-167); contrast ≥ 4.5 : 1 in the light and in the dark theme, no colour outside the tokens, the theme choice on every page; landmarks, labels, headings, table scope on every page in both languages (`test_i18n`, `test_accessibility`, `test_dark_mode`); the version is shown and agrees with `pyproject.toml` (`test_version`) | P2 |
| TC-050 | System | Multi-process | Two server processes share the login rate limit and survive 16 concurrent writes (`test_multiprocess`, `unit/test_rate_limit`) | P1 |
| TC-051 | System | Deployment | Installer syntax and dry runs, systemd units, settings written are settings read, production entry point starts and refuses a weak key, CI definitions, PostgreSQL ratchet (`test_deploy_artifacts`) | P2 |
| TC-052 | System | Documentation | The documents agree with the code: endpoint table, schema counts, audit codes, glossary, requirement ids, links (`test_docs_consistency`) | P1 |
| TC-053 | Integration | Status code import | The six real `.st` programs (three Main, three Hub) are read, previewed with multi-select, imported as Drafts with reserved numbers in one change set, issued exactly the reserved number at Submit, the legacy → new mapping is listed and exported, staged uploads are private and expire (`test_st_import`); the status category follows the alarm type, the default or the choice per program (`test_st_category_and_draft_delete`); no value and no category is assumed - a variable stays its name, what the program lacks is listed in the comment; the user-group numbers become named access levels only where exactly one level fits (`test_st_no_assumptions`) | P0 |
| TC-054 | Integration | Roles and languages | The StCd Owner role and its limits (only an Administrator creates users; the owner moves users between Viewer, Engineer and Reviewer and nothing else), role colours, the language names (letters left, flag right), the drawn flags, French / Hindi / Georgian / Arabic pages with English fallback and right-to-left Arabic, catalogue integrity (`test_roles_and_languages`) | P1 |
| TC-055 | Integration | User administration | View, activate / deactivate and delete users: only an unused account is deleted, the password is asked again, an account with history is refused and deactivated, the StCd Owner has no such buttons (`test_user_administration`) | P1 |
| TC-056 | Integration | Withdraw and re-import | Several change requests withdrawn at once with a result each; a withdrawn import Draft gives its number back, a withdrawn code with an identifier keeps it and is restored; changed programs update the Draft or open a revision (`test_withdraw_and_reimport`) | P1 |
| TC-057 | System | Translations | The translation document equals the generator output; ids and fingerprints are stable; every language's review sheet is complete (review, missing, checklist), right to left where needed (`test_translations_doc`) | P1 |
| TC-058 | Integration | E-mail and Windows sign-in | The e-mail address cannot be changed (service, API, database trigger); Windows identity matched by e-mail or `DOMAIN\name`, accepted only from a trusted proxy, no auto-creation, deactivated accounts refused, password routes off in `windows` mode, the developer simulation uses the same path and is refused in production (`test_email_and_windows_signin`) | P1 |
| TC-059 | Integration | Translation review | Assigned reviewers only, managers assign and decide; save validations (a change needs a proposal, placeholders, length), completion rule, XLSX download and upload, no self-decision and final decisions, an accepted proposal shown at once and removable, missing translations proposed, right to left, audit entries (`test_translation_review`) | P1 |
| TC-060 | Integration | PDF in every script | Each of the twelve script families gets its own font, Latin needs none, Arabic is told from Urdu, right-to-left cells are right-aligned, shaping is switched on only for the cells that need it, every character of every translation is covered by a bundled font, the fonts and their licence are bundled, a 1,500-row Latin export stays fast (`test_pdf_scripts`); the rendered pages were looked at | P1 |
| TC-061 | Integration | Technical nomenclature | The vocabulary ships with every term in every language as a draft and agrees with the interface catalogue, a never-translated term has no translation, everybody reads and only the technical roles propose, an interface reviewer has no say, a proposal is a draft until another person approves it, send-back needs a note and reopens an approval, validation, only managers add and change terms and a new English text reopens approvals, the consistency check, export per language and for all, a formula is neutralised in the CSV (`test_terminology`) | P1 |
| TC-062 | System | Windows sign-in against a real Windows identity | SSPI (Negotiate / NTLM) names the Windows user who runs the tests; the whole chain client, gateway, application signs that user in; a request without credentials gets a challenge and never reaches the application; a header the client sends is dropped by the gateway and ignored when it does not come from the trusted gateway; an unknown identity and a deactivated account are refused (`test_windows_gateway`, Windows only) | P1 |
| TC-063 | Integration | Fields of the generated programs | A Main and a Hub program import keeps every field of the file (further programs, mask, task call frequency, flags, 15 user-group levels), the two zero-load attributes are not mixed up, a field of the other controller is refused (API and form, which keeps what was typed), values out of range are refused, a new revision and a Draft update keep what the caller does not send, the diff lists changes, the exports carry the columns and an audience export never does, withdrawing removes the levels (`test_generated_fields`) | P1 |
| TC-064 | Integration | The menu and the beta mark | What each of the six roles sees and does not see, the groups, no link twice, only the current page marked, the counts at the links and on the group, groups that open and close, the Menu button and its script and style, the menu in German, a language is beta until a review of its current text is completed, a Viewer and a guest see only reviewed languages (and an assigned reviewer his own), a stored preference reads as English, the mark and the hiding can be switched off (`test_menu`) | P1 |
| TC-070 | Integration | Bulk workflow with sample inspection | The size of the sample follows the settings, the sample is spread over the subgroups and reproducible, readiness names what stops each Draft, bulk edit sets a value on every Draft with its own audit entry and refuses unknown fields and other people's Drafts, a bulk domain sign-off needs a sample and gives each code its own sign-off, only a holder of the domain signs, a small batch needs no sample, a defect blocks the decision until the defective codes are sent back and a new sample is passed, a sample cannot be borrowed, reused or kept after the batch changed, a defect needs a note, bulk submit sends what is ready and reports the rest, the dossier holds codes, samples and audit, Viewers see nothing, the workbench works end to end and is translated, and every list with a checkbox per row has a header box that selects them all (`test_bulk_workflow`, `test_select_all`) | P1 |
| TC-071 | System | First start on a new machine | `scripts/first_start.py` lists its six steps from any folder, changes nothing with `--dry-run`, honours `--port` and `--no-admin`; a real run on a clean copy (environment, packages, database, first Administrator, second run) was done by hand (`test_first_start`) | P2 |
| TC-072 | System | Release documents as PDF | The Markdown reader finds every kind of block, inline markup becomes styles, every character of the documents can be drawn (a new symbol needs a word), the four files carry the version in their names, the full documentation has a contents list and appendices, the user manual is built for real (`test_docs_pdf`) | P2 |
| TC-073 | System | Design showcase | The slide model refuses a text that overflows its box, both decks build from placeholder pictures with every picture described, the demo database and its two demo-only routes work and the application itself has none of them (`test_showcase`) | P2 |
| TC-074 | System | Identity | The long name, the owner line and the logo are on every title page, the guide names the same owner, the logo files exist and are drawn, the menu bar and the login page show the logo (`test_branding`) | P2 |
| TC-075 | System | Hand-over to the team repository | The audit finds a planted account name, key, `.env`, data file, personal path, stray address, wrong version and missing release file and passes a clean tree; the export is one commit on `main` by the named author with the annotated tag; a push without the address and the confirmation is refused (`test_handover`) | P2 |
| TC-076 | Integration | The mapping and its three approvals | The seed workbook loads once into an empty table, is consistent (unique numbers, the Hub rows in the Hub range, the four Rotor gaps numbered) and a bad one is refused as a whole; a new row takes effect only after the StCd Owner, the Chief Engineer and an Administrator have approved, two are not enough, one rejection (with a reason) closes the request, only the three roles decide and each once, the requester cannot decide, a decision asks for the password, the requester can withdraw, a Viewer neither reads nor proposes (`test_mapping`) | P1 |
| TC-077 | Integration | What the import takes from the mapping | Cause and directive become the remedy text, the mapping gives the value of a delay the program sets with a parameter and a time in the program wins, the header legacy number must be the row's, a row that is only proposed is used with a warning, a rejected row or one of the other family is as good as none, a title that does not say what the German name says is flagged and never blocks, a code whose row is gone keeps its values (`test_st_mapping_rules`, `test_st_no_assumptions`, `test_st_category_and_draft_delete`) | P1 |
| TC-078 | Integration | Checks of a request | Every wrong value is named and makes no request (type, counter, numbers, delays, access levels, completeness, the controller of the number range), numbers stay unique, a change, a confirmation and a rejection work on stored rows, a row changed in between makes the older request unusable, the numbers of an issued row cannot change (`test_mapping`) | P1 |
| TC-080 | Integration | Filters with several values | The helpers read lists, repeats and comma-joined strings; the mapping, its requests, the legacy mapping and the Status Codes list (lifecycle state, category, platform) take several values by repeated parameter and by comma-joined string, a wrong value is refused, the page shows the chosen boxes ticked and a summary of them, a saved search keeps several values and comes back ticked, a code on two chosen platforms is one row (`test_multi_select`) | P2 |
| TC-079 | Integration | The workbook and the pages | The export is the layout the upload reads and compares as unchanged, a workbook makes one request with the new and the different rows, a wrong row names its place and requests nothing, a formula is never written, the pages show the mapping, the requests and the three places, the form posts make and decide requests, the menu counts the requests that wait, *Show all* gives one page with every row, an old database gets the page that names the two commands, the sign-off sits below the changes (`test_mapping`) | P2 |
| TC-069 | Integration | Connections between status codes | A negated active flag in a set condition is a cause and a plain one a precondition, the real programs name their cause and repeat code, one code shows what it depends on and what depends on it with the chain of causes, the hierarchy puts the cause on top with the codes it suppresses below, escalation targets say which are outside the catalogue, what looks wrong is listed (unknown and deprecated causes, loops), Main and Hub are separated, the code page and the overview show the connections, a Viewer does not, the API returns both views and refuses a bad controller, the menu offers it to the working roles only, and an imported program brings its cause and repeat code (`test_connections`) | P1 |
| TC-068 | Integration | Language impact of a change of the vocabulary | A new term tells the StCd Owner that all 18 languages need attention, an assigned reviewer gets the notice and nobody else, a term kept in English touches no language, a changed term and an approved translation are reported again, a failing notice never undoes the change, the notice shows on the Notices page, nothing is sent while the confidence check is current, changed shipped text is announced once per change and a further change again, a changed nomenclature is named, the deployment command reports and notifies, and the server start and both installers run the check (`test_translation_impact`) | P1 |
| TC-067 | Integration | Approval of new and changed translations; confidence check | A reviewed language has nothing pending until a string changes, a Viewer reads a changed string in English while the approved ones stay in the language and the working roles see the new text, a language never reviewed stays hidden, a follow-up review lists and requires only the new and changed strings, an accepted or rejected proposal is approved and an undecided one is not, the colour intervals run from red (≤ 50 %) to green (> 95 %), the overview shows the percentage of every language in its colour, the record holds a confidence and the findings of every language, a changed string or a changed nomenclature must get a verdict before the record is current, and a test fails while the text or the nomenclature changed without the check (`test_translation_approval`) | P1 |
| TC-066 | Integration | Baseline and package | A Release exports every code valid at its time (not only its own items), an earlier Release keeps its smaller baseline, *changes only* gives the delta, the baseline narrows to a platform and a controller, the summary counts by controller and platform, an unpublished Release previews its baseline, the package holds every language for every access level with one file per format, its manifest lists every file with a matching SHA-256 and the coverage per language, it narrows to platform and controller, everybody downloads what is released and only the StCd Owner and the Administrator what is not (working set, unpublished Release), invalid choices and unpublished Releases are refused, readiness shows the missing translations, the Release page offers it and the job is audited (`test_baseline_and_packages`) | P1 |
| TC-065 | Integration | The words around an export | A PDF in French prints its title page, digest note, column headings, footer and banner in French and leaves the data alone, English and no language keep the English text, every word exists in every language, a placeholder survives (`test_export_language`) | P2 |

## 8a. v4 Test Suites

| Module (`tests/…`) | Cases | Requirements |
|---|---|---|
| `integration/test_step_up_and_delegation.py` | 16 | FR-125, FR-126, SEC-026, BR-017, BR-022 |
| `integration/test_content_integrity.py` | 16 | FR-090 … FR-094, FR-109, FR-131, FR-141 |
| `integration/test_review_aids.py` | 17 | FR-124, FR-127 … FR-130 |
| `integration/test_sla_and_notifications.py` | 16 | FR-120 … FR-123 |
| `integration/test_publication.py` | 25 | FR-100 … FR-111, BR-016, BR-018, BR-021 |
| `integration/test_import_toolkit.py` | 20 | FR-048i … FR-048n |
| `integration/test_st_import.py` | 29 | FR-048o … FR-048w, BR-023, SEC-031 |
| `integration/test_roles_and_languages.py` | 19 | FR-156, FR-157, BR-024, SEC-032 |
| `integration/test_user_administration.py` | 10 | FR-158, BR-025, SEC-032, AUD-076 |
| `integration/test_withdraw_and_reimport.py` | 11 | FR-159, FR-160, FR-048x, BR-026 |
| `integration/test_audit_chain_and_ops.py` | 27 | FR-150 … FR-153, AUD-072 … AUD-075, SEC-029 |
| `integration/test_schema_upgrade.py` | 16 | upgrade, AUD-074 back-fill, BR-016, D-06 |
| `integration/test_prg_idx_and_user_groups.py` | 9 | schema v4.1: PrgIdx_GUi, Main/Hub fields, user-group levels (no FR yet) |
| `integration/test_integrations_and_reports.py` | 32 | FR-140 … FR-147, SEC-027, SEC-028 |
| `integration/test_search_and_help.py` | 16 | FR-148, FR-154 |
| `system/test_route_inventory.py` | 8 | SEC-010, FR-081 |
| `system/test_i18n.py`, `system/test_accessibility.py` | 12 + 8 | FR-155, FR-167, NFR-010 |
| `system/test_multiprocess.py` | 4 | NFR-009 |
| `system/test_deploy_artifacts.py` | 22 | NFR-013, NFR-014 |
| `system/test_docs_consistency.py` | 17 | TC-052 |
| `system/test_translations_doc.py` | 8 | FR-161 |
| `integration/test_email_and_windows_signin.py` | 16 | FR-162, FR-163, SEC-033 |
| `integration/test_translation_review.py` | 14 | FR-164, AUD-077 |
| `integration/test_pdf_scripts.py` | 9 | FR-165, FR-157 |
| `integration/test_terminology.py` | 13 | FR-166, BR-018, AUD-077, SEC-010 |
| `system/test_windows_gateway.py` | 6 | FR-163, SEC-033 |
| `integration/test_generated_fields.py` | 12 | FR-168, FR-048o, FR-025, FR-032 |
| `integration/test_menu.py` | 14 | FR-169, FR-170, SEC-010, NFR-010 |
| `integration/test_export_language.py` | 4 | FR-171, FR-165, FR-110, FR-045 |

The authoritative, always-current counts are in `24-test-report.md` (generated).

**Shared fixtures (v4).** `StepUpClient` answers the password prompt for the acting user so the many tests about *other* behaviour do not each repeat it (`raw_client` / `no_step_up=True` for the tests about the prompt itself); `file_app` is an application on a real SQLite file (background import, backups, upgrade, multi-process); every `app` gets its own instance directory (attachments, import files, the audit anchor); `CSCM_TEST_ORDER` reorders the run and `CSCM_TEST_DB=file` puts the whole suite on a file database. A frozen copy of the v3 schema (`fixtures/schema_d6f8b0c2e4a3.sql`) is the upgrade source.

## 9. Test Environments

Local, CI, staging, production, all on-premises per the deployment constraint. CI is defined for the internal Git server (`.gitea/workflows/ci.yml`, `.gitlab-ci.yml`, both calling `scripts/ci.py`).

## 10. Definition of "Test Complete" for a Release

All P1 cases pass in all three verification runs (§11), coverage threshold met, the five static gates clean, every defined requirement accounted for (§12), the documentation consistency test green, security checklist clean, at least one full UAT pass signed off.

## 11. Verification Runs: Three Methodologies *(v4)*

A change is verified three times, each in a way that can expose a different class of defect. `python scripts/generate_test_report.py [options]` runs one methodology, appends it to `artifacts/test-run-history.json` and regenerates `24-test-report.md`.

| # | Methodology | Command | What it can catch that the others cannot |
|---|---|---|---|
| 1 | **Sequential functional run + static gates.** The complete suite in file order with line coverage, then `black`, `ruff`, `mypy`, `bandit`, `pip-audit`; the load tests run afterwards without coverage tracing. | `scripts/generate_test_report.py` | Functional regressions, type errors, insecure constructs, vulnerable runtime packages, coverage loss |
| 2 | **Order-independence and property testing.** The same suite in a *reversed* or *shuffled* order (seeded, reproducible), including the `schemathesis` / `hypothesis` tests that generate requests from the OpenAPI contract. | `scripts/generate_test_report.py --order reverse` and `--order shuffle:<seed>` | Hidden coupling between tests, leaked global state (rate limiter, caches, instance files), contract violations on inputs nobody wrote by hand |
| 3 | **Real database file and real processes.** Every test on a SQLite *file* in WAL mode instead of memory; inside the suite, two Waitress processes against one file, a background import thread, the upgrade of a frozen v3 database, the installer dry runs and the production entry point. | `scripts/generate_test_report.py --db file` | Locking and visibility problems that only appear with several connections or processes, migration and upgrade defects, packaging defects, file-handling and path errors |

Additionally, `scripts/ci.py` (CI) runs methodology 1 plus the PostgreSQL ratchet, and `--fast` stops at the first failure for a developer's inner loop.

## 12. Requirement Accounting and Documentation Checks *(v4)*

`24-test-report.md` §6a states, for every requirement id *defined* in the specification (FR, NFR, BR in `03-srs.md`, SEC in `11-security-architecture.md`, AUD in `12-audit-compliance.md`), whether it is cited by a test, covered per the traceability matrix, or marked there as out of scope or needing a person. **No id may be left unaccounted for.** `tests/system/test_docs_consistency.py` additionally fails when: the endpoint table of `09-api-specification.md` differs from the code; table, trigger or operation counts quoted in the documents differ from the database or the contract; the application can write an audit action code that `12-audit-compliance.md` does not list; a term the help content defines is missing from the glossary; an id cited in a document is not defined anywhere; a link between documents points to a file or heading that does not exist; or a document set version differs between the index and the documents.

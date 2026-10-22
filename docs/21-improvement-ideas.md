# 21. Improvement Ideas — CSCM Tool

Ideas for making the Controller Status Code Management Tool more useful, safer and easier to run, collected while building, reviewing and testing it (2026-10-21). Everything here is **beyond the Phase 1 scope** in `03-srs.md`: Phase 1 is implemented and traced in [20-traceability-matrix.md](20-traceability-matrix.md). Nothing below is committed work; it is an input to backlog grooming.

**How to read this document**

- **Priority** reflects value to the wind-turbine controls organisation weighed against risk and cost, not effort alone:
  - 🔴 **HIGH** — closes a real risk or a gap that will hurt soon after go-live, or unlocks the core value proposition (trustworthy catalogue → manuals/SCADA). Start these first.
  - 🟠 **MEDIUM** — clear value, can follow once the system is in production use.
  - 🟢 **LOW** — nice to have, speculative, or depends on decisions not yet made.
- **Effort**: S ≈ days, M ≈ 1–2 sprints, L ≈ 3+ sprints (same scale as `16-mvp-roadmap.md` §7).
- **Epic**: an existing epic from `17-implementation-backlog.md` to extend, or a **new epic** proposed in §6.
- Constraint carried over from the project: **everything stays on-premises** — no cloud service, no external e-mail/SMS provider, no telemetry leaving the network (`11-security-architecture.md` §12). Ideas that need mail use the organisation's own SMTP relay.
- Items marked **(observed)** come from something actually seen in the code or test results, not from speculation.

---

## 1. Priority at a glance

| ID | Idea | Priority | Effort | Epic |
|---|---|---|---|---|
| I-01 | Optimistic concurrency on Draft edits (lost-update protection) | 🔴 HIGH | S | EPIC-02 → new EPIC-17 |
| I-02 | Manual-ready PDF and export profiles (PDF currently truncates cells) **(observed)** | 🔴 HIGH | M | new EPIC-20 |
| I-03 | Audience-scoped publication from the eight access fields | 🔴 HIGH | M | new EPIC-20 |
| I-04 | Referential integrity for "status code for repeated error" and where-used report | 🔴 HIGH | M | new EPIC-17 |
| I-05 | Migration toolkit: import preview, update mode, template, reconciliation | 🔴 HIGH | M | EPIC-14 (extend) |
| I-06 | Release integrity: checksums, signed manifest, release notes, release-to-release diff | 🔴 HIGH | M | new EPIC-18 |
| I-07 | Software-version binding and applicability matrix | 🔴 HIGH | M | new EPIC-18 |
| I-08 | Workflow SLA tracking, aging queues and internal reminders | 🔴 HIGH | M | new EPIC-19 |
| I-09 | Automated backups with verified restore | 🔴 HIGH | S | EPIC-13 → new EPIC-25 |
| I-10 | Success-metrics dashboard (the KPIs the business case promises) | 🟠 MEDIUM | M | new EPIC-19 |
| I-11 | Change sets: group CRs that ship with one controller software release | 🟠 MEDIUM | L | EPIC-04 (extend) |
| I-12 | Duplicate and near-duplicate detection when authoring or importing | 🟠 MEDIUM | M | EPIC-02, EPIC-14 |
| I-13 | Evidence and attachments on change requests (test reports, design notes) | 🟠 MEDIUM | M | new EPIC-23 |
| I-14 | Remedy / troubleshooting text, affected component, standard references | 🟠 MEDIUM | M | new EPIC-23 |
| I-15 | Multilingual titles and descriptions with translation workflow | 🟠 MEDIUM (HIGH if manuals are multilingual) | L | new EPIC-22 |
| I-16 | Delegation and out-of-office cover for decision makers | 🟠 MEDIUM | M | EPIC-04, new EPIC-19 |
| I-17 | Step-up re-authentication for approvals and publish | 🟠 MEDIUM | S | EPIC-12 |
| I-18 | Tamper-evident (hash-chained) audit log and retention job | 🟠 MEDIUM | M | EPIC-10 |
| I-19 | Catalogue health report and number-range capacity forecast | 🟠 MEDIUM | S | EPIC-16, EPIC-10 |
| I-20 | Persistent login rate-limit state and multi-process readiness **(observed)** | 🟠 MEDIUM | S | EPIC-12, EPIC-13 |
| I-21 | Observability: metrics endpoint, readiness probe, log shipping (JSON request logs already exist) | 🟠 MEDIUM | M | EPIC-13 → new EPIC-25 |
| I-22 | Accessibility (WCAG 2.1 AA) and German UI | 🟠 MEDIUM | M | EPIC-15 |
| I-23 | Field-level review comments and review checklists | 🟠 MEDIUM | M | EPIC-04 |
| I-24 | Offline field-lookup bundle for service technicians | 🟠 MEDIUM | M | new EPIC-18 |
| I-25 | Platform variants: create a 4XM variant from a 3XM code | 🟠 MEDIUM | S | EPIC-02 |
| I-26 | Saved searches, column chooser, shareable filter links | 🟢 LOW | S | EPIC-05 |
| I-27 | Planned effective / deprecation dates | 🟢 LOW | S | EPIC-06, EPIC-08 |
| I-28 | Fleet feedback: occurrence statistics from SCADA | 🟢 LOW | L | new EPIC-24 |
| I-29 | Webhooks / machine API tokens / change feed (Phase 2–3 items) | 🟢 LOW | M | EPIC-11 |
| I-30 | Reviewer workload balancing and auto-assignment | 🟢 LOW | S | EPIC-04 |
| I-31 | SQLite FTS5 search and typo tolerance | 🟢 LOW | S | EPIC-05 |
| I-32 | Background import jobs with progress | 🟢 LOW | S | EPIC-14 |
| I-33 | On-prem packaging, installer and CI pipeline | 🟢 LOW | M | new EPIC-25 |
| I-34 | PostgreSQL readiness test run | 🟢 LOW | M | EPIC-13 (Phase 3) |
| I-35 | In-app help, glossary tooltips, per-role quick start | 🟢 LOW | S | EPIC-15 |

---

## 2. 🔴 HIGH priority

### I-01 · Optimistic concurrency on Draft edits — 🔴 HIGH · S
**Problem (observed).** The API contract advertises an `expected_updated_at` field to detect conflicting edits, but the schema has no `updated_at`/version column, so it is accepted and ignored (`StatusCodeService.update_draft` says so in its docstring). Two people editing the same Draft — the author and an Administrator, who may both edit — silently overwrite each other. The legacy tool's "form loses data" complaint shows users already distrust data entry; a lost update is worse.
**Idea.** Add a `row_version` integer to `status_code_revision`; the edit form carries it; a save with a stale version returns 409 and re-shows the user's entries next to the current values (reusing the no-data-loss form behaviour of NFR-007a).
**Value.** Prevents silent loss of engineering work. **Epic:** EPIC-02 (FEAT on Draft editing), grouped into new EPIC-17.

### I-02 · Manual-ready PDF and export profiles — 🔴 HIGH · M
**Problem (observed).** The PDF exporter cuts every cell to 24 characters and squeezes ~40 columns onto A4 landscape (`app/export/pdf_exporter.py`, `_MAX_CELL_CHARS = 24`). A truncated description in a document that feeds technical manuals is misleading data, and the CSV/XLSX exports carry every internal column whether the consumer needs it or not.
**Idea.** Named *export profiles*: e.g. **Service manual** (identifier, title, description, category, set/reset delay, resolution text), **SCADA tag list** (identifier, node, category, alarm flag), **Customer list**. Each profile fixes the column set, order, header labels and language, and the PDF uses wrapped multi-line cells with a repeating header and a per-release title page (release name, version, effective date, checksum — see I-06). Profiles are Administrator-managed data, not code.
**Value.** The exports become directly usable by Technical Publications — the exit criterion in `16-mvp-roadmap.md` — instead of being re-edited by hand. **Epic:** new EPIC-20.

### I-03 · Audience-scoped publication — 🔴 HIGH · M
**Problem.** Each code carries eight independent audience-access values (Development, Sales, TCC, Service, Turbine Operator Package, Grid Operator, Service Partner, Customer), yet every export contains every released code regardless of who will read it. Handing the Customer or Service-Partner audience the full catalogue defeats the purpose of the access fields.
**Idea.** Export (and later API) parameter `audience=customer|service_partner|…` that includes only the codes whose access value for that audience grants visibility, and omits the other audiences' columns. Because the Administrator's sign-off confirms these values (BR-012), the filter can be trusted.
**Dependency / blocker.** The meaning of the value `Covert` across vocabularies is still unconfirmed (`06-data-dictionary.md` §9d). Resolve that first, then encode the visibility rule per vocabulary as data.
**Value.** Prevents accidental disclosure of internal fault information to customers and partners. **Epic:** new EPIC-20.

### I-04 · Referential integrity for repeated-error references and a where-used report — 🔴 HIGH · M
**Problem (observed).** `status_code_for_repeated_error` is deliberately an opaque number, not a foreign key (data dictionary §2b), so a code can point at a number that does not exist, or at one that is later deprecated. Deprecating or archiving a code today gives no warning that other codes depend on it (`superseded_by_status_code_id` has the same blind spot).
**Idea.** Soft validation: warn (not block) at save and at submit when the referenced number is unknown, deprecated or archived; a **Where-used** panel on the code detail page listing every code that references it; deprecation requests show the dependants and require the requester to acknowledge them. Keep it soft because the referenced pool may include external escalation numbers (the form already notes this).
**Value.** Avoids dangling references in released catalogues, a classic source of wrong troubleshooting guidance. **Epic:** EPIC-08 (deprecation) + EPIC-02, grouped in new EPIC-17.

### I-05 · Migration toolkit for the legacy library — 🔴 HIGH · M
**Problem.** The business must move roughly 1,160 legacy rows (897 Main + 264 Hub Controller) through the governed workflow. Today the import creates new Drafts only: there is no preview, no way to correct a row and re-upload, no template, and no way to see how much is still unmigrated.
**Idea.** (a) **Dry-run**: validate and show per-row results before creating anything; (b) **downloadable template** with the exact headers and lookup codes; (c) **update mode** keyed on `legacy_reference_number` — a changed row opens a new revision of the already-imported code instead of a duplicate; (d) a **reconciliation report**: legacy rows imported, in review, released, still missing; (e) clearer error report (row, column, value, fix hint) in XLSX.
**Value.** The migration is the largest one-time effort; these features turn weeks of manual re-entry into iterative cleanups. **Epic:** EPIC-14 (extend).

### I-06 · Release integrity, release notes and release-to-release diff — 🔴 HIGH · M
**Problem.** A published Release is immutable in the database, but a file exported from it carries no proof of what it is. Downstream manuals and SCADA tag lists cannot tell whether a CSV was edited after export, and there is no automatic "what changed since the last release" document — the thing a Technical Publications team needs most.
**Idea.** Every export of a Release is accompanied by a manifest (release name, version, effective date, row count, SHA-256 of each file, generation timestamp, generating user); optionally signed with an on-prem key. A **release notes** page lists added / changed (field-level diff, reusing the revision diff) / deprecated codes against the previous Release, available as Markdown, PDF and CSV.
**Value.** Tamper evidence for artefacts leaving the system, and the change log that drives manual updates. **Epic:** new EPIC-18.

### I-07 · Software-version binding and applicability matrix — 🔴 HIGH · M
**Problem.** The open item in the data dictionary (`software_version` on the revision or on the Release) is a real modelling gap: a status code only means something for a given controller software version, and the legacy tool uses the version as its main filter. Today the field is a free-text note.
**Idea.** Decide the model with the business, then: a `controller_software_version` lookup; each Release targets one or more versions; each revision declares the version range in which it applies (from/to); a matrix view "which codes exist in version X / what changed between X and Y"; exports per version.
**Value.** Answers the question service engineers ask first — "does this code exist on the software in front of me?" **Epic:** new EPIC-18 (resolves the open item in `06-data-dictionary.md` §2).

### I-08 · Workflow SLA tracking and reminders — 🔴 HIGH · M
**Problem.** The business case promises a median of ≤ 7 business days from submission to approval and ≤ 3 days for cross-domain sign-off (`01-executive-summary.md` §4), but nothing measures or nudges toward it. A CR waiting for a Reviewer who is on leave is invisible until someone asks.
**Idea.** Each queue entry shows its age and turns amber/red at configurable thresholds; a daily internal reminder (in-app banner and optional e-mail through the organisation's own SMTP relay) to whoever holds the next decision; Administrator view "stalled CRs" with one-click reassignment (FR-039 already exists).
**Value.** Keeps the governance process from becoming the bottleneck the risk table in the roadmap warns about. **Epic:** new EPIC-19.

### I-09 · Automated backups with a verified restore — 🔴 HIGH · S
**Problem.** The system of record is one SQLite file. The full-database export exists but is a manual Administrator action; nothing checks that a backup can actually be restored.
**Idea.** A scheduled job (Windows Task Scheduler / systemd timer, shipped as a documented script) that uses the SQLite online-backup API, stores N generations on a second volume, runs `PRAGMA integrity_check` and a restore smoke test into a temp database, and writes a result file the health endpoint reads. A restore runbook with a quarterly drill.
**Value.** Protects the single most important asset; cheap to build. **Epic:** EPIC-13, grouped into new EPIC-25.

---

## 3. 🟠 MEDIUM priority

| ID | Idea | Detail | Epic |
|---|---|---|---|
| **I-10** | **Success-metrics dashboard** (M) | Turn the KPIs of `01-executive-summary.md` §4 into live tiles for the Administrator and Chief Engineer: median time to Approved, cross-domain turnaround, % of Released codes with a complete audit trail, queue age distribution, codes with unknown owner. Computed from the audit log and CR timestamps already stored. | new EPIC-19 |
| **I-11** | **Change sets** (L) | Engineers change dozens of codes per controller software release. A *change set* groups CRs for one release train so reviewers see the whole package, and the Chief Engineer can decide it in one sitting — each CR still gets its own three independent decisions (no governance shortcut), only the presentation and queueing are bundled. | EPIC-04 |
| **I-12** | **Duplicate and near-duplicate detection** (M) | When creating or importing, show existing codes with the same title or a high text similarity in the same subgroup ("did you mean to revise StCd-01234?"). Warning, not a block. Targets catalogue bloat during the 1,160-row migration. | EPIC-02, EPIC-14 |
| **I-13** | **Evidence and attachments on CRs** (M) | Attach test reports, simulation results, design notes or a safety assessment to a CR; Reviewers and the Chief Engineer see them at decision time; stored outside the web root with type/size allow-listing (SEC-024). The `SAFETY` engineering domain exists already — evidence is how its sign-off becomes auditable. | new EPIC-23 |
| **I-14** | **Remedy text, affected component, standard references** (M) | Optional fields: recommended action for service staff, affected subsystem/component, related codes, references to applicable standards. Turns the catalogue from a list of names into usable troubleshooting content for the manuals. Domain-owned fields follow the existing Cross-Domain Sign-Off rules. | new EPIC-23 |
| **I-15** | **Multilingual content** (L) | Title/description per language (at least German and English) with a translation status (missing / draft / approved) and per-language exports. Becomes **HIGH** if the manuals are published in more than one language — please confirm with Technical Publications. Translations get their own light review, not the three-decision cycle for the source text. | new EPIC-22 |
| **I-16** | **Delegation and out-of-office cover** (M) | A Reviewer, Administrator or Chief Engineer names a delegate for a date range. The delegate acts *as themselves* (audit shows both); segregation-of-duties rules still apply to the delegate. Prevents single points of failure noted as assumption A-007. | EPIC-04, new EPIC-19 |
| **I-17** | **Step-up re-authentication** (S) | Re-enter the password before Reviewer/Admin sign-off, Chief Engineer approval, publish, and full-database export. Makes the approval an affirmative, attributable act and limits damage from an unattended session. | EPIC-12 |
| **I-18** | **Tamper-evident audit log and retention job** (M) | Each audit row stores the hash of the previous row, so removal or reordering is detectable even by someone with database access (the append-only triggers already stop in-application edits). A verification command and a scheduled check. Plus the 7-year retention job that archives, never deletes, old entries. | EPIC-10 |
| **I-19** | **Catalogue health report and capacity forecast** (S) | Report: codes missing optional-but-expected data, inconsistent combinations (e.g. category `INFO` with an alarm flag), unused numbers, and **how full each subgroup's number band is** with an alert before a band is exhausted (allocation raises an error only when it is already full). | EPIC-16, EPIC-10 |
| **I-20** | **Persistent rate-limit state / multi-process readiness** (S) **(observed)** | The login rate limiter is process-local memory (`app/auth/rate_limit.py`); a restart clears it and several worker processes would each keep their own counters. Store the counters in the database (account lockout already is). Also document and test running with several waitress workers. | EPIC-12, EPIC-13 |
| **I-21** | **Observability** (M) | Structured JSON request logs with the request id now exist (`app/logging_config.py`); still open: a readiness endpoint that checks the database and the last backup (I-09), a Prometheus-style metrics endpoint on the internal network (request rates, latencies, queue sizes, lock waits). Fits the on-prem rule. | EPIC-13 → new EPIC-25 |
| **I-22** | **Accessibility and German UI** (M) | WCAG 2.1 AA review (keyboard navigation, focus order, colour contrast, form error association), and German translations of the UI chrome (the Obsidian vault already shows German-language users). The spec excludes localisation from the MVP; this is the follow-up. | EPIC-15 |
| **I-23** | **Field-level review comments and checklists** (M) | Reviewers comment on a specific field in the diff and the author sees them inline on the Draft; a configurable review checklist per Functional System Group ("delay values checked against the control logic", …) recorded with the sign-off. | EPIC-04 |
| **I-24** | **Offline field-lookup bundle** (M) | A read-only, self-contained bundle (single HTML file with embedded JSON, or a small SQLite file) generated from each Release so service technicians can search codes at the turbine without connectivity. No server needed; signed with the release manifest (I-06). Replaces the mobile/tablet scope the roadmap defers. | new EPIC-18 |
| **I-25** | **Platform variants** (S) | The schema already has `platform_variant_of_status_code_id`; add "create 4XM variant of this 3XM code" which copies the revision, links the two, and shows the family on both detail pages. | EPIC-02 |

---

## 4. 🟢 LOW priority

| ID | Idea | Detail | Epic |
|---|---|---|---|
| **I-26** | Saved searches, column chooser, shareable filter links (S) | Remember filters, choose visible columns, put the filter in the URL so a link in a ticket reproduces the view. | EPIC-05 |
| **I-27** | Planned effective and deprecation dates (S) | Stamp a *planned* date on an Approved revision or a deprecation; the release builder warns when a candidate's planned date is in the future. | EPIC-06, EPIC-08 |
| **I-28** | Fleet feedback loop (L) | Import anonymised occurrence counts per code from SCADA/CMS (internal network) to show which codes never fire (candidates for deprecation) and which fire most (candidates for better remedy text). Needs an agreed data feed and is the natural Phase 3 integration. | new EPIC-24 |
| **I-29** | Machine API extras (M) | Scoped API tokens (already Phase 2), a "changes since" feed with ETags, webhooks on Release publish (Phase 3, internal network only). | EPIC-11 |
| **I-30** | Reviewer workload balancing (S) | Suggest or auto-assign the Reviewer with the fewest open CRs, building on FR-039 assignment. | EPIC-04 |
| **I-31** | SQLite FTS5 search and typo tolerance (S) | The current substring search handles 20,000 revisions in ~50 ms; FTS5 ranking and "converter" ≈ "converte" tolerance only matter if the catalogue grows well beyond the target. | EPIC-05 |
| **I-32** | Background import jobs with progress (S) | Import runs inside the upload request today; a 1,000-row file is fine, a much larger one would time out. Move to a worker with a progress bar (the contract already describes asynchronous processing). | EPIC-14 |
| **I-33** | On-prem packaging, installer and CI (M) | A Windows service/systemd unit, an installer script that runs migrations and creates the first Administrator, and a CI pipeline on the internal Git server running `scripts/generate_test_report.py` on every push. | new EPIC-25 |
| **I-34** | PostgreSQL readiness run (M) | Run the existing suite against PostgreSQL in CI to keep the Phase 3 migration option honest (the repository pattern is in place; SQLite-specific triggers and `BEGIN IMMEDIATE` are the parts to port). | EPIC-13 |
| **I-35** | In-app help (S) | Glossary tooltips on lifecycle states and roles, a "what happens next" hint on each CR state, a per-role quick start linking to the user manual. | EPIC-15 |

---

## 5. Quick wins (≤ 2 days each, no new epic)

These are small, safe and visible; good for a first sprint after go-live.

1. **PDF export wrapping** (part of I-02) — stop truncating text; fixes a data-quality problem today.
2. **Persist rate-limit counters** (I-20).
3. **Backup script + restore runbook** (I-09).
4. **Queue-age column and colour** on Review / Approval queues (first slice of I-08).
5. **Capacity hint on the New Status Code form**: "StCd-01042 of 1000–1099 (58 numbers left in this subgroup)" using the existing preview endpoint (first slice of I-19).
6. **Warn on referenced-but-unknown "status code for repeated error"** (first slice of I-04).
7. **Template CSV download** on the Library Import page (first slice of I-05).

---

## 6. Proposed new epics

Numbering continues from EPIC-16 in `17-implementation-backlog.md`. Sizing uses the roadmap scale (S ≈ 1 sprint, M ≈ 2, L ≈ 3–4).

| Epic | Name | Contains | Size | Suggested phase |
|---|---|---|---|---|
| **EPIC-17** | Concurrency & Data Integrity | I-01, I-04, I-12 | M | Phase 2 start |
| **EPIC-18** | Release Integrity & Software-Version Traceability | I-06, I-07, I-24 | L | Phase 2 start (I-06/I-07 are HIGH) |
| **EPIC-19** | Workflow SLAs, Notifications & Metrics | I-08, I-10, I-16 | M | Phase 2 start |
| **EPIC-20** | Audience-Scoped & Profile-Based Publication | I-02, I-03 | M | Phase 2 start (blocked on the `Covert` question for I-03) |
| **EPIC-22** | Multilingual Content | I-15 | L | Decide after confirming manual languages |
| **EPIC-23** | Knowledge Enrichment & Evidence | I-13, I-14 | M | Phase 2 |
| **EPIC-24** | Fleet Feedback Loop | I-28 | L | Phase 3 |
| **EPIC-25** | Operations & Resilience | I-09, I-21, I-33 (and I-20) | M | Before go-live for I-09; rest Phase 2 |

(EPIC-21 is intentionally unused so numbers 17–20 stay together for the near-term work.)

### Existing epics to extend

| Epic | Extension |
|---|---|
| EPIC-02 Data model & validation | I-01 (concurrency), I-12 (duplicates), I-25 (variants) |
| EPIC-04 Dual review & approval | I-11 (change sets), I-16 (delegation), I-23 (field comments), I-30 (balancing) |
| EPIC-05 Search & history | I-26 (saved searches), I-31 (FTS5) |
| EPIC-06 / EPIC-08 Release / deprecation | I-27 (planned dates), I-04 (dependants on deprecation) |
| EPIC-10 Audit | I-18 (hash chain, retention), I-19 (health report) |
| EPIC-11 API | I-29 (tokens, change feed, webhooks) |
| EPIC-12 Security | I-17 (step-up), I-20 (persistent limits) |
| EPIC-13 Non-functional | I-09, I-21, I-34 |
| EPIC-14 Library import | I-05 (toolkit), I-12, I-32 |
| EPIC-15 UI & shell | I-22 (a11y, German), I-35 (help) |
| EPIC-16 Subgroup/group admin | I-19 (capacity forecast) |

---

## 7. Decisions needed from the business before work starts

| Question | Unblocks |
|---|---|
| What does `Covert` mean in each audience vocabulary, and which values permit an audience to *see* a code? | I-03 |
| Does `software_version` belong to the revision, the Release, or both — and is it a single version or a range? | I-07 |
| In which languages are the manuals and the SCADA texts published? | I-15 (HIGH vs. MEDIUM) |
| Is an internal SMTP relay available for reminders, or are in-app notices enough? | I-08, I-16 |
| Which evidence types does the `SAFETY` sign-off require? | I-13 |
| Is there an agreed data feed from SCADA/CMS for occurrence counts? | I-28 |
| Is an on-prem Git/CI server available? | I-33 |

---

## 8. Suggested sequencing

1. **Before go-live (small):** I-09 backups, I-01 concurrency, the PDF wrapping fix from I-02, I-20.
2. **First quarter in production:** EPIC-18 (I-06, I-07), EPIC-20 (I-02 profiles; I-03 once `Covert` is defined), I-05 migration toolkit (needed while the legacy library is moved), EPIC-19 SLA slices (I-08).
3. **Second quarter:** EPIC-17 remainder (I-04, I-12), I-11 change sets, I-13/I-14 enrichment, I-17, I-18, I-21.
4. **Later / on demand:** multilingual (I-15) as soon as the language question is answered, then the LOW items and the Phase 3 integrations.

# 21. Improvement Ideas — CSCM Tool

This document has two halves. **Part A** records the 36 improvement ideas collected on 2026-10-21 (I-01 … I-36) and what became of each: all 36 are **implemented** in v4 (2026-10-23), specified in `03-srs.md` §1.10–§1.15 and traced to automated tests in [20-traceability-matrix.md](20-traceability-matrix.md). **Part B** is the *new* list of improvements (I-37 onward) collected while building, testing and documenting v4 — each grounded in something observed in the code, the tests or the deployment, or in a decision still open. Nothing in Part B is committed work; it is an input to backlog grooming.

**How to read Part B**

- **Priority** reflects value to the wind-turbine controls organisation weighed against risk and cost: 🔴 **HIGH** closes a real risk or gap that will hurt soon after go-live; 🟠 **MEDIUM** has clear value once the system is in production use; 🟢 **LOW** is nice to have, speculative or depends on decisions not yet made.
- **Effort**: S ≈ days, M ≈ 1–2 sprints, L ≈ 3+ sprints (the scale of `16-mvp-roadmap.md` §7).
- Constraint carried over from the project: **everything stays on-premises** — no cloud service, no external e-mail/SMS provider, no telemetry leaving the network (`11-security-architecture.md` §12). Ideas that need an outside connection say so and are opt-in by design.
- Items marked **(observed)** come from something actually seen in the code, the tests or the deployment, not from speculation.

---

# Part A — The 36 ideas of 2026-10-21 and their outcome

## A.1 Status at a glance

| ID | Idea | Status | Requirements | Tests | Deviations from the idea as written |
|---|---|---|---|---|---|
| I-01 | Optimistic concurrency on Draft edits | ✅ implemented | FR-090, BR-019 | TC-039 | — |
| I-02 | Manual-ready PDF and export profiles | ✅ implemented | FR-100, FR-101 | TC-042 | PDF in every script since v4.7 (I-37, FR-165) |
| I-03 | Audience-scoped publication | ✅ implemented | FR-102, BR-016 | TC-042 | `Covert` = not visible until defined (D-02) |
| I-04 | Referential integrity and where-used | ✅ implemented | FR-091, FR-092 | TC-039 | soft warnings, never blocks (as proposed) |
| I-05 | Migration toolkit | ✅ implemented | FR-048i … FR-048m | TC-043 | — |
| I-06 | Release integrity, notes, diff | ✅ implemented | FR-103 … FR-105, SEC-030 | TC-042 | HMAC signature, not asymmetric (D-05, see I-39) |
| I-07 | Software-version binding and matrix | ✅ implemented | FR-106, FR-107, BR-021 | TC-042 | model decided: range per revision + Release targets (D-01) |
| I-08 | SLA tracking, aging queues, reminders | ✅ implemented | FR-120 … FR-122 | TC-041 | business days without holiday calendar (see I-40) |
| I-09 | Automated backups with verified restore | ✅ implemented | FR-150, NFR-012 | TC-044 | second volume / off-host copy is an operator task (see I-45) |
| I-10 | Success-metrics dashboard | ✅ implemented | FR-123 | TC-041, TC-046 | — |
| I-11 | Change sets | ✅ implemented | FR-124 | TC-040 | presentation and queueing only (as proposed) |
| I-12 | Duplicate and near-duplicate detection | ✅ implemented | FR-093 | TC-039, TC-043 | — |
| I-13 | Evidence and attachments | ✅ implemented | FR-130, SEC-024 | TC-040 | — |
| I-14 | Remedy text, component, standards | ✅ implemented | FR-131 | TC-039 | "Any" owner: never gates cross-domain sign-off |
| I-15 | Multilingual content | ✅ implemented | FR-110, FR-111, BR-018 | TC-042 | English + German only (D-03) |
| I-16 | Delegation and out-of-office cover | ✅ implemented | FR-125, BR-017 | TC-038 | decision actions only (D-08) |
| I-17 | Step-up re-authentication | ✅ implemented | FR-126, SEC-026, BR-022 | TC-038 | — |
| I-18 | Tamper-evident audit log, retention job | ✅ implemented | FR-151, AUD-072 … AUD-075 | TC-044 | — |
| I-19 | Catalogue health and capacity forecast | ✅ implemented | FR-140, FR-141 | TC-046, TC-039 | — |
| I-20 | Persistent rate-limit state | ✅ implemented | NFR-009 | TC-050 | proven with two real processes |
| I-21 | Observability | ✅ implemented | FR-152, FR-153, NFR-011 | TC-044 | — |
| I-22 | Accessibility and German UI | ✅ implemented | FR-155, NFR-010 | TC-049 | German and every other language cover the whole interface since v4.9 (I-38, FR-167) |
| I-23 | Field comments and review checklists | ✅ implemented | FR-127, FR-128 | TC-040 | — |
| I-24 | Offline field-lookup bundle | ✅ implemented | FR-108 | TC-042 | single HTML file (no SQLite variant) |
| I-25 | Platform variants | ✅ implemented | FR-094 | TC-039 | — |
| I-26 | Saved searches, columns, shareable links | ✅ implemented | FR-142 | TC-046 | — |
| I-27 | Planned effective / deprecation dates | ✅ implemented | FR-109 | TC-039 | warnings only |
| I-28 | Fleet feedback | ✅ implemented | FR-143 | TC-046 | file import (the agreed shape); no scheduled feed |
| I-29 | Tokens, change feed, webhooks | ✅ implemented | FR-144 … FR-146, SEC-027, SEC-028 | TC-046 | webhooks make a single attempt (see I-46) |
| I-30 | Reviewer balancing | ✅ implemented | FR-129 | TC-040 | — |
| I-31 | FTS5 search and typo tolerance | ✅ implemented | FR-148 | TC-047 | substring fallback without FTS5 |
| I-32 | Background imports with progress | ✅ implemented | FR-048n | TC-043 | a thread of the web process (see I-44) |
| I-33 | On-prem packaging, installer, CI | ✅ implemented | NFR-013 | TC-051 | not yet run on real servers (docs/20 §6) |
| I-34 | PostgreSQL readiness | ◐ **partly** | NFR-014 | TC-051 | inventory + ratchet + dialect guards; **no PostgreSQL run** (see I-41) |
| I-35 | In-app help | ✅ implemented | FR-154 | TC-047 | — |
| I-36 | Hub → Main Controller consolidation | ✅ implemented | FR-147, D-06 | TC-046 | see 25-hc-integration-concept.md for the open numbering proposal |

I-34 is the only idea delivered in part, and the table says so; everything else is complete as specified in 03-srs.md. The 21 new tables, 78 new API operations (one more changed: the full-database export became a POST) and 19 new screens are listed in 06 §13, 09 §7 and 10 §1.

## A.2 The business questions of the original list and how v4 answered them

| Question                                                            | Answer used (03-srs.md §6)                                                 | Still needs the business?                                |
| ------------------------------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------- |
| What does `Covert` mean; which values let an audience *see* a code? | Not visible; visibility is data on each value (D-02)                       | Yes — please define it; a data change, no release needed |
| Does `software_version` belong to the revision or the Release?      | Both: a range per revision and the versions a Release targets (D-01)       | Confirm                                                  |
| In which languages are manuals published?                           | English source, German first (D-03)                                        | Confirm; more languages are data plus translation work   |
| Is an internal SMTP relay available?                                | In-app notices are the mechanism, SMTP optional (D-04)                     | Yes — if mail is wanted, set `SMTP_*`                    |
| Which evidence does the `SAFETY` sign-off require?                  | Any allow-listed file type; no per-domain rule                             | Yes, if a rule is wanted                                 |
| Is there an agreed feed of occurrence counts?                       | File import with an agreed shape (`status_code_identifier`, `occurrences`) | Yes, for a scheduled feed                                |
| Is an on-prem Git/CI server available?                              | CI definitions for Gitea and GitLab are provided                           | Yes — which one                                          |

## A.3 Quick wins and sequencing of the original list — now moot

All seven quick wins and the four-step sequencing of the original document are delivered together in v4; the risk-reducing items (backups, concurrency, persistent rate limit, PDF wrapping) are covered by TC-044, TC-039, TC-050 and TC-042.

---

# Part B — New improvement ideas (I-37 …)

## B.1 Priority at a glance

| ID | Idea | Priority | Effort | Epic |
|---|---|---|---|---|
| I-37 | Unicode font for the PDF export **(observed)** — ✅ delivered in v4.7 (FR-165) | 🔴 HIGH | S | EPIC-20 |
| I-38 | Complete interface coverage in every language: flash messages, admin pages, service-layer sentences **(observed)** — ✅ delivered in v4.9 (FR-167); the text of the exports outside the catalogue is still English (26-translations.md §5) | 🔴 HIGH | M | EPIC-15 |
| I-39 | Asymmetric (Ed25519) manifest signatures and key rotation **(observed)** | 🟠 MEDIUM | M | EPIC-18, EPIC-12 |
| I-40 | Holiday calendar for business days **(observed)** — ✖ not needed (decision of 2026-10-24) | — | — | EPIC-19 |
| I-41 | Run and test on PostgreSQL (execute the port prepared by I-34) | 🟠 MEDIUM | L | EPIC-13 |
| I-42 | Git-linked status code library versions and tag proposals | 🟠 MEDIUM | L | new EPIC-26 |
| I-43 | Template-driven DOCX export (customer / brand templates) — ◐ the data side (complete baseline, platform and controller filter, package) is delivered in v4.10 (FR-173, FR-174); the Word output waits for the templates | 🟠 MEDIUM | L | EPIC-20 |
| I-44 | Import worker that survives a restart and can resume **(observed)** | 🟠 MEDIUM | M | EPIC-14 |
| I-45 | Backup replication and encryption: second volume, off-host copy | 🟠 MEDIUM | S | EPIC-25 |
| I-46 | Webhook retry with back-off and a dead-letter view **(observed)** | 🟠 MEDIUM | S | EPIC-11 |
| I-47 | Active Directory / ADFS authentication provider | 🟠 MEDIUM | L | EPIC-12 (Phase 2) |
| I-48 | Key custody helper: rotate, escrow and check the integrity keys **(observed)** | 🟠 MEDIUM | M | EPIC-25 |
| I-49 | Bulk revision as a change set (e.g. adjust one field across many codes) | 🟠 MEDIUM | M | EPIC-04 |
| I-50 | Pause the SLA clock while the request waits for its author | 🟢 LOW | S | EPIC-19 |
| I-51 | Alert rules and dashboards shipped with the metrics (Prometheus / Grafana files) | 🟢 LOW | S | EPIC-25 |
| I-52 | Audit-log export (CSV) and saved audit filters | 🟢 LOW | S | EPIC-10 |
| I-53 | Command palette and keyboard shortcuts | 🟢 LOW | S | EPIC-15 |
| I-54 | Translation memory and term consistency check | 🟢 LOW | M | EPIC-22 |
| I-55 | Description linter: style rules, title ≠ description, banned words | 🟢 LOW | S | EPIC-02 |
| I-56 | Customer read-only view with permalinks (needs a decision on FR-083) | 🟢 LOW | M | new EPIC-27 |
| I-57 | Mobile / tablet layout for field use | 🟢 LOW | M | EPIC-15 |
| I-58 | Token usage report and per-token rate limit | 🟢 LOW | S | EPIC-11 |
| I-59 | Stronger test techniques: mutation testing and state-machine property tests | 🟢 LOW | M | EPIC-13 |
| I-60 | Document-to-code links: show which exports and releases used a code's wording | 🟢 LOW | S | EPIC-18 |
| I-61 | Batch edit of imported Drafts: status category, platforms and audience access for the ticked codes of a change set — ✅ delivered in v4.13 (FR-180) | 🟠 MEDIUM | M | EPIC-14 |
| I-62 | Bulk submit for review and bulk cross-domain sign-off for a change set — ✅ delivered in v4.13 (FR-180) | 🟠 MEDIUM | M | EPIC-19 |
| I-63 | Re-import from the programs: show what changed against the catalogue (drift) and revise the codes | 🟠 MEDIUM | M | EPIC-14 |
| I-64 | Wire the parsed user-group levels, the remaining subsystem programs and the operating-mode mask from `import_source_item` into catalogue columns — ✅ delivered in v4.9.1 (FR-168) | 🟠 MEDIUM | M | EPIC-14 |
| I-65 | Per-program status category in the preview (derived from the alarm type, or set per program) — ✅ delivered in v4.13.2 (FR-181) | 🟢 LOW | S | EPIC-14 |

## B.2 🔴 HIGH priority

### I-37 · Unicode font for the PDF export — 🔴 HIGH · S
**Problem (observed).** The PDF exporter uses the built-in Latin-1 font; any character outside it (for example some typographic dashes and quotes, or text in a language beyond German) is replaced (`test_pdf_survives_characters_outside_latin_1` proves it does not crash, not that it is right). A German manual with an `€` or a non-Latin-1 symbol, or a future language, would be wrong.
**Idea.** Ship one on-premises, freely licensed Unicode font (for example DejaVu Sans) in `app/static/fonts/` and register it with `fpdf2`; keep the Latin-1 fallback if the file is missing. A test renders a sample with Greek, Cyrillic and typographic characters and extracts the text back.
**Value.** The PDF becomes safe for every language the catalogue may get. **Epic:** EPIC-20.
**Delivered (v4.7, FR-165).** Noto Sans plus the Noto font of each script (Devanagari, Bengali, Gurmukhi, Gujarati, Odia, Tamil, Telugu, Kannada, Malayalam, Georgian, Naskh Arabic, Nastaliq Urdu) are bundled in `app/static/fonts/` with their OFL licence, the text is shaped with `uharfbuzz` and Arabic and Urdu are laid out right to left. Checked by `tests/integration/test_pdf_scripts.py` (TC-060) and by looking at the rendered pages of a sample in all twelve script families. Remaining: bold type (only regular weights ship), a taller line for Nastaliq so its tall letters do not touch the cell border, and a translated title page and headings (layer C of [26-translations.md](26-translations.md)).

### I-38 · Complete German coverage — 🔴 HIGH · M
**Problem (observed).** The catalogue (`app/i18n_de.py`, ~690 strings) covers every template string, but messages built in the service layer (flash messages, validation errors), the administration screens and the column headers of exports stay English (documented limitation in 22 §13).
**Idea.** Route service-layer messages through message codes with parameters, translate them in one catalogue, translate the administration templates, and make export headers part of the profile (a `label_de` next to `label`). Extend `test_i18n` to fail on any user-visible English literal in `app/` that has no catalogue entry.
**Value.** German-speaking users get one language throughout; removes a source of confusing mixed-language screens. **Epic:** EPIC-15.

## B.3 🟠 MEDIUM priority

| ID | Idea | Detail | Epic |
|---|---|---|---|
| **I-39** | **Asymmetric manifest signatures and key rotation (M) (observed)** | Decision D-05 chose HMAC because it needs no PKI, but a verifier then needs the secret and could forge a manifest. An Ed25519 key pair (private key on the server, public key distributed with the manuals) lets Technical Publications verify without being able to sign; the manifest already carries a `key_id`, so old and new keys can coexist. Add a documented rotation procedure for `MANIFEST_SIGNING_KEY` and for the audit key (a signed *checkpoint* entry before and after a key change). | EPIC-18, EPIC-12 |
| **I-40** | **Holiday calendar for business days (S) (observed)** | `business_days_between` skips only weekends, so a public holiday week looks like a stalled queue. An Administrator-maintained table of non-working days (per site or global) feeds SLA ages, reminders and the KPIs. | EPIC-19 |
| **I-41** | **Run and test on PostgreSQL (L)** | I-34 delivered the inventory (47 blockers, 125 ports at the baseline of 2026-10-24, schema v4.7) and the dialect guards; the port itself is open: a PostgreSQL schema file, PL/pgSQL triggers, `FOR UPDATE`/advisory locks instead of `BEGIN IMMEDIATE`, `tsvector` search, `pg_dump`-based backup and a CI job that runs the suite on PostgreSQL. Do this when volume or availability needs justify it (Phase 3). | EPIC-13 |
| **I-42** | **Git-linked status code library versions and tag proposals (L)** | Every controller software release tag gets a *status code library version* (SemVer-like: new code = minor, changed meaning/severity/reaction = major, text only = patch). Tags are *pulled as proposals* from a local or mirrored clone (optionally enriched from GitHub), a human accepts, edits or rejects them; an unchanged software release attaches to the existing library version; a drift scan compares the controller source with the library. Designed (state machine, data model, options, open questions) but **not built**: it needs a sample of the controller source files, the Git host and the tag conventions. Strictly opt-in and read-only toward the code repository, with an explicit exception recorded in 11 §12. | new EPIC-26 |
| **I-43** | **Template-driven DOCX export (L)** | Generate the status-code documentation straight into the customer or brand Word template (registry of versioned templates, placeholders validated on upload, audience-redacted content, headings and tables that feed the table of contents, document properties with library version and hash, optional PDF where LibreOffice exists). The Word output is designed but **not built**; it needs the three real templates (put in the project folder or uploaded, see I-66), the meaning of "2xm/3xm/4xm" (assumed: the turbine platforms) and the audience tiers per customer. | EPIC-20 |
| **I-44** | **Import worker that survives a restart (M) (observed)** | A large import runs in a thread of the web process; a restart leaves the job at its last recorded state and the file must be re-uploaded. Persist the evaluated rows, process them from a small job table by a separate process (or `flask import-worker`), resume after a restart. | EPIC-14 |
| **I-45** | **Backup replication and encryption (S)** | `flask backup-db --mirror <dir>` to copy each verified generation to a second location and record it in the status file; optional encryption of the copy with a key from the password safe; readiness reports an unreplicated backup. | EPIC-25 |
| **I-46** | **Webhook retry with back-off and a dead-letter view (S) (observed)** | A delivery is attempted once; a consumer that is down for ten minutes misses the event (the change feed is the safety net). Retry a few times with back-off from the reminder job and show undelivered events on the Integrations page with a *Resend* button. | EPIC-11 |
| **I-47** | **Active Directory / ADFS authentication (L)** | The `AuthProvider` seam exists (FR-005); **Partly built (v4.7, FR-163, SEC-033):** the Windows sign-in behind an authenticating gateway matches the identity with the (fixed) e-mail address and can be simulated on a developer machine; still open are a direct LDAP/Kerberos or ADFS/SAML provider, a group-to-role mapping policy and just-in-time user creation. Must not introduce any cloud identity provider. | EPIC-12 |
| **I-48** | **Key custody helper (M) (observed)** | The three generated keys cannot be recovered; losing the audit key makes old chain entries unverifiable. A `flask keys-check` that confirms the keys are present and have the expected strength and a printable escrow sheet for the password safe at install time. | EPIC-25 |
| **I-49** | **Bulk revision as a change set (M)** | Controls engineers sometimes change one field across many codes (a delay unit, a reaction). A bulk action creates one revision Draft per selected code, groups them in a change set and shows the diff of all of them, so review and approval stay per code but the work is one operation. | EPIC-04 |
| **I-61** | **Batch edit of imported Drafts (M)** | The status code import gives every Draft the same category, platforms and empty audience access. A bulk action on a change set would set them for the ticked codes in one step, each still an ordinary edit of an open Draft by its author (audited per code). | EPIC-14 |
| **I-62** | **Bulk submit and bulk domain sign-off (M)** | An imported batch of hundreds of Drafts must be submitted one by one and each needs the cross-domain sign-off. A change-set action would submit every ready Draft and let a domain owner sign off the batch with one password confirmation, as the bulk decisions already do (I-11, I-17). | EPIC-19 |
| **I-63** | **Re-import and drift report (M)** | `import_source_item` keeps the SHA-256 and the parsed attributes of every program. Uploading the same program again could show which attributes changed against the catalogue and open a revision (or update the Draft) for the codes the user ticks. | EPIC-14 |
| **I-64** | **Wire the remaining program attributes (M) — delivered in v4.9.1 (FR-168)** | User-group levels, the remaining subsystem programs, the operating-mode mask and the task frequency are parsed and kept as JSON only. Once the v4.1 columns are editable in the application the import should fill them; the mapping table of 06-data-dictionary.md §5a lists which. | EPIC-14 |

## B.4 🟢 LOW priority

| ID | Idea | Detail | Epic |
|---|---|---|---|
| **I-50** | Pause the SLA clock while waiting for the author (S) | A request rejected back to Draft is already outside the clock; add an explicit *waiting for the author* state for questions in Review so reviewers are not shown as slow. | EPIC-19 |
| **I-51** | Alert rules and dashboards shipped with the metrics (S) | The suggested alerts of 14 §8 as a Prometheus rule file and a Grafana dashboard JSON that the platform team can import. | EPIC-25 |
| **I-52** | Audit-log export and saved filters (S) | A CSV export of the filtered audit log (itself audited) and saved filters for the usual auditor questions. | EPIC-10 |
| **I-53** | Command palette and keyboard shortcuts (S) | Jump to `StCd-…`, search or a screen with the keyboard; `g s` style shortcuts documented in Help. | EPIC-15 |
| **I-54** | Translation memory and term check (M) | Reuse translations of identical sentences across codes and flag a translated term that differs from the project glossary. | EPIC-22 |
| **I-55** | Description linter (S) | Rules beyond the current "title must not equal description": minimum information, units spelled consistently, banned words — shown as warnings. | EPIC-02 |
| **I-56** | Customer read-only view with permalinks (M) | A stable per-code URL for a read-only, audience-scoped view (and a QR code on printed documents). Conflicts with FR-083 (internal network only) unless the view is served inside the customer-reachable segment; needs a business and security decision first. | new EPIC-27 |
| **I-57** | Mobile / tablet layout (M) | The shell collapses on narrow screens but dense tables are desktop-first; a card layout for the list and detail pages. | EPIC-15 |
| **I-58** | Token usage report and per-token rate limit (S) | `last_used_at` exists; add request counts, the endpoints used and a limit so a runaway consumer cannot slow the application. | EPIC-11 |
| **I-59** | Stronger test techniques (M) | Mutation testing on the lifecycle, numbering and segregation-of-duties code; a `hypothesis` state-machine test over random sequences of workflow actions; trend of the performance measurements across report runs. | EPIC-13 |
| **I-60** | Document-to-code links (S) | From a code's page, show which export jobs and releases contained which wording (the export history already stores hashes per release); answers "which manuals need to change?". | EPIC-18 |

---

## B.5 Proposed new epics

| Epic | Name | Contains | Size | Suggested phase |
|---|---|---|---|---|
| **EPIC-26** | Git-Linked Library Versions | I-42 | L | After the Git host, tag convention and a controller-source sample are known |
| **EPIC-27** | External Read-Only Access | I-56 | M | Only after the FR-083 decision |

Existing epics to extend: EPIC-02 (I-55), EPIC-04 (I-49), EPIC-10 (I-52), EPIC-11 (I-46, I-58), EPIC-12 (I-39, I-47), EPIC-13 (I-41, I-59), EPIC-14 (I-44), EPIC-15 (I-38, I-53, I-57), EPIC-18 (I-39, I-60), EPIC-19 (I-40, I-50), EPIC-20 (I-37, I-43), EPIC-22 (I-54), EPIC-25 (I-45, I-48, I-51).

## B.6 Decisions needed from the business before work starts

| Question | Unblocks |
|---|---|
| Which Git host is used, how are release tags named (platform, pre-release and hotfix markers), are GitHub Releases used, are tags signed, and may the tool ever write back? Please also supply a sample of the controller source files that carry status codes. | I-42 |
| Where are the customer and brand Word templates, who owns their placeholder conventions, which audience tiers does each customer need, and does "2xm/3xm/4xm" mean the turbine platforms or the 2xxx/3xxx/4xxx number ranges? Is LibreOffice available for PDF output? | I-43 |
| Which languages beyond English and German will the manuals need, and in which fonts? | I-37, I-38, I-54 |
| What is the meaning of `Covert` (and of the other access values)? | I-56, and removes the safe default of D-02 |
| Which public holidays apply to which site? | I-40 |
| Is a PKI or a key-management system available on the network? | I-39, I-48 |
| Is an off-host or second-volume location available for backups, and is encryption at rest mandatory for them? | I-45 |
| Is the volume or availability requirement expected to outgrow one SQLite file, and when? | I-41 |
| Which directory (Active Directory / ADFS) and which group-to-role policy? | I-47 |
| May any part of the catalogue be reachable from a customer-facing segment? | I-56 |

## B.8 Follow-ups of the roles and languages change (v4.3)

Open points, not built; none has an I-number yet because the business has not ranked them. (1) Let the StCd Owner tag engineering domains, so an Engineer they promote can give cross-domain sign-offs at once. (2) Let a colleague cover for the StCd Owner (delegation covers only Reviewer, Administrator and Chief Engineer). (3) Decide whether the StCd Owner may read the audit log. (4) A second person's confirmation when an Administrator role is handed out. (5) Have the fourteen added languages reviewed by native speakers and extend them to the full catalogue (German is complete); until then keep them off for people who depend on them. (6) Show a translated word beside the lifecycle and category codes (translation scope, `10-ui-ux-specification.md` §10a). (7) Translate the flash messages of the service layer for the interface, never the API messages. (8) Decide the flag for Bengali and Punjabi (India today; Bangladesh and Pakistan are the other homes of the languages).

## B.9 Follow-ups of user administration, withdrawal and re-import (v4.6)

Open points, not built. (1) Deleting an account is possible only while it has no history; a person who must disappear for data-protection reasons needs an *anonymise* action that replaces name and e-mail but keeps the account row and its audit trail. (2) Bulk deactivate and bulk role change in the user list. (3) Bulk withdraw from the change-set page, not only from *My Change Requests*. (4) A Draft that is withdrawn after other people commented loses those comments except in the audit snapshot; a *return to author* state would keep them. (5) The preview of a re-import compares only the fields the catalogue has columns for; the user-group levels and the subsystem programs of the file are kept in the provenance JSON but not compared. (6) Update from a file for a code in Review has to wait for the decision; a *replace the Draft under review* path is open.

## B.10 Translations (v4.7)

The concept and the eleven open items for checking the translations by native speakers and for exporting the status code manuals in every designated language are in [26-translations.md](26-translations.md) §8. Built since: the review itself runs in the application, in its own section *Translations* (FR-164, [26-translations.md](26-translations.md) §3.4). The ones that matter most: find one native-speaker reviewer per language and assign them there; mark unreviewed languages as beta; a terminology list per language; language competence on the user for approving status code translations; content sheets (export and import) for translating the status codes; a coverage matrix and a readiness rule per Release; Unicode fonts for the PDF (I-37). Delivered in v4.9: the whole interface in all nineteen languages (FR-167, I-38) and the technical nomenclature as a section of its own with a two-person approval (FR-166, [26-translations.md](26-translations.md) §8a); the critical review of the implementation is in §8b of that file.

## B.11 Delivered since v4.9, and what the review of the release process added (v4.10)

**Delivered after the list was written** (each is specified in [03-srs.md](03-srs.md) §1.17 and traced in [20-traceability-matrix.md](20-traceability-matrix.md)):

| Delivered | Version | Requirements |
|---|---|---|
| The fields of the generated programs (further programs, flags, task call frequency, operating-mode mask, user-group levels) stored, edited, imported and exported — this is **I-64** | v4.9.1 | FR-168 |
| Users with history and withdrawn codes can be deleted (erased in place, the audit log is never changed) | v4.9.0 – v4.9.2 | BR-025, BR-026 |
| The menu grouped by the work of the user, with counts and a Menu button | v4.9.2 | FR-169 |
| The *beta* mark for unreviewed languages, hidden from Viewers and guests | v4.9.2 – v4.9.3 | FR-170, FR-172 |
| The words around an export in the language of the export | v4.9.2 | FR-171 |
| **The complete baseline of a Release** (every code valid as of it, ~900 MC + ~350 HC), narrowed by platform (2XM / 3XM / 4XM) and controller (MC / HC) | v4.10.0 | FR-173 |
| **The package**: every language x every access level x chosen formats, release notes and a manifest with a SHA-256 per file, built in the background | v4.10.0 | FR-174 |
| **The download rule**: everybody downloads what is released; the working set and unpublished Releases only the StCd Owner and the Administrator | v4.10.0 | FR-175 |
| **Confidence check of the translations**, separate approval of new and changed strings, language impact notices to the StCd Owner | v4.11.0 | FR-176 … FR-178 |
| **Connections** between status codes (suppression, preconditions, escalation) read from the imported programs | v4.12.0 | FR-179 |
| **Bulk workflow for the migration — I-70 with I-61 and I-62**: the workbench of a change set (readiness, bulk edit, bulk submit, bulk domain sign-off, bulk decisions), the sample inspection (stratified, 10 % / at least 8, one defect blocks), and the dossier (XLSX) for an auditor | v4.13.0 | FR-180 |
| **Select-all on every list with tick boxes; a status category per program of a `.st` import (by alarm type, per row or for the ticked rows); delete several own Drafts at once from the Status Codes list — I-65** | v4.13.1 / v4.13.2 | FR-181, FR-182 |
| **Dark mode**: Automatic (system) / Light / Dark in the top bar, every colour a token, the dark palette checked for contrast | v4.14.0 | FR-183 |
| **Visible version**: in the menu, on the login page and in the health endpoints, from one place in the code | v4.14.1 | FR-184 |
| **Release documents as PDF**: full documentation, software description, user manual and test report, each with the version in its file name | v4.15.0 | FR-185 |
| **Design showcase decks** (management, team) from real screenshots, and the identity of every title page: long name, owner line, logo | v4.16.0 | FR-186, FR-187 |
| **Hand-over to the team repository**: audited clean export, code owners, pipeline for GitHub, contribution guide | v4.16.0 | FR-188 |
| **No assumed values in the `.st` import**: a variable stays its name, what the program lacks is listed in the comment, no status category is preselected; the user-group numbers become named access levels where exactly one level fits | v4.16.1 | FR-189, FR-190 |

**New ideas from the review of the release process** (not built):

| ID | Idea | Priority | Effort | Epic |
|---|---|---|---|---|
| I-66 | Upload of the DOCX templates in the application (one per platform, replaceable by an Administrator, placeholders and styles checked on upload) — the way into I-43 | 🟠 MEDIUM | M | EPIC-20 |
| I-67 | Publish gate on translation coverage: warn or block the publication of a Release while a language is below a threshold (today the Release page only shows the numbers, FR-173) | 🟠 MEDIUM | S | EPIC-22 |
| I-68 | Packages: retention and cleanup of the files under `instance/packages`, one running build per Release, a build that survives a restart (as I-44), a notice when it is ready | 🟠 MEDIUM | M | EPIC-20 |
| I-69 | A manual edition number and document properties (library version, Release, hash) printed on every file of a package | 🟢 LOW | S | EPIC-20 |

**I-43 now.** The baseline, the platform and controller filter and the package are the data side of it and are built. What is missing is the Word output itself: the three templates (2XM, 3XM, 4XM; assumed to be the turbine platforms, which the templates will confirm) are to be put in the project folder or uploaded in the application (I-66), together with their style names, the cover fields and an example entry page.

## B.12 What would benefit the controls team most (2026-10-24)

Weighed from the work of a wind turbine controls team - getting ~1,250 codes (about 900 Main, 350 Hub) into governed use, keeping the manual equal to what the turbine does, and helping the technician at the turbine - not from the list of what is easy to build. The holiday calendar (I-40) is dropped: not needed.

| Rank | ID | Idea | Why it matters to the team | Size |
|---|---|---|---|---|
| 1 ✅ | I-70 | **Bulk workflow for the migration** (delivered in v4.13): bulk edit (I-61), bulk submit and bulk cross-domain sign-off (I-62) and a bulk decision with a sample check for a change set of imported codes | The three decisions per code are right for a new code and impossible for 1,250 imported ones; without a bulk path go-live stalls in the queues of four roles | M |
| 2 | I-71 | **Build-against-catalogue check**: upload the generated programs of a controller software build and get a drift report against the released baseline for that software version (extends I-63 and the first step of I-42) | Closes the loop *manual = turbine*: the one question the whole tool exists to answer, asked at every software release instead of once at import | M |
| 3 | I-72 | **Definition linter with turbine rules** (extends I-55 and I-67): alarm without remedy text, set or reset delay inconsistent with the category, a repeat counter without a replacement code, a Hub code without a Main counterpart, a missing program field, duplicate titles; shown per code and as a gate on the Release | Catches the defects that cost service technicians time, before they are published; gives the Release a measurable completeness | S - M |
| 4 | I-73 | **Change propagation across platform variants**: when a code of 3XM is revised, list its 2XM and 4XM variants with the same change prefilled for review | The same fault is maintained three times today; this is the main source of drift between platforms | M |
| 5 | I-74 | **Technician lookup at the turbine**: the offline page (I-24) as an installable page with search by symptom and free text, the remedy steps first, related codes, and the language of the technician | The people who read the codes most are at the turbine without a network, not at a desk | M |
| 6 | I-67 / I-68 / I-69 | Release hardening: publish gate on coverage, package retention and resumable builds, edition number | Keeps what v4.10 delivered dependable for Technical Publications | S - M |

Items that wait for input from outside the project (templates for I-43 and I-66, the directory for I-47, the Git host for I-42, a PostgreSQL environment for I-41) stay where they are.

## B.7 Suggested sequencing

1. **With go-live of v4:** I-45 (backup copy), I-48 (key custody) (I-37, the PDF font, is delivered) — small and they close observed gaps.
2. **First quarter in production:** I-40 (holidays), I-44 (resumable import) and, once its inputs exist, the design-ready I-42 and I-43.
3. **Second quarter:** I-39 (signatures and rotation), I-46 (webhook retry), I-49 (bulk revision), I-47 (SSO) as needed.
4. **Later / on demand:** the LOW items and I-41 when the volume justifies the port.

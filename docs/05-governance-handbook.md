# 05. Status Code Governance Handbook — CSCM Tool

## 1. Purpose

This handbook is the authoritative governance policy the application must enforce in software. Where this document and any other document disagree on a process rule, this document wins.

## 2. Code Numbering Strategy

The Status Code Identifier is `StCd-XXXXX`: a five-digit, zero-padded number, e.g. `StCd-01232`. Its numeric value is not arbitrary — it equals the code's position within its Functional System Group's fixed numeric range, so the identifier itself encodes classification. There is no separate prefix letter scheme in the identifier (the former `MC-`/`HC-` split and its Controller Type basis are retired entirely); the four-letter group codes (`WCNV`, `WGEN`, ...) are displayed alongside the identifier for cross-reference but are not part of it.

| Range | Functional System Group | Prefix (display only) |
|---|---|---|
| 1000–1999 | Converter & Grid Interface | WCNV |
| 2000–2999 | Generator System | WGEN |
| 3000–3999 | Meteorology & Nacelle Environment | WNAC |
| 4000–4999 | Rotor & Pitch System | WROT |
| 5000–5999 | Tower & Structure | WTOW |
| 6000–6999 | Transformer & MV System | WTRF |
| 7000–7999 | Drivetrain & Gearbox | WTRM |
| 8000–8999 | Yaw System | WYAW |
| 9000–9999 | Turbine Control & Operation | WTUR |
| 10000–10999 | *free — reserved for a new group* | — |
| 11000–11999 | Hub Controller Control System | WTUR |
| 12000–12999 | Hub Controller Rotor & Pitch | WROT |
| 13000–13999 | Wind Farm / Plant Dispatch | WPPD |
| 14000–14999 | *free — reserved for a new group* | — |
| 15000–15999 | *free — reserved for a new group* | — |
| 16000–16999 | *free — reserved for a new group* | — |

**Prefix reuse (added 2026-09-17):** `WTUR` and `WROT` each identify two numerically distinct groups — one Main Controller, one Hub Controller — confirmed explicitly by the business as intentional (same thematic domain, separate status code range per controller's software). The prefix is a display/cross-reference label only; the numeric range is always the authoritative identifier of which group a code belongs to (06-data-dictionary.md §9).

**Reserved capacity (confirmed 2026-09-17):** `10000–10999`, `14000–14999`, `15000–15999`, and `16000–16999` are explicitly free — no Functional System Group occupies them yet, and none is required to. This includes the `15000–15999` range previously found in the live 4XM codebase, which turned out to be exactly this kind of reserved space, not a code-classification gap needing resolution. An Administrator can assign a whole new Functional System Group (and its subgroups) into any of these ranges later, following the same non-overlap validation as adding a subgroup (§9a.1 of 06-data-dictionary.md) — a pure data change, never a schema migration.

**Subgroups (mandatory — corrected 2026-09-17):** every Functional System Group is divided into Functional Subgroups, and every Status Code must belong to exactly one — Functional Subgroup is **never optional**, confirmed against a real export where all 897 live status codes carry one. Most subgroups own a 100-number sub-band aligned to the hundreds digit of the identifier; the **first subgroup of each Main Controller group owns the first 200 numbers** (e.g. `StCd-010xx`, 01000–01199, is the Converter subgroup within Converter & Grid Interface; Tower is 05000–05199); the Hub Controller groups follow the same alignment and the same naming (`123xx` is 12300–12399, `110xx` is 11000–11099). **A subgroup code is the digits of the first number of its band, with `x` for the free positions, and never carries a dash or a letter:** a band shorter than a hundred is named by its first ten with a digit in place of the second `x` (`1110x` is 11100–11149, `1115x` is 11150–11199, `1205x` begins at 12050); within Turbine Control & Operation, six subgroups share the `099xx` hundred-block in finer ten-number sub-bands and are called `0990x` (9900–9929), `0993x` (9930–9959), `0996x`, `0997x`, `0998x` and `0999x`. The range shown next to a code is always the true band. The real taxonomy, corrected 2026-09-17 against the authoritative row-level export (superseding an earlier hand-typed summary that used the wrong subgroup names — the exact issue flagged by the business), is seeded in full: 06-data-dictionary.md §9a, `artifacts/schema.sql`.

Not every block within a group is currently assigned to a named subgroup — e.g. `011xx` and `045xx`–`049xx` within Rotor & Pitch System are unassigned. This is deliberate reserved capacity, not a gap to close: an Administrator can create a new Functional Subgroup at any time, in any Functional System Group, choosing any sub-range that does not overlap an existing one (validated by the service layer and, as a backstop, a database trigger — 07-database-design.md §5). No hundreds-digit alignment is enforced — the WTUR ten-number sub-bands prove narrower ranges are legitimate — but the UI suggests the next hundred-aligned free block as a sane default. Adding a subgroup, like adding a Functional System Group (subject to resolving the open `15000–15999` item above), is a pure lookup-table data change, never a schema migration or a renumbering of existing codes. A code that already exists inside a currently-unassigned block (e.g. legacy `StCd-04960`, found in the live 4XM codebase, sitting in the unassigned `049xx` block) predates this taxonomy and needs formal reclassification once a covering subgroup exists — the mandatory-subgroup rule applies to newly created codes; it does not retroactively invalidate legacy data.

**Allocation rule:** the identifier is **not** assigned at Draft creation. An Engineer creating a new Status Code selects a Functional System Group and a Functional Subgroup via dropdown — **both required, the subgroup is never optional** — and the Draft is worked on with no fixed number (displayed as "TBD — assigned on submission"). Only at the moment the Change Request is submitted for Review (Draft → Review) does the system atomically allocate the next free number within the selected Subgroup's sub-band. This satisfies the requirement that in-progress codes never carry a fixed number.

A Change Request that is rejected back to Draft and later resubmitted, and every later revision of an already-numbered code, **keeps the identifier it already has** — allocation happens exactly once per code (BR-001). Numbers are never reused, even if a code is later Archived. Gaps are expected wherever a Draft is abandoned before submission (its number was never allocated in the first place — it never had one). An Administrator may allocate an out-of-sequence number only for a documented migration/reservation case, recorded and audited as a manual override.

**Sandbox exception:** Administrator-created test/sandbox Status Codes never draw from the ranges above. They receive an identifier from an isolated `StCd-T#####` counter, are flagged `is_sandbox = true`, are excluded from every Release, catalogue export, and manual, and are the only records in the system an Administrator may permanently delete (§12).

Identifier + Functional System Group assignment is immutable once allocated (BR-001). If a code was genuinely created in error before any Review activity, it is deprecated, not renumbered or reassigned to a different group.

## 2a. Platform Variants

A condition that differs between Turbine Platforms is represented in one of two ways. If the same code simply also applies to another platform, the platform is added to the code's Turbine Platform multi-select — one code, one identifier. If the code is renamed or functionally regenerated for another platform, it becomes an **independent Status Code** with its own `StCd` identifier and its own full cycle, optionally pointing back to the originating code through `platform_variant_of_status_code_id` purely for navigability; the link carries no lifecycle or approval meaning (04-domain-model.md §2.10). Since v4 the *Create platform variant* action copies the latest decided revision into a new Draft for the other platform and sets the link (FR-094).

## 3. Code Ownership

Every Status Code has exactly one Owner at all times, captured on the current revision (`owner_id`). Default Owner is the Engineer who authored the first revision; reassignable by an Administrator without altering revision content or requiring re-approval. Controlled vocabularies (Functional System Group, Functional Subgroup, Turbine Platform, Engineering Domain, Status Category, Availability Group, Brake Program, Reset Program, Operational State, Access Rights, Alarm Behaviour) are owned by Governance (Administrator role); Engineers may propose new values, only an Administrator may activate one.

## 4. Lifecycle States

Seven states (extended from the original six to represent the dual-review-then-Chief-Engineer-approval sequence explicitly, rather than collapsing it into a single "Review" step):

| State | Meaning | Mutable? |
|---|---|---|
| **Draft** | Being authored; no fixed StCd identifier yet | Yes, freely |
| **Review** | Submitted; StCd identifier now fixed; awaiting the two required sign-offs (Reviewer + Administrator) | No (read-only to the author) |
| **PendingApproval** | Both required Review sign-offs recorded; awaiting Chief Engineer decision | No |
| **Approved** | Chief Engineer has approved; awaiting inclusion in a Release | No |
| **Released** | Published as part of a formal Release; authoritative and citable | No |
| **Deprecated** | No longer active; retained for historical reference | No (metadata-only: reason, superseding code) |
| **Archived** | Long-term retention state after the retention period | No |

## 5. Valid State Transitions

| From | To | Trigger | Actor |
|---|---|---|---|
| *(none)* | Draft | Create new Status Code (select Functional System Group [+ Subgroup]) | Engineer, Administrator |
| Draft | Review | Submit Change Request — **identifier allocated here** (§2); requires all Cross-Domain Sign-Offs complete (§6a) | Engineer (author), Administrator |
| Review | PendingApproval | Both required sign-offs recorded (Reviewer AND Administrator — order-independent) | System-triggered on the second sign-off |
| Review | Draft | Either required reviewer rejects (mandatory comment) | Reviewer, Administrator |
| PendingApproval | Approved | Chief Engineer approves | Chief Engineer |
| PendingApproval | Draft | Chief Engineer rejects (mandatory comment) | Chief Engineer |
| Approved | Released | Included in a published Release | Administrator (system-executed at publish) |
| Approved | Draft | Withdraw before release (exceptional; Administrator + reason) | Administrator |
| Released | Deprecated | Deprecation action (mandatory reason) | Administrator, or Engineer CR + full dual-review-and-approval cycle |
| Deprecated | Archived | Archival, only after retention period elapsed | Administrator |
| Deprecated | Released | Reinstatement (exceptional; Administrator + reason) | Administrator |

Any transition not listed is prohibited by the system.

## 6. Status Code Creation Process

1. Engineer (or Administrator) initiates "New Status Code," selects Functional System Group and Functional Subgroup via dropdown — both required (§2). No identifier is shown yet.
2. System creates a `StatusCode` (identifier `NULL`, `functional_system_group_id`/`functional_subgroup_id` set) + first `StatusCodeRevision` + a `ChangeRequest` (`cr_type = NEW`), all in **Draft**.
3. Engineer completes mandatory attributes; system validates continuously.
4. If the originating Engineer's tagged Engineering Domain(s) do not cover every domain-owned field on the revision, the Draft is flagged "awaiting domain input" and cannot be submitted until each missing domain is signed off (§6a).
5. Engineer submits for Review; the system allocates the StCd identifier atomically and transitions Draft → Review.
6. Reviewer and Administrator each independently evaluate and sign off (§7); on the second sign-off, the system auto-transitions Review → PendingApproval.
7. Chief Engineer evaluates and approves or rejects (§8); on approval, PendingApproval → Approved.
8. On inclusion in a published Release, Approved → Released, Effective Date stamped.

*(v4)* Around this process: saving a Draft that someone else changed meanwhile is refused (§9); the form warns about unknown or retired references and similar titles (§6c); the Engineer may attach evidence, group the request into a change set and state the software-version range; submitting may auto-assign the least-loaded Reviewer (§14); each decision asks for the actor's password (§7a).

## 6a. Cross-Domain Sign-Off

Some Functional System Groups require input from more than one Engineering Domain (e.g. a Generator-group code created by an Electrical engineer may still need Controls-domain parameters — delay/alarm/reset behavior — that the originating engineer cannot authoritatively provide). Each field in 06-data-dictionary.md is tagged with an owning Engineering Domain. When a Draft's originating Engineer lacks a domain tag required by one or more of its fields, the system marks those domains as "pending" and blocks Submit-for-Review until a `DomainSignoff` exists for each pending domain, recorded by an Engineer who holds that domain. This is a completeness gate, not a content judgment — it does not replace Review.

## 6b. Library Import

New capability (2026-09-17): an Engineer or Administrator may import a CSV or XLSX file of status codes (e.g. a legacy library such as the 897-row export used to ground this taxonomy) instead of creating codes one at a time through the UI. **Import is a faster data-entry path, not a governance bypass, confirmed explicitly by the business:** every row that passes field validation becomes an ordinary `StatusCode`/`StatusCodeRevision`/`ChangeRequest` triple in **Draft**, exactly as if an Engineer had typed it in — it still requires Cross-Domain Sign-Off where applicable, both Review sign-offs, and Chief Engineer approval before it can ever be Released. A row that fails validation is skipped and reported in the import job's error report (06-data-dictionary.md §5); it never partially creates a record. The source file's legacy numbering (e.g. the old "Status Code Number" column) is preserved on each created code as `legacy_reference_number` for traceability, and is never mistaken for the governed `StCd` identifier, which is still allocated only at Draft→Review (§2) — including for imported rows.

**Status codes from the generated programs (v4.2).** The controller programs `StCd_<n>.st` already carry the codes, so an Engineer or Administrator may import them directly (FR-048o … FR-048w) — several files, a folder or a ZIP at a time, first as a **preview** in which any subset is ticked, then confirmed. The same rule holds as for the CSV import: every program becomes an ordinary Draft that still needs Cross-Domain Sign-Off, both Review sign-offs and Chief Engineer approval; all Drafts of one confirmation join one change set so the batch is reviewed together. What is specific to this source: **the number is already decided by the program**, so it is *reserved* for the Draft and issued unchanged at Submit for Review (BR-023) — no sequence allocation, no Administrator override, and the allocator skips it; the subgroup follows from the band the number lies in; the legacy number (Main Controller: the old number in the program header; Hub Controller: the number in the file, which is the legacy Hub number and is translated through the numbering table) is stored as `legacy_reference_number`, which makes the **legacy → new mapping** — one direction only, because the new library holds more codes than the old one. The file carries no status category, so the uploader picks one for the batch and each Draft's author refines it.

## 6c. Soft Checks While Authoring *(v4)*

These never block a save; they make a mistake visible while it is cheap to fix (FR-091, FR-092, FR-093):
- **References.** A repeated-error pointer, a related code or a superseding code that is unknown, Deprecated, Archived or the code itself produces a warning — the pointer may legitimately name an external escalation number, so it stays a warning.
- **Similar titles.** An identical or very similar title in the same Functional Subgroup produces "did you mean to revise StCd-…?".
- **Where-used.** Every code shows which other codes refer to it. Deprecating a code that live codes still refer to requires the requester to acknowledge the dependants.
- **Platform variants.** *Create platform variant* copies the latest decided revision into a new Draft for another turbine platform and links the two; it is an ordinary Draft that still passes the whole cycle (FR-094).
- **Planned dates.** An Administrator may stamp a planned effective and planned deprecation date on the current revision; they warn at release time and appear in the health report, but never change a lifecycle state by themselves (FR-109).

## 7. Review Sign-Off Rules

Review requires **two independent sign-offs**, from two different people holding two different roles:
1. **Reviewer** (organizationally the Sub-PO for Status Codes).
2. **Administrator** (organizationally the Product Owner / Component Owner Controls Software).

Both are required; they may occur in either order and do not depend on each other. Either one rejecting (with a mandatory comment) returns the revision to Draft — the other sign-off, if already given, is discarded and must be re-given after resubmission. Neither sign-off may be given by the Change Request's author (segregation of duties, BR-005). The Administrator's sign-off is also the point at which any Engineer-proposed value in a restricted field (e.g. Access Rights — 04-domain-model.md §2.9) is confirmed or overridden as authoritative.

**Reviewer checklist (procedural, not fully machine-checkable):**
1. No duplicate or overlapping-meaning code exists (system-assisted search, human judgment).
2. Classification fields are internally consistent (hard incompatibilities are system-enforced per 06-data-dictionary.md; soft conventions are reviewer judgment).
3. Delay Parameters are sane for the selected Operational State.
4. Description is unambiguous, not a restatement of the Title.
5. Functional System Group / Subgroup assignment matches the condition's actual subsystem.

*(v4)* The Administrator can turn this checklist into **configured review-checklist items** per Functional System Group (or for all groups). An approving Reviewer must confirm every active item that applies; the confirmed wording is stored with the sign-off, so later edits never rewrite history (FR-128). A Reviewer, Administrator or Chief Engineer may also comment on **one specific field** while the request is in Review or Pending Approval; the author sees open field comments inline and marks them resolved (FR-127).

## 7a. Password Confirmation and Delegation *(v4)*

**Step-up (SEC-026, BR-022).** Reviewer and Administrator sign-off, Chief Engineer decision, publishing a Release and the full-database export require the actor to enter their own password again, so each is a deliberate, attributable act and an unattended session cannot approve anything. A missing password gives `step_up_required`, a wrong one `step_up_failed`; both are audited.

**Delegation (FR-125, BR-017).** A Reviewer, Administrator or Chief Engineer who will be absent names a delegate for a date range (an Administrator may arrange it for anybody). While the delegation is active the delegate may take the *decision actions* of that role — never user administration or other Administrator functions. The delegate acts **as themselves**: the audit entry names them and the person they cover for, segregation of duties applies to them personally (they cannot decide a request they wrote or already signed, and the two Review sign-offs must still come from two different people), and the Reviewer auto-assignment skips an absent Reviewer. The delegator or an Administrator can revoke it.

## 8. Chief Engineer Approval

Once both Review sign-offs are recorded (PendingApproval), a Chief Engineer performs the final Approval decision — approve or reject with a mandatory comment on rejection. The Chief Engineer may not be the Change Request's author, the Reviewer who signed off, or the Administrator who signed off on the same Change Request (segregation of duties extends across all three decision points). *(v4)* A Chief Engineer may work through a **change set** — the requests that ship with one controller software release — in one sitting: each request is still decided by its own single-request service call with its own segregation-of-duties check, comment and audit entry, the password is asked once, and a request the actor may not decide is reported as skipped without blocking the others (FR-124). Approval is the final governance gate before a revision is eligible for Release; it is a distinct accountability step from Review and is always performed by a named individual, never inferred from role membership alone.

## 9. Revision Numbering & Concurrency

Each new Draft opened against an existing `StatusCode` increments `revision_number`; a rejection (Review or PendingApproval → Draft) reuses the same revision row; only one open (Draft/Review/PendingApproval) revision is permitted per `StatusCode` at a time (BR-003). *(v4)* Every Draft carries a `row_version` that increases on each save; a save based on an older version is refused with 409 and the user's entries are kept for comparison, so two people editing the same Draft can no longer overwrite each other silently (FR-090, BR-019).

## 10. Release Rules

Only an Administrator may create/publish/pre-publish-delete a Release ( candidate pool is Approved-state revisions matching the scope filter, now expressed in terms of Functional System Group/Subgroup rather than Controller Type; publish is atomic; a published Release is permanently immutable). *(v4)* Before publishing, the Administrator may set the controller **software versions** the Release targets, which limits the candidate list to revisions whose version range includes a target (BR-021); publishing asks for the password (§7a) and warns, without blocking, about included revisions whose planned effective date is in the future. Every export of a Release carries a manifest of SHA-256 hashes (signed when a key is configured), the Release has generated **release notes** against the previous published Release, and exports can be scoped to an audience (only values the Administrator confirmed at sign-off count; `Covert` is treated as not visible, BR-016), a language (approved translations only, §16) and a software version (FR-100 … FR-111).

## 11. Deprecation, Retention & Archival Rules

Deprecation requires a reason and optional superseding reference; minimum 180 days in Deprecated before Archival; 7-year minimum retention for Archived records and all associated Change Requests/comments/sign-offs/audit entries, never hard-deleted — **except** sandbox Status Codes (§12). *(v4)* The deprecation request lists the live dependants (Where-used) and the requester acknowledges them; audit entries older than the retention period are archived to compressed files with a hash and are never deleted (§18).

## 12. Sandbox / Test Status Codes

An Administrator may create a Status Code flagged `is_sandbox = true` for testing purposes (e.g. verifying a new export template, training a new Reviewer). Sandbox codes:
- Draw their identifier from an isolated `StCd-T#####` band, never from a real Functional System Group range, so they can never collide with or consume a production number.
- Are excluded from every Release candidate list, catalogue export, and manual by construction (a hard filter, not a convention).
- May proceed through the same lifecycle states for realistic testing, but can never actually be included in a real Release (the system blocks adding a sandbox-flagged revision to any Release, regardless of state).
- Are the **only** records in the system an Administrator may permanently delete. Deletion is logged as an immutable `SANDBOX_DELETE` audit entry that captures the full record snapshot in `before_value` — the audit trail entry survives even though the record itself does not (12-audit-compliance.md §2).
- This is a narrow, explicit, audited exception to the otherwise absolute no-hard-delete rule (§11) and must never be generalized to non-sandbox records.

## 13. Compliance Rules

Every Released Status Code must be traceable, without gaps, through Draft → Review (both sign-offs, with identity and timestamp) → PendingApproval → Approved (Chief Engineer, with identity and timestamp) → Released (Release identity, Effective Date). Segregation of duties is enforced server-side at all three decision points (Reviewer, Administrator, Chief Engineer), never only in the UI.

## 14. Service Levels and Reminders *(v4)*

A request waiting for a decision is aged in **business days** (Monday–Friday; no holiday calendar) from the moment it entered its stage and shown amber or red against Administrator-configured thresholds (defaults: Review 3 / 5, Approval 2 / 3 days — settings `sla.review.*`, `sla.approval.*`). `flask send-reminders`, run by the scheduler, creates one in-app notice per decision holder (including delegates), request, stage, level and day; if the organisation's own SMTP relay is configured the same text is mailed. Administrators see the **stalled requests** list with one-click reassignment (FR-039) and the open reviews per Reviewer; with `reviewer.auto_assign` enabled the least-loaded available Reviewer is assigned at submit. The business-case KPIs (median approval time ≤ 7 days, cross-domain turnaround ≤ 3 days, audit-trail completeness 100 %, queue ages, codes without an active owner) are computed on the Success Metrics page (FR-120 … FR-123, FR-129).

## 15. Evidence, Remedy Content and Change Sets *(v4)*

The author (or an Administrator) may attach **evidence** — test reports, simulation results, design notes, a safety assessment — to an open request (allow-listed types, checked against their content, at most 10 MB and 20 files each, stored outside the web root, downloadable by the working roles only, removable only while the request is a Draft; FR-130). Revisions may carry *remedy text*, *affected component*, *related codes* and *standard references* for service use (FR-131). Requests that ship together are grouped in a **change set** (FR-124); grouping changes presentation and queueing only, never the decisions required.

## 16. Translations *(v4, decision D-03)*

English is the source language of every code. A translation of title, description and remedy text is saved as DRAFT against an Approved or Released revision by an Engineer or Administrator, and approved by one Reviewer or Administrator **other than the translator** — a light review, deliberately not the three-decision cycle (BR-018). Editing an approved translation returns it to DRAFT; translations can be carried over from the previous revision as DRAFTs. Exports in a language use approved translations only (falling back to English unless the export is strict), and the translation worklist lists the current codes still lacking an approved translation (FR-110, FR-111).

## 17. Hub → Main Controller Consolidation *(v4, assumption A-008)*

If the Hub Controller leaves the hardware setup, its codes are defined anew on the Main Controller side without renumbering anything: *Create MC draft* on an Approved or Released Hub code copies the descriptive fields into a new Draft in a chosen Main Controller group and subgroup (the new MC number is allocated at submit, the Hub identifier is kept as the legacy reference, a mapping row is recorded). The mapping report shows every Hub code with the state of its replacement; once a replacement is Released, an Administrator opens deprecation requests for all such Hub codes of a group at once — each an ordinary deprecation request needing review and approval (FR-147, BR-015). Hub groups stay ordinary data (`controller_type = HUB`, decision D-06).

## 18. Integrity, Backup and Retention *(v4)*

Each audit entry stores the hash of the previous one; an Administrator verifies the chain on demand and a scheduled job verifies it weekly, so an edited, removed, reordered or truncated entry is found (FR-151). Verified backups are taken nightly and each is proven restorable (FR-150); the readiness probe reports `degraded` when the newest verified backup is older than 36 hours. Audit entries older than seven years are archived, never deleted (BR-020). The restore drill is rehearsed quarterly (14-deployment-architecture.md §7).

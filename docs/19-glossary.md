# 19. Glossary — CSCM Tool

This glossary is a living document. Any change to terminology, roles, lifecycle states, or domain concepts elsewhere in this package must be reflected here in the same pull request (see 15-development-standards.md §6). Terms are alphabetical.

**Administrator** — System role. Organizationally equivalent to the Product Owner Controls Software / Component Owner Controls Software. Owns user administration, lookup/vocabulary governance (incl. creating new Functional Subgroups), Release publishing, database export, sandbox status codes, and is one of the two mandatory Review sign-offs (05-governance-handbook.md §7).

**API Token** — A scoped, expiring, revocable secret an Administrator issues to a machine consumer on the internal network (scopes `catalogue:read`, `changes:read`; at most 365 days). Sent as `Authorization: Bearer cscm_…`, honoured only on read-only `GET` operations that declare its scope, with Viewer-level visibility; stored only as a SHA-256 hash and shown once (FR-144, SEC-027).

**Applicability Matrix** — The answer to "which Released codes apply to controller software version X" and "what was added, removed and changed between versions X and Y", computed from the revisions' version ranges (FR-107, decision D-01).

**Approved** — Lifecycle state reached once a Chief Engineer has approved a status code revision that has already completed dual Review sign-off. Awaiting inclusion in a Release.

**Archived** — Terminal lifecycle state for long-retained, inactive status codes, reached from Deprecated after the minimum retention period.

**Audience** — One of the eight groups an export can be scoped to: Development, Sales, TCC, Service, Turbine Operator Package, Grid Operator, Service Partner, Customer. An audience export contains only the codes the Administrator-confirmed access value makes visible to that audience (FR-102, BR-016).

**Audience Access Fields** — Eight independent governed fields (Development, Sales, TCC, Service, Turbine Operator Package, Grid Operator, Service Partner, Customer), each with its own real vocabulary, controlling visibility per audience (corrected 2026-09-17 from a real library export; replaces the earlier single "Access Rights" enum). Proposed by the authoring Engineer but only authoritative once confirmed by the Administrator's Review sign-off (06-data-dictionary.md §2d, §9d).

**Audience Visibility** — The flag `audience_visible` on each value of the eight access vocabularies. A code is visible to an audience only if its confirmed value for that audience has the flag set; no value, or `Covert`, means not visible (decision D-02).

**Audit Anchor** — The row count and head hash written to `instance/audit_chain_anchor.json` by every successful chain verification; the next verification uses it to detect entries removed from the end of the log.

**Audit Hash Chain** — The tamper-evidence of the audit log: each entry stores `prev_hash` and `entry_hash` (SHA-256, or HMAC-SHA-256 with `AUDIT_HMAC_KEY`) over its own fields and its predecessor's hash. Verification finds an edited, removed, reordered or truncated entry (AUD-074, AUD-075).

**Audit Log Entry** — Immutable system record of every state-changing action (12-audit-compliance.md). Never edited or deleted, with one narrow exception: the deletion of a Sandbox Status Code, which is itself logged (the deletion event persists even though the underlying record does not).

**Available Group** — A numeric availability-accounting code (corrected 2026-09-17: real data uses a plain integer, not a lettered A–D group). Soft-validated against the currently-observed set; descriptive labels not yet available from source data (06-data-dictionary.md §9c).

**Backup, Verified** — A copy of the database made with SQLite's online-backup API and proven usable: integrity check, restore into a scratch database, row-count comparison and audit-chain check. Only a verified backup counts as the last good one (FR-150, NFR-012).

**Business Day** — Monday to Friday; there is no holiday calendar. Service levels are counted in business days (FR-120).

**Change Feed** — `GET /api/v1/changes`: releases, deprecations, reinstatements and archivals in audit order, paged with a `since_id` cursor and an ETag, for consumers that poll (FR-145).

**Change Set** — A group of change requests that ship with one controller software release, shown and queued together. Grouping changes presentation only: each request keeps its own decisions (FR-124).

**Chief Engineer** — System role. Performs the final Approval decision after both required Review sign-offs (Reviewer and Administrator) are complete. Cannot approve a change request they authored, or one they already signed off on as Reviewer or Administrator (segregation of duties).

**Code Number** — See Status Code Identifier (StCd).

**Controller Software Version** — An entry of the ordered vocabulary of controller software versions. A revision declares an inclusive from/to range of versions it applies to; a Release targets one or more versions (FR-106, decision D-01).

**Covert** — A value that appears in several audience-access vocabularies. Its business meaning is unconfirmed (it may be a mistranslation of "Covered"); the system treats it as *not visible* to that audience until the business defines it (decision D-02, assumption A-010).

**Cross-Domain Sign-Off** — The workflow step where a second Engineer, holding an Engineering Domain the originating Engineer does not, completes the fields tagged to that domain before a Change Request can be submitted for Review (05-governance-handbook.md §6a).

**Delegation** — Out-of-office cover: a Reviewer, Administrator or Chief Engineer names a delegate for a date range. The delegate acts as themselves, for the decision actions of that role only, under full segregation of duties; the audit entry names both (FR-125, BR-017, decision D-08).

**Deprecated** — Lifecycle state for a previously Released status code that is no longer active but is retained for historical/service reference.

**Draft** — Initial, freely editable lifecycle state. A status code in Draft has no fixed Status Code Identifier — the identifier is allocated only when the Change Request is submitted for Review (05-governance-handbook.md §2).

**Dry Run** — An import validation that reports every problem per row and column and creates nothing, not even an import job (FR-048j).

**Engineer** — System role. A controls engineer or cross-functional engineer (e.g. electrical, mechanical) who authors and edits status codes. Tagged with one or more Engineering Domains.

**Engineering Domain** — Classification of an Engineer's specialty (e.g. Controls, Electrical, Mechanical, Grid, Safety). Used to route Cross-Domain Sign-Off requirements.

**Evidence** — A file attached to a change request — test report, simulation, design note, safety assessment. Allow-listed types, content-checked, at most 10 MB and 20 per request, stored outside the web root, removable only while the request is a Draft (FR-130).

**Export Profile** — An Administrator-managed, named column set with header labels and an optional default audience and language, used to shape an export (FR-100).

**Field Comment** — A comment a Reviewer, Administrator or Chief Engineer attaches to one specific field of a change request in Review or Pending Approval; the author sees open ones inline and resolves them (FR-127).

**Fleet Feedback** — Anonymised occurrence counts per status code and period, imported from the monitoring side, used to find codes that never fire and those that fire most (FR-143).

**Functional Subgroup** — A sub-division of a Functional System Group, **mandatory on every Status Code — never optional** (corrected 2026-09-17). Most subgroups own a 100-number sub-band aligned to the hundreds digit of the identifier (e.g. `020xx` = 02000–02199 for the first subgroup of a group, which owns 200 numbers; later ones such as `022xx` = 02200–02299 own 100); within Turbine Control & Operation, several subgroups share the `099xx` block in finer ten-number sub-bands, named `0990x` … `0999x`. A subgroup code is the first digits of its band with `x` for the free positions — never a dash or a letter (`110xx`, `1110x`). The real taxonomy, corrected 2026-09-17 against an authoritative row-level export (the earlier hand-typed summary used incorrect subgroup names), is seeded in full (06-data-dictionary.md §9a). Unassigned blocks within a group are deliberate reserved capacity — an Administrator can create a new subgroup there at any time, provided it does not overlap an existing one.

**Functional System Group** — The primary classification and numbering axis for status codes. Twelve groups as of 2026-09-17: nine Main Controller groups (WCNV, WGEN, WNAC, WROT, WTOW, WTRF, WTRM, WYAW, WTUR, ranges 1000–9999) plus three Hub Controller groups added from a real export (WTUR 11000–11999, WROT 12000–12999, WPPD 13000–13999) — see 05-governance-handbook.md §2. The four-letter prefix is **not** a unique key on its own: `WTUR` and `WROT` are each intentionally reused across a Main Controller group and a Hub Controller group with a different numeric range — always resolve by range, not prefix alone. `10000–10999`, `14000–14999`, `15000–15999`, and `16000–16999` are confirmed free/reserved capacity for future groups, not currently assigned to anything.

**Hub Consolidation** — Moving the status codes of the Hub Controller to the Main Controller side without renumbering: Main Controller drafts created from Hub codes, a mapping report, and bulk deprecation of the Hub codes once replaced (FR-147, assumption A-008).

**Import Job** — A record of a CSV or XLSX status code library upload (new 2026-09-17). Every row that passes validation becomes an ordinary Draft Change Request subject to the full governance cycle — import is a faster data-entry path, never a bypass (05-governance-handbook.md §6b). Row failures are reported per-row and create nothing. Since v4 it also records its mode (`CREATE` or `UPDATE`), progress and warning counts, and runs in the background above a row threshold.

**Legacy Mapping** — Which new status code replaces which legacy number, for the Main Controller and the Hub Controller separately: the code's `legacy_reference_number` read with its controller type and its identifier (or the number it has reserved). It runs from legacy to new only — the new library holds more codes than the old one, so a code without a legacy number is normal (*n/a*) and nothing maps back (FR-048u).

**Legacy Reference Number** — Free-text field on a Status Code preserving a pre-migration/source-system number (e.g. the old "Status Code Number" seen in the legacy tool) carried through library import, for traceability only — never mistaken for the governed StCd identifier (06-data-dictionary.md §1, §12).

**Logical Node** / **Node Value** — Derived, read-only technical addressing fields on a Status Code Revision, always equal to the parent Functional System Group's prefix and sort order respectively. Exist in the real export as their own columns but carry no information CSCM Tool doesn't already have from the group assignment (06-data-dictionary.md §2e).

**Manifest** — The `MANIFEST.json` that accompanies an export: release, scope, row count, SHA-256 of every file, content digest, generator, timestamp and applied options, signed with HMAC-SHA-256 when `MANIFEST_SIGNING_KEY` is configured. A file can be verified against it without the database (FR-103, FR-104).

**Master Database** — CSCM Tool's own on-premises server database. It is the single system of record; no external "master" system exists upstream of it. Data leaves only via Administrator-triggered export (08-system-architecture.md §6).

**Notice** — An in-app message for whoever holds the next decision on a stalled change request (and anyone covering for them), created at most once per user, request, stage, level and day; optionally also mailed through the organisation's relay (FR-121, decision D-04).

**Offline Bundle** — A single self-contained HTML page generated from a Release, with the codes embedded and a search box, for use at the turbine without connectivity (FR-108).

**OneTool** — The shared internal tools platform CSCM Tool integrates with visually (shared top bar, sidebar, design tokens, and component treatments — 10-ui-ux-specification.md §0). CSCM Tool keeps its own login and credential store; only the visual shell is shared, not authentication (confirmed decision, 2026-09-17).

**PendingApproval** — Lifecycle state entered automatically once both required Review sign-offs (Reviewer and Administrator) are recorded. Awaiting Chief Engineer decision.

**Planned Date** — A planned effective date or planned deprecation date stamped on the current revision by an Administrator. It warns at release time and appears in the health report but never changes a lifecycle state (FR-109).

**Platform Variant Link** — An optional cross-reference between two independent Status Code records that represent the same underlying condition on different Turbine Platforms. Used when a code was renamed or regenerated between platforms rather than being modeled as a single multi-platform record (05-governance-handbook.md §2a). Since v4 it is created by the *Create platform variant* action (FR-094).

**Product Owner** — Organizational title equivalent to the Administrator role in CSCM Tool.

**Program Reference Fields** — Eight numeric fields (Yaw Program, Manual Reset Program, Auto Reset Program, Converter Reactive Power Program, Brake Program, Umrichterprogramm GSC, Umrichterprogramm MSC, Yaw Bearing Lubrication Program) referencing controller-firmware subroutine numbers CSCM Tool does not itself govern — soft-validated against observed values, not hard-enforced lookups, since the descriptive meaning of each code is not available from source data (06-data-dictionary.md §2c).

**Readiness Probe** — `GET /api/v1/health/ready`: database reachable, schema at the expected Alembic head, newest audit entries chain correctly, last verified backup recent. 200 with status `ok` or `degraded`, 503 when not ready (FR-152).

**Reconciliation Report** — The migration progress of the legacy library: rows imported, in review, approved, released, retired and — given the legacy master list — the legacy numbers still missing (FR-048l).

**Release** — A named, versioned, immutable bundle of Approved status code revisions, published by the Administrator. Since v4 it may target one or more controller software versions and has generated release notes and a signed manifest on every export.

**Release Notes** — A generated document listing the codes a Release added, changed (with the field-level diff) and deprecated compared with the previous published Release (FR-105).

**Released** — Lifecycle state reached when a revision is included in a published Release; authoritative and citable.

**Remedy Text** — An optional field with the recommended action for service staff, on a revision and per translation (FR-131).

**Reserved Identifier** — The number an imported `StCd_<n>.st` program already carries, held for the Draft created from it (`status_code.reserved_identifier`). It is issued unchanged at Submit for Review; the allocator skips it, no override can take it and no other code can be given it (BR-023).

**Review Checklist** — Administrator-defined items, per Functional System Group or for all, that an approving Reviewer must confirm; the confirmed wording is stored with the sign-off (FR-128).

**Reviewer** — System role. Organizationally the Sub-PO for Status Codes. One of the two mandatory Review sign-offs, alongside the Administrator.

**Review** — Lifecycle state entered on submission. Requires two independent sign-offs (Reviewer and Administrator) before automatically advancing to PendingApproval. Either sign-off may reject back to Draft with a mandatory comment.

**Row Version** — A counter on each revision that increases on every save. A save based on an older value is refused with 409 and nothing is overwritten (FR-090, BR-019).

**Sandbox Status Code** — A test-only status code created by an Administrator, drawn from an isolated `StCd-T#####` identifier band outside the real Functional System Group ranges. Never included in a Release, catalogue export, or manual. The only category of record that may be permanently deleted (05-governance-handbook.md §12).

**Segregation of Duties** — The rule that no single person may both author and decide on the same Change Request at any of the three decision points (Reviewer sign-off, Administrator sign-off, Chief Engineer approval).

**SLA (Service Level)** — How long a change request may wait at its stage, in business days, before it is shown amber and then red; thresholds are Administrator settings (defaults review 3 / 5, approval 2 / 3) (FR-120).

**Status Code** — The governed identity record for a wind turbine controller status/fault/warning condition, identified by its Status Code Identifier (StCd).

**Status Code Identifier (StCd)** — The five-digit, zero-padded human identifier, e.g. `StCd-01232`. The numeric value is the code's position within its Functional System Group's range (e.g. 1000–1999 for Converter & Grid Interface), so the identifier itself encodes classification. Fixed only at the Draft → Review transition, never before.

**StCd Owner** — *(v4.3)* System role. The owner of the status code library: reads the whole library and the workflow without acting, and may change a user's role between Viewer, Engineer and Reviewer — nothing else about a person, and never a higher role. Creating users and all other role changes stay with the Administrator (BR-024). Shown purple; the colour of a role badge is its level, red is the highest (the Administrator).

**Status Code Revision** — A specific versioned set of attribute values for a Status Code, carrying its own lifecycle state. Field set corrected 2026-09-17 against a real 897-row library export — see 06-data-dictionary.md's provenance note for the full list of corrections (Status Category is Error/Warning/Info; Available Group is numeric; Alarm is boolean; Set/Reset Delay are free text with unit; Manual and Automatic Reset are separate fields; eight Audience Access fields replace the single Access Rights enum; eight numeric Program Reference fields; repeated-error escalation fields; Logical Node/Node Value derived fields).

**StCd Program** — One `PROGRAM StCd_<n>` of the generated controller code, written in IEC 61131-3 Structured Text: a status code with its number, name, delays, repeat rule, alarm and availability settings, subsystem programs and user-group levels. The status code import reads these programs as text, without running them (FR-048o).

**Step-up** — Re-entering the actor's own password for a sensitive action — Reviewer or Administrator sign-off, Chief Engineer decision, publishing a Release, the full-database export. A missing password gives `step_up_required`, a wrong one `step_up_failed`; both are audited (FR-126, SEC-026, decision D-07).

**Translation** — The title, description and remedy text of a revision in a language other than the English source, with a status of MISSING, DRAFT or APPROVED; approved by someone other than the translator (FR-110, BR-018, decision D-03).

**Turbine Platform** — A multi-select classification (minimum seed values `2XM`, `3XM`, `4XM`, extensible) indicating which turbine platform(s) a status code revision applies to. See Platform Variant Link for cross-platform divergence handling.

**Update Mode** — An import mode keyed on `legacy_reference_number`: a changed row revises the open Draft in place or opens a new revision of a Released code, an unchanged row is skipped, an unmatched row is created (FR-048k).

**Viewer** — System role. Read-only consumer of Approved/Released/Deprecated/Archived data.

**WCNV / WGEN / WNAC / WROT / WTOW / WTRF / WTRM / WYAW / WTUR / WPPD** — Four-letter prefixes identifying each Functional System Group (Converter & Grid Interface, Generator System, Meteorology & Nacelle Environment, Rotor & Pitch System, Tower & Structure, Transformer & MV System, Drivetrain & Gearbox, Yaw System, Turbine Control & Operation, and Wind Farm / Plant Dispatch respectively). `WROT` and `WTUR` each also identify a second, Hub Controller group with a different numeric range (12000–12999 and 11000–11999 respectively, added 2026-09-17) — see Functional System Group. Displayed alongside the StCd identifier for cross-reference, not part of the identifier itself.


**Webhook** — A registered internal URL that receives a signed `POST` when a Release is published. Targets must be private or loopback addresses, redirects are not followed, a failure never affects the publish (FR-146, SEC-028).

**Where-used** — The list, on a code's detail page, of other codes whose current revision refers to it (repeated-error pointer, related codes, supersession, platform variant); deprecating a code with live dependants requires acknowledging them (FR-092).

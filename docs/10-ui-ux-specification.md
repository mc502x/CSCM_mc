# 10. UI/UX Specification — CSCM Tool

## 0. OneTool Design System Integration

CSCM Tool is a **OneTool-integrated application** (2026-09-17 decision): it renders inside the shared OneTool shell (top bar, sidebar, navigation) rather than as a standalone page shell, following the canonical `ONETOOL_UI_DESIGN.md` design system supplied by the central tools team. Per the explicit decision on authentication scope (03-srs.md, 11-security-architecture.md §2), CSCM Tool **keeps its own login and its own user/credential store** — only the *visual* shell, tokens, and component treatments are shared, not identity or session.

**What is shared (adopt as-is, do not reinvent):**
- Shared top bar (64px, fixed) and sidebar (256px, fixed) — CSCM Tool's own pages occupy only the main workspace region (`margin-left: 256px`, `padding: 32px`, `padding-top: 96px`), using `max-width: 1280px` (CSCM Tool qualifies as a "dense data tool" per the design system's own guidance, given its tables and multi-section forms).
- Design tokens: `--ot-primary #002e6d`, `--ot-background #f7f9fb`, `--ot-surface-raised #fff`, `--ot-error #ba1a1a`, and the full token set in the design doc — CSCM Tool introduces no new primary color, font, or button style.
- Typography: Manrope (headings), Inter (body/labels/controls), Material Symbols Outlined icons.
- Component treatments: cards (12px radius, soft shadow), buttons (primary/secondary/outline/danger per the design doc's table), form inputs (40px height, 8px radius, blue focus ring), tabs, alerts, loading/empty states — all per the design doc verbatim.
- Responsive/accessibility rules: sidebar collapse at tablet width, 16–20px mobile padding, 44×44px minimum pointer targets, WCAG AA contrast.

**What CSCM Tool still owns:**
- Its own login screen (S1) and Account Settings (S18) — not delegated to OneTool, per the auth-scope decision.
- Its own navigation item within the OneTool sidebar (marked active when a CSCM Tool page is open), registered once, not duplicated.
- All domain-specific screens, forms, and workflow (S2–S17 below).

**Integration checklist** (from the design doc, applied to CSCM Tool specifically): render the shared shell with the CSCM Tool nav item active; use the standard main workspace offsets; use the documented tokens/components exclusively; test desktop, collapsed-sidebar, tablet, keyboard-only, loading, error, and empty states before release (15-development-standards.md).

## 1. Screen Inventory

| # | Screen | Primary Role(s) | Purpose |
|---|---|---|---|
| S1 | Login | All | Authenticate (CSCM Tool's own — not delegated to OneTool) |
| S2 | Dashboard | All | Role-relevant summary + quick links |
| S3 | Status Code List / Search | All | Browse, filter, search all codes (sandbox excluded by default) |
| S4 | Status Code Detail | All | View current revision, history, related CR |
| S5 | New Status Code | Engineer, Administrator | Create a new code (Draft, no fixed identifier yet) |
| S5a | New Sandbox Status Code | Administrator | Create a test code from the isolated StCd-T##### band |
| S6 | Edit Status Code Revision | Engineer | Edit a Draft |
| S7 | Revision History / Diff | All | Compare any two revisions |
| S8 | My Change Requests | Engineer | Track own submissions, incl. pending domain sign-off requests; tick several and **Withdraw selected** (v4.6) |
| S9 | Review Queue | Reviewer, Administrator | List CRs awaiting their sign-off |
| S9a | Approval Queue | Chief Engineer | List CRs in PendingApproval awaiting final decision |
| S10 | Change Request Detail / Decision | Reviewer, Administrator, Chief Engineer | Sign off / approve / reject with diff + comments + domain sign-off status |
| S10a | Domain Sign-Off Request | Engineer (second domain) | Complete domain-owned fields, record sign-off |
| S11 | Release List | All | Browse releases |
| S12 | Release Builder | Administrator | Build candidate set, publish |
| S13 | Release Detail | All | View published contents, export |
| S14 | User Management | Administrator, StCd Owner (roles only) | CRUD users, roles, Engineering Domain tags; every role is a coloured badge, red = highest level; the StCd Owner sees the list and moves users between Viewer, Engineer and Reviewer (v4.3). Per user: **View** (the user's page, `/admin/users/{id}`: profile and what the account has done), **Edit**, **Deactivate / Activate** and **Delete** (v4.6; delete only while the account has no history and with the Administrator's password) |
| S15 | Lookup/Vocabulary Management | Administrator | Manage Functional Groups/Subgroups (incl. create new — §4 S15), Turbine Platforms, Engineering Domains, Available Group, the 8 access vocabularies |
| S16 | Audit Log Search | Administrator, Reviewer/Chief Engineer (scoped) | Investigate history |
| S17 | Export Center | All (scoped by role); Full-Database Export | Ad-hoc catalogue exports (CSV/JSON/XLSX/PDF); full DB export (Administrator only) |
| S18 | Account Settings | All | Change own password (CSCM Tool's own) |
| S19 | Library Import | Engineer, Administrator | Upload CSV/XLSX, review progress and errors; since v4 template download, **Validate only** dry run, mode (create / update), background progress |
| S20 | Import Reconciliation ("Migration progress") *(v4)* | Engineer, Administrator | Legacy rows imported / in review / released / still missing, with the master list uploaded to name the missing numbers (`/imports/reconciliation`) |
| S21 | Notices *(v4)* | All | The user's in-app notices, mark as read (`/notifications`) |
| S22 | Delegation *(v4)* | Reviewer, Chief Engineer, Administrator | Name a delegate for a date range, see and revoke delegations (`/delegation`) |
| S23 | Change Sets *(v4)* | Administrator, Engineer, Reviewer, Chief Engineer (create: not Reviewer) | List, create, open a set, add or remove requests, decide several in one sitting (`/change-sets`) |
| S24 | Stalled Requests *(v4)* | Administrator | Requests past their amber/red SLA with reassignment and Reviewer workload (`/admin/stalled`) |
| S25 | Translations *(v4)* | All (Viewers see approved text only) | Status per language, edit, approve, carry over (`/status-codes/{id}/translations`) |
| S26 | Release Notes, Shaped Export, Offline Bundle *(v4)* | All | Added / changed / deprecated against the previous Release; export with profile, audience, language, version and bundle; offline lookup page (`/releases/{id}/notes`, `/shaped-export`, `/offline-bundle`) |
| S27 | Software Versions *(v4)* | All | The version matrix and the changes between two versions (`/software-versions`) |
| S28 | Verify a File *(v4)* | All | Upload an export and optionally its manifest; result of the hash and signature check (part of S17, posts to `/exports/verify`) |
| S29 | Catalogue Health *(v4)* | Administrator, Reviewer, Chief Engineer | Capacity forecast (Main Controller rows blue, Hub Controller rows light blue, each with an MC / HC chip), missing data, inconsistencies, unused numbers, upcoming dates (`/reports/catalogue-health`) |
| S30 | Success Metrics *(v4)* | Administrator, Chief Engineer | The business-case KPIs (`/reports/success-metrics`) |
| S31 | Fleet Feedback *(v4)* | Administrator, Chief Engineer | Import occurrence counts; never-fired and most-frequent codes (`/reports/fleet-feedback`) |
| S32 | Hub Consolidation *(v4)* | Working roles (actions: Engineer, Administrator) | Mapping of Hub codes to Main replacements; create MC draft; bulk deprecation (`/hub-consolidation`) |
| S33 | Export Profiles *(v4)* | Administrator | Column sets, default audience and language (`/admin/export-profiles`) |
| S34 | Review Checklist *(v4)* | Administrator | Checklist items per Functional System Group (`/admin/review-checklist`) |
| S35 | Settings *(v4)* | Administrator | SLA thresholds, reviewer auto-assignment, capacity alert (`/admin/settings`) |
| S36 | Integrations *(v4)* | Administrator | API tokens and webhooks with delivery log (`/admin/integrations`) |
| S37 | Operations *(v4)* | Administrator | Backup status, audit-chain verification (`/admin/operations`) |
| S38 | Help *(v4)* | All | Per-role quick start, glossary of states, roles and terms (`/help`) |
| S39 | Import from .st files *(v4.2)* | Engineer, Administrator | Upload several generated `StCd_<n>.st` files, a folder or a ZIP (`/imports/st`), read the preview, tick the programs to import, confirm into Drafts in one change set; programs that differ from a code already in the catalogue offer **update the Draft**, **new revision** or **restore** (not ticked by default, v4.6) |
| S40 | Legacy mapping *(v4.2)* | Engineer, Administrator, Reviewer, Chief Engineer | Legacy number → new identifier with filters and CSV/XLSX export (`/legacy-mapping`); legacy → new only |
| S41 | Windows sign-in *(v4.7)* | All | The page behind *Sign in with your Windows account* (`/login/windows`): in a deployment the gateway has already told the application who the user is and the page signs them in; on a developer machine it asks for the identity the gateway would have supplied (`/login/windows/simulate`) |
| S42 | Translations *(v4.7)* | Reviewers of a language, Administrator, StCd Owner | The languages the user may review with the state of each (not reviewed, in progress, reviewed, changed since the review); managers see all languages (`/translations`) |
| S43 | Translation review *(v4.7)* | Assigned reviewers | One row per string with screens, English, current translation, verdict, proposal and comment; the missing translations; XLSX sheet download and upload (`/translations/{language}`) |
| S44 | Translation decisions *(v4.7)* | Administrator, StCd Owner | Reviewers of the language, proposals waiting for a decision, accepted overrides, recent decisions (`/translations/{language}/decisions`) |
| S45 | Terminology *(v4.9)* | Everybody signed in; managers add and change terms | The vocabulary: coverage per language, the terms with category, definition and the state of every language, search and filter, add a term (`/terminology`) |
| S46 | Terminology of a language *(v4.9)* | Everybody signed in; the technical roles propose, the approving roles approve | One row per term with the English text, the proposal and its state; save translations, send back with a note, approve one or all drafts of others; XLSX and CSV export (`/terminology/{language}`) |
| S47 | Terminology check *(v4.9)* | Everybody signed in | The interface strings that contain a term whose translation is missing from the translation of the string (`/terminology/{language}/check`) |
| S48 | Withdrawn Codes *(v4.9)* | Administrator | The codes whose last revision was withdrawn and that still hold a number, a legacy number or a PrgIdx_GUi; tick, enter the password, delete (`/admin/withdrawn-codes`) |

## 2. Navigation Map

```
[OneTool shared top bar + sidebar, CSCM Tool nav item active]
  Login (S1, CSCM Tool's own)
  └─▶ Dashboard (S2)
        ├─▶ Status Codes (S3) ──▶ Status Code Detail (S4) ──▶ Revision History/Diff (S7)
        │                                │
        │                                └─▶ Edit Revision (S6) [Engineer, own open CR]
        │
        ├─▶ New Status Code (S5) [Engineer/Admin] ──▶ Status Code Detail (S4)
        ├─▶ New Sandbox Status Code (S5a) [Admin only] ──▶ Status Code Detail (S4, sandbox-flagged)
        ├─▶ Library Import (S19) [Engineer/Admin] ──▶ My Change Requests (S8) [imported Drafts appear here]
        ├─▶ Import from .st files (S39) [Engineer/Admin] ──▶ Import job ──▶ Change Sets (S23) [the batch change set]
        ├─▶ Legacy mapping (S40) [every role except Viewer]
        ├─▶ Translations (S42) [reviewers of a language, Administrator, StCd Owner] ──▶ Review (S43) / Decisions (S44)
        │
        ├─▶ My Change Requests (S8) [Engineer] ──▶ Domain Sign-Off Request (S10a) [if flagged]
        │
        ├─▶ Review Queue (S9) [Reviewer/Admin] ──▶ Change Request Detail/Decision (S10)
        ├─▶ Approval Queue (S9a) [Chief Engineer] ──▶ Change Request Detail/Decision (S10)
        │
        ├─▶ Notices (S21) · Help (S38) · Language switch [every role, top bar]
        ├─▶ Change Sets (S23) · Delegation (S22) [decision roles] · Stalled Requests (S24) [Admin]
        │
        ├─▶ Insight: Catalogue Health (S29) · Success Metrics (S30) · Fleet Feedback (S31) · Hub Consolidation (S32)
        │
        ├─▶ Releases (S11) ──▶ Release Detail (S13) ──▶ Notes / Shaped Export / Offline Bundle (S26) ──▶ Export Center (S17)
        │         └─▶ New Release / Release Builder (S12) [Admin]
        │
        ├─▶ Administration [Admin only, top-level menu]
        │         ├─▶ User Management (S14)
        │         ├─▶ Lookup Management (S15) ──▶ New Subgroup form (non-overlap validated)
        │         ├─▶ Export Profiles (S33) · Review Checklist (S34) · Settings (S35)
        │         ├─▶ Integrations (S36) · Operations (S37)
        │         ├─▶ Audit Log (S16)
        │         └─▶ Full-Database Export (S17, Admin-only section)
        │
        └─▶ Account Settings (S18) [every role, via user menu]
```

## 3. Role-Based Navigation Visibility

| Nav Item | Administrator | Engineer | Reviewer | Chief Engineer | Viewer |
|---|---|---|---|---|---|
| Status Codes | ✓ | ✓ | ✓ | ✓ | ✓ |
| New Status Code | ✓ | ✓ | — | — | — |
| New Sandbox Status Code | ✓ | — | — | — | — |
| Library Import | ✓ | ✓ | — | — | — |
| My Change Requests | ✓ | ✓ | ✓ (as any submitter) | ✓ | — |
| Review Queue | ✓ | — | ✓ | — | — |
| Approval Queue | — | — | — | ✓ | — |
| Releases | ✓ | ✓ (read) | ✓ (read) | ✓ (read) | ✓ (read) |
| Release Builder | ✓ | — | — | — | — |
| Administration menu | ✓ | — | — | — | — |
| Full-Database Export | ✓ | — | — | — | — |
| Catalogue Export Center | ✓ | ✓ | ✓ | ✓ | ✓ (Released/Approved only) |
| Notices, Help, Software Versions | ✓ | ✓ | ✓ | ✓ | ✓ |
| Change Sets | ✓ | ✓ | ✓ | ✓ | — |
| Delegation | ✓ | — | ✓ | ✓ | — |
| Stalled Requests | ✓ | — | — | — | — |
| Catalogue Health | ✓ | — | ✓ | ✓ | — |
| Success Metrics, Fleet Feedback | ✓ | — | — | ✓ | — |
| Hub Consolidation | ✓ | ✓ | ✓ | ✓ | — |
| Export Profiles, Review Checklist, Settings, Integrations, Operations | ✓ | — | — | — | — |

## 4. Wireframe Descriptions

### S5 — New Status Code
*(v4)* The form additionally offers the optional remedy text, affected component, related codes, standard references and the software-version range; shows a **capacity hint** for the chosen subgroup ("158 numbers left in this band"); warns, without blocking, about unknown or retired references and similar titles after saving; and on a stale save (409) re-shows the user's entries beside the current values and the current `row_version`.

A single-page form on the standard `ot-card` surfaces, laid out in labeled sections per the design system's two-column grid guidance:

1. **Classification** — Functional System Group (dropdown, required) → Functional Subgroup (dependent dropdown, populated from the selected group, **required — never optional**, disabled with a "select a Functional System Group first" hint until a group is chosen) → Turbine Platform (multi-select chip input, at least one required). The identifier field shows **"Not yet assigned — fixed on Submit for Review"**, never a real or placeholder number; a small, explicitly-labeled non-binding grey preview may appear ("likely next: `StCd-01233` — not reserved").
2. **Description** — Title, Description.
3. **Status & Timing** — Status Category (Error/Warning/Info), Available Group (numeric picker, sourced from the soft-validated lookup), Alarm (checkbox), Set Delay / Reset Delay (each a value + unit-select pair — ms/s/min/h/d — composed into the stored free-text form, so Engineers never have to type the unit suffix by hand), Up/Down Counter, Trigger Snapshot, Loadless Spinning Permitted (checkboxes).
4. **Repeated-Error Escalation** (collapsible, optional) — Number of Times Repeated, Repeated Over the Course (value + unit), Status Code for Repeated Error (plain numeric field, labeled "reference number in the separate escalation code pool — not a CSCM Tool status code").
5. **Program References** (collapsible, labeled "Advanced — controller firmware programs", CONTROLS-domain-owned) — Yaw Program, Manual Reset Program, Auto Reset Program, Converter Reactive Power Program, Brake Program, Umrichterprogramm GSC, Umrichterprogramm MSC, Yaw Bearing Lubrication Program — each a plain numeric field with the currently-observed valid values shown as a soft-suggestion list (autocomplete), not a hard-enforced dropdown, since the firmware-side table can grow independently of CSCM Tool (06-data-dictionary.md §2c).
5a. *(v4.9, FR-168)* **Further Program References** (collapsible: the 13 Main Controller programs, then the 3 Hub Controller programs), **Operation Parameters** (operating-mode mask as a bit string, task call frequency, the flags as *not captured / Yes / No*) and **User-Group Levels** (a read and a write level for each of the 16 slots). The detail page shows the sections of the controller of the code and the levels that exist.
6. **Audience Access** (Governance-restricted — badge "Proposed, confirmed by Product Owner at review" on every field, per §5 below) — eight independent dropdowns: Development, Sales, TCC, Service, Turbine Operator Package, Grid Operator, Service Partner, Customer.
7. **Ownership** — Owner (defaults to current user).

If the current Engineer's tagged Engineering Domain(s) do not cover a required domain (e.g. Program References is CONTROLS-owned and the originating Engineer is Electrical), that section is marked **"Needs Controls input"** with a "Request Domain Sign-Off" button; Submit for Review stays disabled until every required `DomainSignoff` exists.

**No data loss on failure (explicit fix, 2026-09-17):** a failed Submit-for-Review or Save never clears the form. The legacy tool resets all fields on any creation failure — flagged directly by the business as "cumbersome." CSCM Tool's client keeps every entered value in place after a 422 response and highlights only the specific invalid fields inline (per §9's inline-validation pattern); nothing is ever discarded because of a validation error, a network retry, or a session-timeout-triggered re-login.

Sticky footer: "Save as Draft" (secondary) and "Submit for Review" (primary, disabled until validation and all domain sign-offs pass).

### S5a — New Sandbox Status Code (Administrator only)
Same form as S5, minus the Functional Group/Subgroup/numbering section — a persistent banner reads **"Sandbox status code — never numbered from a real range, never released, deletable."** The resulting record's identifier is shown as `StCd-T#####`, with a red "SANDBOX" badge visible everywhere the code appears, and a "Delete Permanently" button on S4 for this record only, gated behind a typed-confirmation modal.

### S19 — Library Import
1. **Upload** — drag-and-drop or file picker for a `.csv` or `.xlsx` file, with a short format note ("one row per status code; column headers must match the exported template — download a template from here").
2. **Progress** — once uploaded, the job runs (in the background above the row threshold); the screen polls the progress endpoint and shows a bar with `processed_count` of `row_count` plus `created_count`, `error_count` and `warning_count`.
*(v4)* Before importing, **Template** (CSV or XLSX) downloads the exact headers and lookup codes; **Validate only** runs the dry run and shows every problem per row and column with the value and a fix hint, and a banner states that nothing has been created; the **mode** selector chooses *create* or *update* (matching on the legacy number). Warnings (similar titles) are listed but do not block.
3. **Result** — on completion, a summary ("128 of 134 rows imported as Drafts, 6 failed validation") with "Download error report" links (CSV and XLSX; row, column, value, problem, how to fix) and a "View imported Drafts" link to My Change Requests (S8), filtered to this import job. Imported rows are ordinary Drafts — the screen never implies they are already Approved.

### S39 — Import from .st files *(v4.2)*
1. **Upload** — the generated `StCd_<n>.st` files (several at once), a whole folder or a ZIP; options: controller (detect / Main / Hub), the new number of Hub programs (proposal 1 five-digit, the default, or proposal 2 inside the Main scheme), the status category of the new codes (the files carry none) and the turbine platforms. A note states that every imported program becomes an ordinary Draft with its number reserved.
2. **Preview** — nothing is created. Chips count files, programs, ready, already in the catalogue, blocked, warnings and programs without a legacy number. One row per program: a checkbox (disabled unless the program is ready), new identifier, legacy number (*n/a* when there is none), controller, name with file and line, group and subgroup, state, and every problem and warning. A header checkbox selects every ready program, a filter box narrows the list by text. Optional name of the change set.
3. **Create Drafts** — creates the ticked programs (a large batch runs in the background with the progress bar of S19) and opens the import job page, which links to the batch change set (S23); **Cancel** discards the staged upload.

### S40 — Legacy mapping *(v4.2)*
Chips: codes with a legacy number (Main / Hub), the number of new codes without one (*n/a*), and how many identifiers are issued, reserved or not yet assigned. Filter by text, controller and number state. Table: controller, legacy number, new identifier, number state, name and lifecycle state; a row opens the status code. CSV and XLSX export honour the filter. The page says that the mapping runs from legacy to new only.

### S41 — Windows sign-in *(v4.7)*
The login page shows the password form, the link *Sign in with your Windows account*, or both, as `AUTH_MODE` says (FR-163). The Windows page signs in the account that matches the identity of the gateway and says clearly when there is no account ("No active account matches this Windows identity") or when no identity arrived (*No Windows identity reached the application* — the gateway is not configured or the request did not come from a trusted proxy). On a developer machine (`WINDOWS_AUTH_SIMULATE`) it shows a field for the identity and a note *Simulation.* that says a deployment signs in without this page; the production configuration never shows it. In `windows` mode the account page offers no password change. The e-mail address of a user is shown as fixed in the user form and the user view (FR-162).

### S42 — Translations *(v4.7)*
A table of the languages the user reviews (all languages for an Administrator or StCd Owner): flag and name, strings translated and missing, the state of the language, the date of the last completed review, *Review* and, for managers, *Decisions and reviewers*. A user who reviews nothing sees a note instead of the table; the sidebar entry appears only for reviewers and managers.

### S43 — Translation review *(v4.7)*
The header shows the answered strings of the total as a bar, a *What to check* checklist and the two views *Check translations* and *Missing translations*; a filter by text, screen and answer; 40 rows per page. A row has the screens and the string id, the English, the current translation (right to left for Arabic and Urdu), three radio buttons OK / CHANGE / UNCLEAR, a proposal box and a comment. *Mark the rest of this page OK* answers the rows without a verdict; *Save* and *Save and next page* store the page; a row that is decided is locked. *Download the sheet* and *Upload* are the offline route. *Complete the review* is possible when every translated string has a verdict, otherwise the message says how many are missing.

### S44 — Translation decisions *(v4.7)*
Three blocks: the reviewers of the language (remove, and assign any active user), the proposals waiting for a decision — string, current text, what the reviewer says; **Accept** with the text pre-filled and editable, **Reject**, or for an UNCLEAR item **Noted** and **Dismiss**; a proposal of the signed-in manager shows a note instead of buttons — and the accepted overrides with *Remove*, followed by the recent decisions.

### S15 — Lookup/Vocabulary Management, incl. New Subgroup and New Functional System Group
In addition to the original vocabularies, an Administrator can select a Functional System Group and click "Add Subgroup," entering a name and a proposed numeric sub-range. The form shows the group's existing subgroups and their ranges visually (a simple horizontal bar from `range_start` to `range_end` with existing subgroups shaded and reserved blocks highlighted) and pre-fills a suggested next hundred-aligned free block. Submitting a range that overlaps an existing subgroup returns the specific conflict inline ("overlaps 'Hot Air De-icing' (4200–4299)") without losing the entered name — the same no-data-loss principle as S5.

A second, top-level "Add Functional System Group" action (new 2026-09-17, FR-048g/h) works the same way one level up: an overview strip shows the full 1000–16999 span with occupied groups (including both the Main and Hub Controller ranges) shaded and the confirmed free bands (`10000–10999`, `14000–14999`, `15000–15999`, `16000–16999`) highlighted as available. The Administrator enters a code, label, and range within a free band; an overlapping range is rejected inline the same way, naming the conflicting group, without losing the entered name.

### S4 — Status Code Detail
*(v4)* Additional panels: **Where-used**, **Family** (platform variants) with *Create platform variant*, **reference and similar-title warnings**, **planned dates** (Administrator), **remedy, component, related codes and standards**, the software-version range, and a link to **Translations** (S25). The list (S3) offers ranked, typo-tolerant search, sort links, paging, a **column chooser**, **Save search** and a share link. Header band: Status Code Identifier (or "Not yet assigned" for Draft) + Title + Lifecycle State badge (§6) + Functional System Group **and Functional Subgroup** tags (both always present) + Turbine Platform chips. A red "SANDBOX" badge replaces the identifier styling for sandbox records. Tabs: **Current**, **History**, **Change Requests**. Action buttons (role- and state-gated): "Open New Revision" (Engineer, if no open CR), "Deprecate" (Administrator, if Released), "Delete Permanently" (Administrator, sandbox only).

### S9a — Approval Queue (Chief Engineer)
Table: Identifier, Title, Functional Group/Subgroup, Reviewer (who signed off), Administrator (who signed off), Age since both sign-offs completed. Row click → S10. *(v4)* An **SLA chip** (days waited, amber/red) replaces the plain age column on this queue and on the Review Queue; the Review Queue also shows the assigned Reviewer.

### S10 — Change Request Detail / Decision
Split layout: left panel field-level diff (now covering every field category in §4 S5); right panel CR metadata, a **Sign-Off Status strip** (Reviewer / Administrator / Chief Engineer, each pending or signed-with-name-and-date), and a **Domain Sign-Off strip**. Action buttons render per the viewer's role and the CR's current state, hidden entirely (not merely disabled) for the CR's own author and, at the Chief Engineer stage, for whichever individuals already signed off as Reviewer or Administrator on this same CR.

### S10a — Domain Sign-Off Request
Shows only the fields tagged to the requested domain (06-data-dictionary.md §2a), pre-filled with the originating Engineer's best-effort values where present, editable, with a "Sign Off This Domain" button.

### S10 additions *(v4)*
The decision panel asks for the actor's **password** (step-up); a banner names the person being covered when the actor decides as a delegate; **field comments** can be added per field in the diff and the author sees the open ones inline; the configured **review checklist** appears as checkboxes the approving Reviewer must tick; **evidence** (attachments) is listed and downloadable; the **SLA chip** shows days waited and amber/red; **Where-used**, **reference warnings** and **similar-title warnings** appear above the diff; the change set the request belongs to is linked.

### S12 — Release Builder
Candidate table shows Functional System Group **and Subgroup**; sandbox-flagged revisions are structurally absent from the candidate list. *(v4)* A *Target software versions* form (before publishing) limits the candidates to revisions whose version range includes a target; revisions with a future planned effective date are flagged; **Publish** asks for the Administrator's password and keeps the typed-confirmation pattern.

### S17 — Export Center
Two sections: **Catalogue Export** — format selector now offers **CSV, JSON, XLSX, PDF** (adds XLSX, 2026-09-17), all producing the same flat, table-shaped output (one row per status code, every field as a column — including JSON, emitted as a flat array of row objects, mirroring the legacy tool's grid and its "Export for: Customer / Service" pattern, which maps onto filtering by the relevant audience-access field). **Full-Database Export** — visible only to Administrator, with the same data-sensitivity warning as before.

## 5. Field Definitions, Validation, and Inline Help (corrected 2026-09-17)

Field set and validation rules mirror 06-data-dictionary.md exactly (superseding the earlier, less accurate field list). Two explicit UX requirements, both direct responses to feedback on the legacy tool:

- **"No explanations given on options"** (legacy tool complaint) — every dropdown/lookup-backed field in CSCM Tool shows the selected lookup value's `description` (06-data-dictionary.md §9, `LookupValue.description` in the API) as inline help text: a small `(?)` icon next to the field label opens a tooltip with the description, and the dropdown's own option list shows the description as secondary text under each option's label, not just the raw code. Lookups currently without a populated `description` (e.g. Available Group codes, whose meanings are still TBD per 06-data-dictionary.md §9c) show "Description not yet available — confirm with Controls Engineering" rather than leaving the tooltip empty or absent.
- **No data loss on validation failure** — see §4 S5.

The eight audience-access fields carry a "Proposed — confirmed by Product Owner at review" badge (§2.9 restricted-field pattern, 04-domain-model.md) until `admin_signoff_at` is non-null, after which they render as confirmed/locked on the read-only Current tab. The identifier field is never directly editable by any role in the UI.

## 6. Lifecycle State Visual Language

| State | Badge Color | Icon |
|---|---|---|
| Draft | Grey | pencil |
| Review | Amber | clock |
| PendingApproval | Deep amber / gold | hourglass |
| Approved | Blue | check |
| Released | Green | check-circle (filled) |
| Deprecated | Orange | alert-triangle |
| Archived | Dark grey / muted | archive box |
| (Sandbox, any state) | Red outline overlay on the badge above | flask/test-tube |

Uses the OneTool `--ot-error`/`--ot-success` tokens where applicable (§0); color is never the sole signal (icon + text label always accompany the badge), satisfying WCAG 1.4.1 (§8).

## 7. Responsive Behaviour

Per the OneTool design system (§0): sidebar collapses at tablet width with main content taking full width; mobile padding reduces to 16–20px with grids stacking and toolbars scrolling horizontally; desktop remains the primary target given CSCM Tool's dense tables and multi-section forms (`max-width: 1280px`).

## 8. Accessibility Requirements

*(v4, NFR-010)* These are now checked by automated tests on every page in both languages: contrast of text and badge colours ≥ 4.5 : 1, one `main` landmark, skip link, language attribute, heading order, labelled controls, table header scope, and a style sheet that honours `prefers-reduced-motion`; a manual screen-reader pass stays on the pre-go-live checklist (13-test-strategy.md §8a). Per the OneTool design system (§0): WCAG 2.1 AA target, full keyboard operability, associated labels, `aria-live` validation announcements, WCAG AA contrast pairs (dark blue on white, white on primary blue), 44×44px minimum pointer targets, semantic headings and native controls, text alternatives for icons, proper table semantics (`<th scope="col">`, `aria-sort`).

## 9. User Interaction Patterns

- **No data loss on failure** (§4 S5) — the single highest-priority UX fix from legacy-tool feedback; applies to every form in the application, not just S5.
- **Inline explanations on all lookup-backed options** (§5) — the second highest-priority fix.
- **Sandbox deletion** requires a typed-confirmation pattern identical in rigor to Release publish.
- **Domain sign-off requests** produce a notification-style entry on the target Engineer's Dashboard (S2) and My Change Requests (S8).
- **Import progress** (S19) never blocks the UI synchronously for large files — always asynchronous with pollable status, so an Engineer can navigate away and come back.
- Destructive/irreversible actions always require explicit confirmation; optimistic UI is avoided for state-changing actions; empty states include a next action; toasts confirm non-navigating actions while navigating actions land on the resulting screen with a success banner.

## 10. v4 Interaction Patterns

- **Password confirmation.** Every sensitive action (sign-off, approval, publish, full-database export, change-set decision) has a *Your password* field in the same form; a wrong or missing password re-shows the form with the user's entries intact and an inline error (NFR-007a).
- **Language.** The translations, their review by native speakers and the way the manuals reach every language are described in [26-translations.md](26-translations.md). A language menu in the top bar (country letters, name, drawn national flag; nineteen languages from GB English to GE ქართული, Georgian last, the list scrolls) stores the preference with the user; before login it follows the browser. Untranslated strings fall back to English, never to a blank. Flash messages from the service layer and the administration screens stay English (further improvement in 21-improvement-ideas.md).
- **Notices.** The bell in the top bar shows the number of unread notices; the Notices page marks one or all as read.
- **Tooltips and help.** State badges and role names carry their glossary text as a tooltip; each change-request state shows a "What happens next" line; `/help` gives the per-role quick start (FR-154).
- **Shareable views.** The status code list keeps filters, sort, page and chosen columns in the URL, so a link reproduces the view; *Save search* stores it under a name.
- **Background work.** Imports above the row threshold show progress and can be left; the job page reports `COMPLETE` or `FAILED`, never an endless spinner.
- **Tables.** Every table uses `<th scope="col">`; sortable headers are links; empty states name the next action.

## 10a. Translation scope (v4.4)

A critical review of what the interface translates and what it must not. The rule: **translate what a person reads to operate the tool; never translate what is data, evidence, identity or contract.**

| Item | Translated? | Reason |
|---|---|---|
| Interface text: navigation, buttons, labels, hints, table headings, help | **Yes**, through the catalogues (German complete; French, Hindi, Georgian, Arabic the main strings; the ten Indian-subcontinent languages after Arabic about sixty strings; the rest falls back to English) | A person needs to operate the tool in their language. |
| Role names | **Yes**, as display words; the role code stays in data, API and audit | Same code, readable name. |
| Identifiers (`StCd-01000`), numbers, versions, dates, file names | **No**; Latin letters and digits in every language, shown left-to-right inside right-to-left text | An identifier must be identical wherever it is quoted, searched or typed on a controller. |
| Stored and exchanged values: lifecycle states (`DRAFT`), categories (`ERROR`, `WARNING`, `INFO`), engineering-domain and platform codes, CSV and JSON field names, API error codes | **No** | They are the contract of the API, the exports and the database. A translated label may be shown beside the code later; it never replaces it. |
| Title, description and remedy text of a status code | **Not by the interface catalogue.** Only through the translation workflow (FR-110): one translation per language, approved by a second person | This text carries the safety-relevant meaning; a machine or unreviewed translation must never stand in for the source. |
| Audit log entries, action codes, the hash chain and audit exports | **No** | Compliance evidence must read the same for every reviewer (BR-020). |
| Technical vocabulary: codes and abbreviations (`MC`, `HC`, `StCd`, `PrgIdx_GUi`, `2XM` / `3XM` / `4XM`), IEC terms, product names | **No**; explained in help where needed | They are terms of the controller software and its documentation. The descriptive names *Main Controller* and *Hub Controller* are translated, one fixed word per language ([26-translations.md](26-translations.md) §4.3), the abbreviations are not. |
| Messages from the service layer and the API (`message` fields), log lines | **Not yet**; English | Clients and operators search and parse them. Messages shown to people in the UI could be translated later; API messages never. |
| PDF, XLSX, DOCX and CSV exports | Content language is chosen at export (FR-111); column headers and codes stay English | Audience files must stay machine-readable. |
| Names of people, free text typed by users, comments | **Never** | They are the user's words. |
| The documentation set and the manual | English source; the manual may be translated later | One authoritative text. |

Findings of the review: (1) the lifecycle and category badges show the English code by design, a translated word beside the code is an open improvement; (2) flash messages from the administration screens and the service layer are still English; (3) French, Hindi, Georgian and Arabic cover about a hundred strings each, the ten languages after them about sixty each, Spanish, Italian and Danish about a hundred, and none has been checked by native speakers, so they should not be switched on for people who rely on them before that happens; (4) a flag stands for a country, not a language: Saudi Arabia for Arabic (confirmed by the business), Pakistan for Urdu and India for the other Indian languages are conventions, and Bengali and Punjabi are also spoken in Bangladesh and Pakistan; (5) in right-to-left pages (Arabic, Urdu) the layout is mirrored by `app.css` (`html[dir="rtl"]`), mixed text such as `.st` in a heading can show its punctuation on the wrong side; (6) Urdu is normally set in the Nastaliq style, which many computers do not offer; the page then shows the Arabic-script font of the system, usually Naskh.

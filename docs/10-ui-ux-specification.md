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
| S8 | My Change Requests | Engineer | Track own submissions, incl. pending domain sign-off requests |
| S9 | Review Queue | Reviewer, Administrator | List CRs awaiting their sign-off |
| S9a | Approval Queue | Chief Engineer | List CRs in PendingApproval awaiting final decision |
| S10 | Change Request Detail / Decision | Reviewer, Administrator, Chief Engineer | Sign off / approve / reject with diff + comments + domain sign-off status |
| S10a | Domain Sign-Off Request | Engineer (second domain) | Complete domain-owned fields, record sign-off |
| S11 | Release List | All | Browse releases |
| S12 | Release Builder | Administrator | Build candidate set, publish |
| S13 | Release Detail | All | View published contents, export |
| S14 | User Management | Administrator | CRUD users, roles, Engineering Domain tags |
| S15 | Lookup/Vocabulary Management | Administrator | Manage Functional Groups/Subgroups (incl. create new — §4 S15), Turbine Platforms, Engineering Domains, Available Group, the 8 access vocabularies |
| S16 | Audit Log Search | Administrator, Reviewer/Chief Engineer (scoped) | Investigate history |
| S17 | Export Center | All (scoped by role); Full-Database Export | Ad-hoc catalogue exports (CSV/JSON/XLSX/PDF); full DB export (Administrator only) |
| S18 | Account Settings | All | Change own password (CSCM Tool's own) |
| S19 | Library Import | Engineer, Administrator | Upload CSV/XLSX, review progress and errors |

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
        │
        ├─▶ My Change Requests (S8) [Engineer] ──▶ Domain Sign-Off Request (S10a) [if flagged]
        │
        ├─▶ Review Queue (S9) [Reviewer/Admin] ──▶ Change Request Detail/Decision (S10)
        ├─▶ Approval Queue (S9a) [Chief Engineer] ──▶ Change Request Detail/Decision (S10)
        │
        ├─▶ Releases (S11) ──▶ Release Detail (S13) ──▶ Export Center (S17)
        │         └─▶ New Release / Release Builder (S12) [Admin]
        │
        ├─▶ Administration [Admin only, top-level menu]
        │         ├─▶ User Management (S14)
        │         ├─▶ Lookup Management (S15) ──▶ New Subgroup form (non-overlap validated)
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

## 4. Wireframe Descriptions

### S5 — New Status Code
A single-page form on the standard `ot-card` surfaces, laid out in labeled sections per the design system's two-column grid guidance:

1. **Classification** — Functional System Group (dropdown, required) → Functional Subgroup (dependent dropdown, populated from the selected group, **required — never optional**, disabled with a "select a Functional System Group first" hint until a group is chosen) → Turbine Platform (multi-select chip input, at least one required). The identifier field shows **"Not yet assigned — fixed on Submit for Review"**, never a real or placeholder number; a small, explicitly-labeled non-binding grey preview may appear ("likely next: `StCd-01233` — not reserved").
2. **Description** — Title, Description.
3. **Status & Timing** — Status Category (Error/Warning/Info), Available Group (numeric picker, sourced from the soft-validated lookup), Alarm (checkbox), Set Delay / Reset Delay (each a value + unit-select pair — ms/s/min/h/d — composed into the stored free-text form, so Engineers never have to type the unit suffix by hand), Up/Down Counter, Trigger Snapshot, Loadless Spinning Permitted (checkboxes).
4. **Repeated-Error Escalation** (collapsible, optional) — Number of Times Repeated, Repeated Over the Course (value + unit), Status Code for Repeated Error (plain numeric field, labeled "reference number in the separate escalation code pool — not a CSCM Tool status code").
5. **Program References** (collapsible, labeled "Advanced — controller firmware programs", CONTROLS-domain-owned) — Yaw Program, Manual Reset Program, Auto Reset Program, Converter Reactive Power Program, Brake Program, Umrichterprogramm GSC, Umrichterprogramm MSC, Yaw Bearing Lubrication Program — each a plain numeric field with the currently-observed valid values shown as a soft-suggestion list (autocomplete), not a hard-enforced dropdown, since the firmware-side table can grow independently of CSCM Tool (06-data-dictionary.md §2c).
6. **Audience Access** (Governance-restricted — badge "Proposed, confirmed by Product Owner at review" on every field, per §5 below) — eight independent dropdowns: Development, Sales, TCC, Service, Turbine Operator Package, Grid Operator, Service Partner, Customer.
7. **Ownership** — Owner (defaults to current user).

If the current Engineer's tagged Engineering Domain(s) do not cover a required domain (e.g. Program References is CONTROLS-owned and the originating Engineer is Electrical), that section is marked **"Needs Controls input"** with a "Request Domain Sign-Off" button; Submit for Review stays disabled until every required `DomainSignoff` exists.

**No data loss on failure (explicit fix, 2026-09-17):** a failed Submit-for-Review or Save never clears the form. The legacy tool resets all fields on any creation failure — flagged directly by the business as "cumbersome." CSCM Tool's client keeps every entered value in place after a 422 response and highlights only the specific invalid fields inline (per §9's inline-validation pattern); nothing is ever discarded because of a validation error, a network retry, or a session-timeout-triggered re-login.

Sticky footer: "Save as Draft" (secondary) and "Submit for Review" (primary, disabled until validation and all domain sign-offs pass).

### S5a — New Sandbox Status Code (Administrator only)
Same form as S5, minus the Functional Group/Subgroup/numbering section — a persistent banner reads **"Sandbox status code — never numbered from a real range, never released, deletable."** The resulting record's identifier is shown as `StCd-T#####`, with a red "SANDBOX" badge visible everywhere the code appears, and a "Delete Permanently" button on S4 for this record only, gated behind a typed-confirmation modal.

### S19 — Library Import
1. **Upload** — drag-and-drop or file picker for a `.csv` or `.xlsx` file, with a short format note ("one row per status code; column headers must match the exported template — download a template from here").
2. **Progress** — once uploaded, the job processes asynchronously; the screen polls `GET /imports/{id}` and shows a progress bar with `created_count`/`error_count`/`row_count`.
3. **Result** — on completion, a summary ("128 of 134 rows imported as Drafts, 6 failed validation") with a "Download error report" link (per-row reasons) and a "View imported Drafts" link to My Change Requests (S8), filtered to this import job. Imported rows are ordinary Drafts — the screen never implies they are already Approved.

### S15 — Lookup/Vocabulary Management, incl. New Subgroup and New Functional System Group
In addition to the original vocabularies, an Administrator can select a Functional System Group and click "Add Subgroup," entering a name and a proposed numeric sub-range. The form shows the group's existing subgroups and their ranges visually (a simple horizontal bar from `range_start` to `range_end` with existing subgroups shaded and reserved blocks highlighted) and pre-fills a suggested next hundred-aligned free block. Submitting a range that overlaps an existing subgroup returns the specific conflict inline ("overlaps 'Hot Air De-icing' (4200–4299)") without losing the entered name — the same no-data-loss principle as S5.

A second, top-level "Add Functional System Group" action (new 2026-09-17, FR-048g/h) works the same way one level up: an overview strip shows the full 1000–16999 span with occupied groups (including both the Main and Hub Controller ranges) shaded and the confirmed free bands (`10000–10999`, `14000–14999`, `15000–15999`, `16000–16999`) highlighted as available. The Administrator enters a code, label, and range within a free band; an overlapping range is rejected inline the same way, naming the conflicting group, without losing the entered name.

### S4 — Status Code Detail
Header band: Status Code Identifier (or "Not yet assigned" for Draft) + Title + Lifecycle State badge (§6) + Functional System Group **and Functional Subgroup** tags (both always present) + Turbine Platform chips. A red "SANDBOX" badge replaces the identifier styling for sandbox records. Tabs: **Current**, **History**, **Change Requests**. Action buttons (role- and state-gated): "Open New Revision" (Engineer, if no open CR), "Deprecate" (Administrator, if Released), "Delete Permanently" (Administrator, sandbox only).

### S9a — Approval Queue (Chief Engineer)
Table: Identifier, Title, Functional Group/Subgroup, Reviewer (who signed off), Administrator (who signed off), Age since both sign-offs completed. Row click → S10.

### S10 — Change Request Detail / Decision
Split layout: left panel field-level diff (now covering every field category in §4 S5); right panel CR metadata, a **Sign-Off Status strip** (Reviewer / Administrator / Chief Engineer, each pending or signed-with-name-and-date), and a **Domain Sign-Off strip**. Action buttons render per the viewer's role and the CR's current state, hidden entirely (not merely disabled) for the CR's own author and, at the Chief Engineer stage, for whichever individuals already signed off as Reviewer or Administrator on this same CR.

### S10a — Domain Sign-Off Request
Shows only the fields tagged to the requested domain (06-data-dictionary.md §2a), pre-filled with the originating Engineer's best-effort values where present, editable, with a "Sign Off This Domain" button.

### S12 — Release Builder
Unchanged in structure from the prior revision; candidate table now shows Functional System Group **and Subgroup**; sandbox-flagged revisions structurally absent from the candidate list.

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

Per the OneTool design system (§0): WCAG 2.1 AA target, full keyboard operability, associated labels, `aria-live` validation announcements, WCAG AA contrast pairs (dark blue on white, white on primary blue), 44×44px minimum pointer targets, semantic headings and native controls, text alternatives for icons, proper table semantics (`<th scope="col">`, `aria-sort`).

## 9. User Interaction Patterns

- **No data loss on failure** (§4 S5) — the single highest-priority UX fix from legacy-tool feedback; applies to every form in the application, not just S5.
- **Inline explanations on all lookup-backed options** (§5) — the second highest-priority fix.
- **Sandbox deletion** requires a typed-confirmation pattern identical in rigor to Release publish.
- **Domain sign-off requests** produce a notification-style entry on the target Engineer's Dashboard (S2) and My Change Requests (S8).
- **Import progress** (S19) never blocks the UI synchronously for large files — always asynchronous with pollable status, so an Engineer can navigate away and come back.
- Destructive/irreversible actions always require explicit confirmation; optimistic UI is avoided for state-changing actions; empty states include a next action; toasts confirm non-navigating actions while navigating actions land on the resulting screen with a success banner — all unchanged from the prior revision.

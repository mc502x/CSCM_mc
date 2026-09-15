# 10. UI/UX Specification — CSCM Tool

## 1. Screen Inventory

| # | Screen | Primary Role(s) | Purpose |
|---|---|---|---|
| S1 | Login | All | Authenticate |
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
| S15 | Lookup/Vocabulary Management | Administrator | Manage Functional Groups/Subgroups, Turbine Platforms, Engineering Domains, and the original 7 vocabularies |
| S16 | Audit Log Search | Administrator, Reviewer/Chief Engineer (scoped) | Investigate history |
| S17 | Export Center | All (scoped by role); Full-Database Export | Ad-hoc catalogue exports; full DB export (Administrator only) |
| S18 | Account Settings | All | Change own password |

## 2. Navigation Map

```
Login (S1)
  └─▶ Dashboard (S2) [role-specific widgets: e.g. Chief Engineer sees Approval Queue count]
        ├─▶ Status Codes (S3) ──▶ Status Code Detail (S4) ──▶ Revision History/Diff (S7)
        │                                │
        │                                └─▶ Edit Revision (S6) [Engineer, own open CR]
        │
        ├─▶ New Status Code (S5) [Engineer/Admin] ──▶ Status Code Detail (S4)
        ├─▶ New Sandbox Status Code (S5a) [Admin only] ──▶ Status Code Detail (S4, sandbox-flagged)
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
        │         ├─▶ Lookup Management (S15)
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
Multi-section single-page form:
1. **Classification** — Functional System Group (dropdown, required; drives numbering, see 05-governance-handbook.md §2) → Functional Subgroup (dependent dropdown, populated from the selected group, optional) → Turbine Platform (multi-select, at least one required). The identifier field shows **"Not yet assigned — fixed on Submit for Review"**, never a real or placeholder number, so users never mistake a Draft for having a citable code (a `GET /status-codes/next-available` preview may be shown as small, explicitly-labeled non-binding grey text: "likely next: StCd-01233 (not reserved)").
2. **Description** — Title, Description.
3. **Classification (continued)** — Status Category, Availability Group, Brake Program, Reset Program, Operational State, Alarm Behaviour (dropdowns from lookups).
4. **Access Rights** — shown with a badge "Proposed — confirmed by Product Owner at review," editable by the Engineer but visually distinct from confirmed fields (06-data-dictionary.md §2, "restricted field").
5. **Technical Parameters** — Software Version, Delay Before Alarm, Delay Before Reset.
6. **Ownership** — Owner (defaults to current user).

If the current Engineer's tagged Engineering Domain(s) do not cover every domain-owned field (06-data-dictionary.md §2a), the affected section is marked **"Needs Controls input"** (or the relevant domain) with a "Request Domain Sign-Off" button that notifies eligible Engineers holding that domain; Submit for Review stays disabled until every required `DomainSignoff` exists.

Sticky footer: "Save as Draft" (secondary) and "Submit for Review" (primary, disabled until validation and all domain sign-offs pass).

### S5a — New Sandbox Status Code (Administrator only)
Same form as S5, minus the Functional Group/Subgroup/numbering section entirely — a persistent banner reads **"Sandbox status code — never numbered from a real range, never released, deletable."** The resulting record's identifier is shown as `StCd-T#####` once created, with a red "SANDBOX" badge visible everywhere the code appears (list, detail, search results), and a "Delete Permanently" button appears on S4 for this record only, gated behind a typed-confirmation modal.

### S4 — Status Code Detail
Header band: Status Code Identifier (or "Not yet assigned" for Draft) + Title + Lifecycle State badge (§6) + Functional System Group tag + Turbine Platform chips. A red "SANDBOX" badge replaces the identifier styling for sandbox records. Tabs: **Current**, **History**, **Change Requests**. Action buttons (role- and state-gated): "Open New Revision" (Engineer, if no open CR), "Deprecate" (Administrator, if Released), "Delete Permanently" (Administrator, sandbox only).

### S9a — Approval Queue (Chief Engineer)
Table: Identifier, Title, Functional Group, Reviewer (who signed off), Administrator (who signed off), Age since both sign-offs completed. Row click → S10.

### S10 — Change Request Detail / Decision
Split layout: left panel field-level diff; right panel CR metadata, a **Sign-Off Status strip** showing three slots — Reviewer, Administrator, Chief Engineer — each showing pending/signed-with-name-and-date, plus a **Domain Sign-Off strip** listing each required Engineering Domain and its status. Action buttons render according to the viewer's role and the CR's current state: Reviewer sees "Sign Off" only while in Review and their slot is empty; Administrator sees the same; Chief Engineer sees "Approve"/"Reject" only while in PendingApproval. Reject always opens a modal requiring a mandatory comment. Buttons are hidden entirely (not merely disabled) for the CR's own author and, at the Chief Engineer stage, for whichever individuals already signed off as Reviewer or Administrator on this same CR (segregation of duties, reinforced at the UI layer in addition to the server-side 403).

### S10a — Domain Sign-Off Request
Shown to an Engineer who receives a sign-off request for a domain they hold. Displays only the fields tagged to that domain (06-data-dictionary.md §2a), pre-filled with the originating Engineer's best-effort values where present, editable, with a "Sign Off This Domain" button that records the `DomainSignoff` and returns control to the originating Engineer's Draft.

### S12 — Release Builder
Unchanged in structure from v1, with the candidate table now showing Functional System Group instead of Controller Type as a filterable column, and sandbox-flagged revisions structurally absent from the candidate list (the API never returns them, per `trg_prevent_sandbox_release`).

### S17 — Export Center
Two clearly separated sections: **Catalogue Export** (CSV/JSON/PDF of Approved/Released data, available per the role matrix in §3) and, visible only to Administrator, **Full-Database Export** (raw SQLite backup, with an explicit warning that this contains the complete governed dataset and must be handled per 11-security-architecture.md §7 data-at-rest controls).

## 5. Field Definitions & Validation Rules (UI Layer)

Mirror 06-data-dictionary.md exactly. Key additions for v2:
- Functional System Group selection drives which Functional Subgroups are offered (dependent dropdown; changing the group clears any selected subgroup).
- Turbine Platform is a multi-select chip input, minimum one selection enforced before Submit for Review.
- Access Rights carries the "Proposed" badge (§4 S5) until `admin_signoff_at` is non-null, after which it renders as confirmed/locked on the read-only Current tab.
- The identifier field is never directly editable by any role in the UI (system-allocated only); an Administrator's manual-override capability (05-governance-handbook.md §2, exceptional migration case) is a separate, clearly-labeled Administration-only action, not part of the normal creation form.

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

Color is never the sole signal (icon + text label always accompany the badge), satisfying WCAG 1.4.1 (§8).

## 7. Responsive Behaviour

Unchanged from v1 (§7): desktop-primary (≥1280px), supported down to 1024px, not optimized below that for MVP.

## 8. Accessibility Requirements

Unchanged from v1 (§8): WCAG 2.1 AA target, full keyboard operability, associated labels, `aria-live` validation announcements, 4.5:1/3:1 contrast, non-decorative icons carry text/`aria-label`, proper table semantics.

## 9. User Interaction Patterns

Unchanged principles from v1 (§9: confirm irreversible actions, no optimistic UI on state changes, inline validation, empty states, toasts vs. navigating banners), extended with:
- **Sandbox deletion** requires a typed-confirmation pattern (type the identifier to confirm) identical in rigor to Release publish, since it is the one truly irreversible action in the entire system.
- **Domain sign-off requests** produce a notification-style entry on the target Engineer's Dashboard (S2) and My Change Requests (S8), not just an email/toast, since blocking Submit-for-Review on it makes it a hard dependency, not a courtesy ping.

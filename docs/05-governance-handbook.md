# 05. Status Code Governance Handbook — CSCM Tool

## 1. Purpose

This handbook is the authoritative governance policy the application must enforce in software. Where this document and any other document disagree on a process rule, this document wins.

## 2. Code Numbering Strategy

The Status Code Identifier is `StCd-XXXXX`: a five-digit, zero-padded number, e.g. `StCd-01232`. Its numeric value is not arbitrary — it equals the code's position within its Functional System Group's fixed numeric range, so the identifier itself encodes classification. There is no separate prefix letter scheme in the identifier (the former `MC-`/`HC-` split and its Controller Type basis are retired entirely); the four-letter group codes (`WCNV`, `WGEN`, ...) are displayed alongside the identifier for cross-reference but are not part of it.

| Range | Functional System Group | Prefix (display only) |
|---|---|---|
| 1000–1999 | Converter / Grid Interface | WCNV |
| 2000–2999 | Generator | WGEN |
| 3000–3999 | Meteorology / Environment / Nacelle Monitoring | WNAC |
| 4000–4999 | Pitch System / Hub | WROT |
| 5000–5999 | Tower / Oscillation Monitoring | WTOW |
| 6000–6999 | Transformer / MV Switchgear | WTRF |
| 7000–7999 | Drive Train / Gearbox / Hydraulic System / Rotor Brake | WTRM |
| 8000–8999 | Yaw System | WYAW |
| 9000–9999 | Turbine Control / Safety / Operational States / SCADA | WTUR |

**Subgroups (placeholder, TBD):** each Functional System Group is further divided into Functional Subgroups, each owning a numeric sub-band within the group's range. The real subgroup taxonomy has not yet been provided; this package seeds three generically-named placeholder subgroups per group (`Subgroup 1/2/3 (TBD)`), splitting each 1000-number range into three roughly equal sub-bands, purely so the data model, dropdowns, and allocation logic are structurally complete and testable. **This placeholder must be replaced with the real subgroup list from Controls Engineering before go-live** — replacing it is a data change (lookup table rows), not a schema change (06-data-dictionary.md §9a).

**Allocation rule:** the identifier is **not** assigned at Draft creation. An Engineer creating a new Status Code selects a Functional System Group (required) and, optionally, a Functional Subgroup via dropdown; the Draft is worked on with no fixed number (displayed as "TBD — assigned on submission"). Only at the moment the Change Request is submitted for Review (Draft → Review) does the system atomically allocate the next free number: within the selected Subgroup's sub-band if one was chosen, otherwise the next free number anywhere in the Functional System Group's range not already claimed by a subgroup-scoped allocation. This satisfies the requirement that in-progress codes never carry a fixed number.

Numbers are never reused, even if a code is later Archived. Gaps are expected wherever a Draft is abandoned before submission (its number was never allocated in the first place — it never had one). An Administrator may allocate an out-of-sequence number only for a documented migration/reservation case, recorded and audited as a manual override.

**Sandbox exception:** Administrator-created test/sandbox Status Codes never draw from the ranges above. They receive an identifier from an isolated `StCd-T#####` counter, are flagged `is_sandbox = true`, are excluded from every Release, catalogue export, and manual, and are the only records in the system an Administrator may permanently delete (§12).

Identifier + Functional System Group assignment is immutable once allocated (BR-001). If a code was genuinely created in error before any Review activity, it is deprecated, not renumbered or reassigned to a different group.

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

1. Engineer (or Administrator) initiates "New Status Code," selects Functional System Group and, optionally, Functional Subgroup via dropdown (§2). No identifier is shown yet.
2. System creates a `StatusCode` (identifier `NULL`, `functional_system_group_id`/`functional_subgroup_id` set) + first `StatusCodeRevision` + a `ChangeRequest` (`cr_type = NEW`), all in **Draft**.
3. Engineer completes mandatory attributes; system validates continuously.
4. If the originating Engineer's tagged Engineering Domain(s) do not cover every domain-owned field on the revision, the Draft is flagged "awaiting domain input" and cannot be submitted until each missing domain is signed off (§6a).
5. Engineer submits for Review; the system allocates the StCd identifier atomically and transitions Draft → Review.
6. Reviewer and Administrator each independently evaluate and sign off (§7); on the second sign-off, the system auto-transitions Review → PendingApproval.
7. Chief Engineer evaluates and approves or rejects (§8); on approval, PendingApproval → Approved.
8. On inclusion in a published Release, Approved → Released, Effective Date stamped.

## 6a. Cross-Domain Sign-Off

Some Functional System Groups require input from more than one Engineering Domain (e.g. a Generator-group code created by an Electrical engineer may still need Controls-domain parameters — delay/alarm/reset behavior — that the originating engineer cannot authoritatively provide). Each field in 06-data-dictionary.md is tagged with an owning Engineering Domain. When a Draft's originating Engineer lacks a domain tag required by one or more of its fields, the system marks those domains as "pending" and blocks Submit-for-Review until a `DomainSignoff` exists for each pending domain, recorded by an Engineer who holds that domain. This is a completeness gate, not a content judgment — it does not replace Review.

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

## 8. Chief Engineer Approval

Once both Review sign-offs are recorded (PendingApproval), a Chief Engineer performs the final Approval decision — approve or reject with a mandatory comment on rejection. The Chief Engineer may not be the Change Request's author, the Reviewer who signed off, or the Administrator who signed off on the same Change Request (segregation of duties extends across all three decision points). Approval is the final governance gate before a revision is eligible for Release; it is a distinct accountability step from Review and is always performed by a named individual, never inferred from role membership alone.

## 9. Revision Numbering & Concurrency

Unchanged from the original model in substance: each new Draft opened against an existing `StatusCode` increments `revision_number`; a rejection (Review or PendingApproval → Draft) reuses the same revision row; only one open (Draft/Review/PendingApproval) revision is permitted per `StatusCode` at a time (BR-003).

## 10. Release Rules

Unchanged in mechanics from v1 (only an Administrator may create/publish/pre-publish-delete a Release; candidate pool is Approved-state revisions matching the scope filter, now expressed in terms of Functional System Group/Subgroup rather than Controller Type; publish is atomic; a published Release is permanently immutable).

## 11. Deprecation, Retention & Archival Rules

Unchanged in mechanics from v1: deprecation requires a reason and optional superseding reference; minimum 180 days in Deprecated before Archival; 7-year minimum retention for Archived records and all associated Change Requests/comments/sign-offs/audit entries, never hard-deleted — **except** sandbox Status Codes (§12).

## 12. Sandbox / Test Status Codes

An Administrator may create a Status Code flagged `is_sandbox = true` for testing purposes (e.g. verifying a new export template, training a new Reviewer). Sandbox codes:
- Draw their identifier from an isolated `StCd-T#####` band, never from a real Functional System Group range, so they can never collide with or consume a production number.
- Are excluded from every Release candidate list, catalogue export, and manual by construction (a hard filter, not a convention).
- May proceed through the same lifecycle states for realistic testing, but can never actually be included in a real Release (the system blocks adding a sandbox-flagged revision to any Release, regardless of state).
- Are the **only** records in the system an Administrator may permanently delete. Deletion is logged as an immutable `SANDBOX_DELETE` audit entry that captures the full record snapshot in `before_value` — the audit trail entry survives even though the record itself does not (12-audit-compliance.md §2).
- This is a narrow, explicit, audited exception to the otherwise absolute no-hard-delete rule (§11) and must never be generalized to non-sandbox records.

## 13. Compliance Rules

Unchanged in principle from v1, updated for the new sequence: every Released Status Code must be traceable, without gaps, through Draft → Review (both sign-offs, with identity and timestamp) → PendingApproval → Approved (Chief Engineer, with identity and timestamp) → Released (Release identity, Effective Date). Segregation of duties is enforced server-side at all three decision points (Reviewer, Administrator, Chief Engineer), never only in the UI.

# 02. Product Requirements Document (PRD) — CSCM Tool

## 1. Product Vision

CSCM Tool is the master system of record for wind turbine Main Controller and Hub Controller status codes. It replaces document-first authoring with a governed, auditable, database-first workflow: engineers propose codes (completing cross-domain fields where their own specialty cannot cover them), a Reviewer and an Administrator each independently sign off, a Chief Engineer gives final approval, and every other document or system that needs status code data consumes it from CSCM Tool, never the reverse. The system runs entirely on local, on-premises infrastructure.

## 2. Goals

1. Provide one authoritative, versioned record per status code, classified and numbered by Functional System Group (and, optionally, Functional Subgroup) rather than an arbitrary series.
2. Enforce a mandatory, three-decision-point review/approval workflow before any code becomes Released.
3. Preserve complete, immutable revision history for every status code.
4. Provide release management so a specific, named, dated snapshot of approved codes can be exported and referenced by manuals, SCADA configuration, and future integrations.
5. Provide a REST API, reachable only from the internal network, suitable for future on-premises integration with documentation generation tools, software repositories, and SCADA systems.
6. Provide role-appropriate access so contribution (Engineer), cross-domain completion, gatekeeping (Reviewer, Administrator, Chief Engineer), and consumption (Viewer) are cleanly separated.
7. Provide a safe, isolated sandbox mechanism for testing and training that can never contaminate production numbering, catalogues, or manuals.

## 3. Personas

### 3.1 Engineer (primary contributor)
A controls engineer or cross-functional engineer (electrical, mechanical, grid, safety), tagged with one or more Engineering Domains. Creates new status codes and change requests. Needs a fast, structured entry form with strong validation, clear visibility into which domain-owned fields still need a second engineer's input, and visibility into where their submissions sit across the three decision points.

### 3.2 Reviewer (Sub-PO for Status Codes)
Responsible for one of the two required Review sign-offs: verifying a proposed status code or change is technically correct, non-duplicate, and consistent with existing conventions. Needs a focused sign-off queue, side-by-side diff of proposed vs. current revision, and mandatory-comment rejection.

### 3.3 Administrator (Product Owner Controls Software / Component Owner Controls Software)
Owns system configuration, user/role/Engineering-Domain administration, controlled vocabularies (including the Functional System Group/Subgroup and Turbine Platform lookups), release process, sandbox status codes, and full-database export. Also provides the second of the two required Review sign-offs, during which any Engineer-proposed restricted field (e.g. Access Rights) is confirmed or overridden.

### 3.4 Chief Engineer (final approval authority)
Performs the final Approval decision once both Review sign-offs are complete. Cannot approve a submission they authored or already signed off on as Reviewer or Administrator. Needs an Approval Queue and the same diff/comment tooling as the Reviewer/Administrator sign-off screens.

### 3.5 Viewer (consumer)
Technical writer, service technician, or other stakeholder who looks up current or historical status code definitions but never edits data. Needs fast search/filter and read-only export of Approved/Released catalogues.

## 4. Stakeholders

| Stakeholder | Interest |
|---|---|
| Controls Engineering | Accurate, unambiguous status code definitions tied to firmware behaviour, and the final real Functional Subgroup taxonomy |
| Technical Publications | Reliable source data for manuals and specifications, on a predictable release cadence |
| Quality / Compliance | Auditability, traceability, and change control evidence across all three decision points |
| Service & Field Operations | Correct, current status code meaning for troubleshooting |
| SCADA/Software Integration teams (future) | Machine-readable, versioned status code data via an internal-network-only API |
| IT/Platform Operations | Operable, securable, maintainable, fully on-premises system |

## 5. User Journeys

### 5.1 Engineer creates a new status code
1. Engineer logs in, navigates to "New Status Code," selects Functional System Group (e.g. Converter/Grid Interface) and, optionally, Functional Subgroup, plus at least one Turbine Platform. No identifier is shown yet.
2. Engineer completes all mandatory attributes; validation blocks submission until the record is complete and internally consistent.
3. If fields owned by a domain the Engineer does not hold are still unset, the system flags them and lets the Engineer request sign-off from a colleague holding that domain.
4. Once complete, Engineer submits for Review; the system allocates a fixed `StCd-XXXXX` identifier at that moment, not before.
5. Engineer tracks sign-off/approval progress and sees Reviewer/Administrator/Chief Engineer comments if rejected at any stage.

### 5.2 Reviewer and Administrator sign off
1. Reviewer opens their queue, opens a submitted code, reviews the field-level diff, checks for duplicate-meaning codes, and signs off or rejects with a comment.
2. Independently, the Administrator does the same, additionally confirming or overriding the Engineer-proposed Access Rights value.
3. Once both sign-offs are recorded (in either order), the system automatically advances the code to Pending Approval.

### 5.3 Chief Engineer approves
1. Chief Engineer opens the Approval Queue, reviews the same diff plus both sign-offs' comments, and approves or rejects with a comment.
2. On approval, the code becomes Approved and enters the Release candidate pool.

### 5.4 Administrator builds and publishes a Release
1. Administrator creates a Release scoped by Functional System Group/Subgroup, reviews the Approved (non-sandbox) candidate list, confirms the set, and publishes.
2. Publishing atomically transitions included revisions to Released, stamps Effective Date, and locks the Release's contents.
3. Administrator exports the Release catalogue (CSV/JSON/PDF) for Technical Publications.

### 5.5 Viewer looks up a status code
Unchanged from the original journey: search, view current Released definition and history, export a filtered read-only catalogue.

### 5.6 Administrator deprecates an obsolete code
Unchanged in outcome, now routed through the full three-decision-point cycle when initiated as an Engineer Change Request.

### 5.7 Administrator uses a sandbox status code
1. Administrator creates a sandbox status code for testing an export template or training a new Reviewer, drawing an isolated `StCd-T#####` identifier that can never enter a real Functional System Group range.
2. Administrator exercises it through the lifecycle as needed; it can never be added to a real Release.
3. Administrator permanently deletes it when done; the deletion itself remains in the audit trail forever, even though the record does not.

## 6. Functional Scope

**In scope (MVP):** status code CRUD via the governed three-decision-point Change Request workflow; Functional System Group/Subgroup classification and numbering (`StCd-XXXXX`, allocated at Draft→Review, not before); Turbine Platform multi-select; Cross-Domain Sign-Off; full attribute set per 06-data-dictionary.md; seven-state lifecycle with enforced valid transitions; revision history and field-level diffing; role-based access control across five roles; sandbox status codes (create/delete, Administrator-only); Release management (build, publish, lock, export); search/filter/sort; full audit trail; session-based authentication and internal user management; catalogue export (role-scoped) and full-database export (Administrator-only); REST API covering all core resources, internal-network-only.

**Out of scope (MVP):** on-premises Active Directory/ADFS SSO integration itself (the `AuthProvider` hook is built; the integration is not); live/automated push integration to documentation generation tools, code repositories, or SCADA systems; multi-language localization; multi-OEM/multi-tenant data partitioning; mobile native applications; configurable/multi-stage approval chains beyond the fixed Reviewer+Administrator+Chief-Engineer model; the final Functional Subgroup taxonomy (placeholder until Controls Engineering supplies it — a data-only gap, not a feature gap); any public-cloud component of any kind, at any phase.

## 7. Out-of-Scope Items (Explicit Exclusions)

| Item | Reason |
|---|---|
| Cloud-hosted SSO (e.g. Azure AD) | Explicitly excluded by the no-cloud-infrastructure requirement; the future SSO path is on-premises Active Directory/ADFS only (16-mvp-roadmap.md, 11-security-architecture.md §2) |
| Automated SCADA tag sync | Requires SCADA-side integration work outside CSCM Tool's control; API contract only in MVP, internal-network-only |
| Configurable/multi-stage approval chains | The fixed Reviewer→Administrator (parallel)→Chief Engineer model is sufficient for current governance need |
| Bulk import of legacy status codes | Explicitly against the "codes are created in CSCM Tool, not imported from documents" principle; any legacy reconciliation is a one-time, human-reviewed project activity, not a product feature |
| Real-time collaborative editing | Not required; optimistic concurrency control is sufficient |
| Public-cloud infrastructure of any kind | Hard deployment constraint (00-INDEX.md "Deployment Principle"); every environment is on-premises |

## 8. Acceptance Criteria (Product-Level)

1. A user cannot create two Status Codes with the same `status_code_identifier` (enforced at the database and API layer).
2. A Status Code Draft never displays a fixed identifier; one is allocated exactly once, atomically, at Draft→Review.
3. A Status Code cannot reach Released without passing through both required Review sign-offs (Reviewer and Administrator, neither the CR's author) and a separate Chief Engineer approval (also not the author or either sign-off).
4. Submission for Review is blocked while any Engineering-Domain-owned field required by the code's classification is not yet signed off by a qualified second Engineer, when the originating Engineer does not hold that domain.
5. Every mandatory attribute in 06-data-dictionary.md is enforced as required at both the UI and API layer before a revision can leave Draft.
6. Every state transition, field change, sign-off, approval, and role assignment produces an immutable audit log entry with actor, timestamp, before/after values.
7. A published Release is immutable, and a sandbox-flagged revision can never be included in one.
8. Role-based access control prevents Viewers from performing any write operation, prevents Engineers from self-signing-off or self-approving their own Change Requests at any of the three decision points, and restricts full-database export to the Administrator role alone.
9. Search returns results across all major attributes (identifier, title, category, Functional System Group, lifecycle status, owner) within NFR-001 performance targets.
10. An exported catalogue contains only Approved or Released, non-sandbox records, correctly scoped to the export filter and reproducible.
11. A sandbox status code can be permanently deleted only by an Administrator, and only while flagged sandbox; the deletion is itself permanently audited with a full before-state snapshot.

## 9. KPIs (Product Health, Ongoing)

| KPI | Target |
|---|---|
| Active Engineer/Reviewer/Administrator/Chief Engineer adoption (weekly active / licensed users in those roles) | ≥ 90% by end of Phase 1 |
| Change Requests rejected due to preventable data-entry errors | < 10% of all submissions after month 2 |
| Mean combined Reviewer+Administrator sign-off turnaround | ≤ 3 business days |
| Mean Chief Engineer approval turnaround | ≤ 2 business days |
| API error rate (5xx) | < 0.1% of requests |
| Audit log completeness (state-changing actions with a corresponding log entry) | 100% |
| Cloud-infrastructure findings in any architecture review | 0 (standing check, 11-security-architecture.md §12) |

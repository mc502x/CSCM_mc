# 17. Implementation Backlog — CSCM Tool

Conventions: `EPIC-##` → `FEAT-##.#` → `US-###`. Priority: P0 (must-have for MVP go-live), P1 (should-have), P2 (nice-to-have, may slip to Phase 2). Dependencies reference other story IDs or epics. Sizing: 16-mvp-roadmap.md §7.

---

## EPIC-01 — Foundation

### FEAT-01.1 Project Scaffold & CI
- **US-001** Flask application factory, blueprint skeleton, folder structure (15-development-standards.md §1). *AC:* app boots, health endpoint returns 200. *Dependencies:* none. *Priority:* P0.
- **US-002** CI configured (lint, format, type-check, test, security scan, no-cloud grep check). *AC:* CI runs on every push/PR; a deliberately failing test blocks merge; a deliberate cloud-SDK import blocks merge (TC-029). *Dependencies:* US-001. *Priority:* P0.

### FEAT-01.2 Database Schema & Migrations
- **US-003** Initial Alembic migration implementing `artifacts/schema.sql` v2 (all lookups, 7-state lifecycle, dual sign-off + Chief Engineer columns, sandbox support). *AC:* fresh DB matches schema.sql exactly; migration reversible. *Dependencies:* US-001. *Priority:* P0.
- **US-004** Seed all lookup tables, including the 9 Functional System Groups, the **placeholder** Functional Subgroups (flagged TBD), Turbine Platforms (2XM/3XM/4XM), and Engineering Domains. *AC:* seed migration inserts all documented rows. *Dependencies:* US-003. *Priority:* P0.

### FEAT-01.3 Authentication & Session Management
- **US-005**–**US-008** Login/session/lockout/logout/timeouts (FR-001–FR-004, SEC-001–SEC-004). Unchanged in substance from v1. *Dependencies:* US-003. *Priority:* P0/P1.

### FEAT-01.4 Role-Based Access Control (5 roles)
- **US-009** Administrator can create/edit/deactivate users, assign exactly one of the 5 roles, and tag Engineer-role users with one or more Engineering Domains (FR-010–FR-012 + new domain-tagging). *AC:* last active Administrator cannot be deactivated. *Dependencies:* US-005. *Priority:* P0.
- **US-010** Full 5-role × endpoint permission matrix enforced identically on UI and API (11-security-architecture.md §3). *AC:* TC-018 parameterized grid passes. *Dependencies:* US-009, incrementally with every endpoint. *Priority:* P0.
- **US-011**/**US-012** Self password change / Administrator-forced reset. Unchanged from v1. *Priority:* P1/P2.

---

## EPIC-02 — Status Code Data Model, Numbering & Validation

### FEAT-02.1 Functional Group / Subgroup Classification
- **US-020** Engineer selects Functional System Group (required) and Functional Subgroup (optional, dependent dropdown) when starting a new Status Code; no identifier is assigned at this point (05-governance-handbook.md §2, §6). *AC:* Draft shows "Not yet assigned." *Dependencies:* EPIC-01. *Priority:* P0.
- **US-021** Turbine Platform multi-select (minimum one required) on the same form. *AC:* Submit blocked with zero platforms selected. *Dependencies:* US-020. *Priority:* P0.

### FEAT-02.2 Identifier Allocation
- **US-022** Atomic identifier allocation at Draft→Review: `StCd-XXXXX` drawn from the selected group's (or subgroup's) numeric range (07-database-design.md §7a). *AC:* TC-007, TC-008 pass; two concurrent submissions never collide (integration test with simulated concurrency). *Dependencies:* US-020. *Priority:* P0.
- **US-023** `GET /status-codes/next-available` non-binding preview endpoint and UI display. *AC:* preview never reserves a number. *Dependencies:* US-022. *Priority:* P1.
- **US-024** Administrator manual-override allocation for a documented migration/reservation case, with reason logged. *Dependencies:* US-022. *Priority:* P2.
- **US-025** Capacity-exhaustion handling: allocation beyond a (sub)range's upper bound raises a domain error rather than overflowing. *Dependencies:* US-022. *Priority:* P2.

### FEAT-02.3 Field Validation
- **US-026** Mandatory field validation, client- and server-side (06-data-dictionary.md). *Dependencies:* US-020. *Priority:* P0.
- **US-027** Cross-field rules (Safety × Alarm Behaviour, Auto reset × delay, Emergency Brake × Fault/Safety). *AC:* TC-005, TC-006. *Dependencies:* US-026. *Priority:* P0.
- **US-028** Restricted-field handling: `access_rights_id` is Engineer-proposable but only authoritative once the Administrator's sign-off sets it (06-data-dictionary.md §2, SEC-013). *Dependencies:* US-026. *Priority:* P0.
- **US-029** Save-as-Draft any number of times without triggering submission validation. *Dependencies:* US-020. *Priority:* P0.

### FEAT-02.4 Revision Management
- **US-030** No in-place editing of Approved/Released/Archived revisions; new Draft revision required. *AC:* TC-013. *Dependencies:* US-026. *Priority:* P0.
- **US-031** Only one open (Draft/Review/PendingApproval) revision per code at a time. *AC:* TC-012. *Dependencies:* US-030. *Priority:* P0.
- **US-032** Engineer can withdraw own open CR. *Dependencies:* US-030. *Priority:* P1.

---

## EPIC-03 — Cross-Domain Sign-Off

- **US-040** System derives, from the field-to-domain ownership table (06-data-dictionary.md §2a), which Engineering Domains are "required" on a given revision, and flags any not covered by the originating Engineer's own domain tags. *Dependencies:* EPIC-02, US-009 (domain tags must exist). *Priority:* P0.
- **US-041** Originating Engineer can request sign-off from an Engineer holding a required domain; request surfaces on that Engineer's Dashboard and My Change Requests (S10a). *Dependencies:* US-040. *Priority:* P0.
- **US-042** Second Engineer completes domain-owned fields and records a `DomainSignoff`; system verifies they actually hold that domain (403 otherwise). *AC:* TC-020, TC-021. *Dependencies:* US-041. *Priority:* P0.
- **US-043** Submit-for-Review is blocked (422) while any required domain lacks a sign-off. *Dependencies:* US-042. *Priority:* P0.

---

## EPIC-04 — Dual Review & Chief Engineer Approval Workflow

### FEAT-04.1 Submission
- **US-050** Engineer submits Draft for Review; identifier allocated (EPIC-02 FEAT-02.2); requires all domain sign-offs complete (EPIC-03). *Dependencies:* EPIC-02, EPIC-03. *Priority:* P0.

### FEAT-04.2 Dual Sign-Off
- **US-051** Reviewer (Sub-PO for StCd) records sign-off (approve/reject); cannot act on own CR. *Dependencies:* US-050. *Priority:* P0.
- **US-052** Administrator (Product Owner) records sign-off (approve/reject); cannot act on own CR; approving also confirms/overrides restricted fields (US-028). *Dependencies:* US-050. *Priority:* P0.
- **US-053** System auto-transitions Review→PendingApproval atomically on the second sign-off, in either order. *AC:* integration test covers both orderings. *Dependencies:* US-051, US-052. *Priority:* P0.
- **US-054** Either sign-off rejecting (mandatory comment) returns the CR to Draft and clears both sign-off columns. *Dependencies:* US-051, US-052. *Priority:* P0.

### FEAT-04.3 Chief Engineer Approval
- **US-055** Chief Engineer views Approval Queue (S9a) listing PendingApproval CRs. *Dependencies:* US-053. *Priority:* P0.
- **US-056** Chief Engineer approves (PendingApproval→Approved) or rejects (→Draft, mandatory comment); cannot act if they are the requester, Reviewer sign-off, or Administrator sign-off on this CR. *AC:* TC-009b, TC-019. *Dependencies:* US-055. *Priority:* P0.

### FEAT-04.4 Review/Approval Queues & Tracking
- **US-057** Reviewer/Administrator see items awaiting their sign-off, filterable. *Dependencies:* US-050. *Priority:* P0.
- **US-058** Engineer's "My Change Requests" shows sign-off/approval progress (three-slot status strip). *Dependencies:* US-050. *Priority:* P1.
- **US-059** Reviewer/Administrator/Chief Engineer can add plain comments without a decision. *Dependencies:* US-050. *Priority:* P1.

---

## EPIC-05 — Search, Browse, History

Unchanged in substance from v1 EPIC-04, updated filters: Functional System Group, Functional Subgroup, Turbine Platform, `is_sandbox` (default excluded) replace Controller Type (FR-060–FR-064). *Dependencies:* EPIC-02. *Priority:* P0/P1.

---

## EPIC-06 — Release Management

Unchanged in substance from v1 EPIC-05, with candidate resolution explicitly excluding `is_sandbox=true` revisions (enforced by `trg_prevent_sandbox_release`, TC-014a) and `scope_filter` expressed via Functional System Group/Subgroup. *Dependencies:* EPIC-04. *Priority:* P0.

---

## EPIC-07 — Sandbox Status Codes

- **US-070** Administrator creates a sandbox Status Code (`is_sandbox=true`), identifier drawn from the isolated `StCd-T#####` band. *Dependencies:* EPIC-02. *Priority:* P1.
- **US-071** Sandbox codes are structurally excluded from default search, catalogue export, and Release candidates. *AC:* TC-014a, TC-023. *Dependencies:* US-070. *Priority:* P0 (verification story).
- **US-072** Administrator permanently deletes a sandbox code via typed-confirmation UI; blocked at both service and DB-trigger layers for any non-sandbox record. *AC:* TC-018a. *Dependencies:* US-070. *Priority:* P1.
- **US-073** Deletion writes a `SANDBOX_DELETE` audit entry with a full pre-delete snapshot; `SANDBOX_CREATE`/`SANDBOX_DELETE` pair remains queryable after the record is gone. *AC:* TC-015a. *Dependencies:* US-072. *Priority:* P0 (compliance-critical despite feature being P1).

---

## EPIC-08 — Deprecation & Archival

Unchanged in substance from v1 EPIC-06 (FR-050–FR-052), with deprecation of a Released code via Engineer CR now requiring the **full** dual-review-plus-Chief-Engineer-approval cycle rather than single-Reviewer approval. *Dependencies:* EPIC-06. *Priority:* P1.

---

## EPIC-09 — User & Lookup Administration

- **US-090** User list/create/edit with role + Engineering Domain tag assignment (S14). *Dependencies:* US-009. *Priority:* P1.
- **US-091** Manage Functional System Group / Functional Subgroup / Turbine Platform / Engineering Domain vocabularies, alongside the original 7 (S15). *Dependencies:* US-004. *Priority:* P1.
- **US-092** Engineer can propose a new lookup value (any vocabulary) for Administrator review. *Dependencies:* US-091. *Priority:* P2.
- **US-093** Administrator loads the real Functional Subgroup taxonomy, replacing the placeholder (data-only change, no deploy required beyond a seed update). *Dependencies:* US-091. *Priority:* P0 (MVP exit criterion, 16-mvp-roadmap.md §2), but not a blocking *development* dependency.

---

## EPIC-10 — Audit Trail & Reporting

Unchanged in substance from v1 EPIC-08, with the action catalogue expanded per 12-audit-compliance.md §2 (`REVIEWER_SIGNOFF`, `ADMIN_SIGNOFF`, `CHIEF_ENGINEER_APPROVE/REJECT`, `DOMAIN_SIGNOFF`, `SANDBOX_CREATE/DELETE`, `FULL_DATABASE_EXPORT`), and audit search access extended to the Chief Engineer role (scoped). *Dependencies:* threads through EPIC-02–EPIC-07. *Priority:* P0.

---

## EPIC-11 — REST API Hardening & Conformance

Unchanged in substance from v1 EPIC-09, extended to the new decision endpoints (`reviewer-signoff`, `admin-signoff`, `chief-engineer-decide`), domain sign-off endpoints, sandbox delete, and full-database export. *Dependencies:* built alongside each corresponding UI story. *Priority:* P0/P1.

---

## EPIC-12 — Security Hardening, Compliance & No-Cloud Verification

Unchanged in substance from v1 EPIC-10 (security headers, CSRF, XSS/SQLi prevention, `bandit`/`pip-audit`, manual OWASP checklist), plus:
- **US-120** CI grep-based check blocking any known cloud-SDK import. *AC:* TC-029. *Dependencies:* US-002. *Priority:* P0.
- **US-121** Manual no-cloud verification checklist (11-security-architecture.md §12) executed before each production deployment. *Dependencies:* all functional epics substantially complete. *Priority:* P0.

---

## EPIC-13 — Non-Functional: Performance, Deployment, Monitoring

Unchanged in substance from v1 EPIC-11, all infrastructure confirmed on-premises (14-deployment-architecture.md), performance validation now covering identifier-allocation contention within a popular Functional Group (TC-025). *Priority:* P0/P1.

---

## Dependency Graph Summary (Epic Level)

```
EPIC-01 (Foundation)
   │
   ├──▶ EPIC-02 (Data Model, Numbering & Validation)
   │        │
   │        ├──▶ EPIC-03 (Cross-Domain Sign-Off)
   │        │        │
   │        │        └──▶ EPIC-04 (Dual Review & Chief Engineer Approval)
   │        │                 │
   │        │                 ├──▶ EPIC-06 (Release Management)
   │        │                 │        │
   │        │                 │        └──▶ EPIC-08 (Deprecation & Archival)
   │        │                 │
   │        │                 └──▶ EPIC-10 (Audit Trail) [threads through 02-08]
   │        │
   │        ├──▶ EPIC-05 (Search, Browse, History)
   │        └──▶ EPIC-07 (Sandbox Status Codes)
   │
   ├──▶ EPIC-09 (User & Lookup Administration)
   ├──▶ EPIC-11 (API Hardening) [parallel, per-endpoint]
   ├──▶ EPIC-12 (Security & No-Cloud Verification) [parallel, cross-cutting]
   └──▶ EPIC-13 (Non-Functional / Deployment) [parallel, cross-cutting]
```

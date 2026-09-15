# 03. Software Requirements Specification (SRS) — CSCM Tool

## 1. Functional Requirements

### 1.1 Authentication & Session Management

- **FR-001** The system shall authenticate users via username/email and password using session-based authentication (server-side session, HttpOnly + Secure + SameSite=Strict cookie).
- **FR-002** The system shall enforce session expiry after 30 minutes of inactivity (configurable) and require re-authentication thereafter.
- **FR-003** The system shall allow a user to explicitly log out, invalidating the server-side session immediately.
- **FR-004** The system shall lock a user account for 15 minutes after 5 consecutive failed login attempts.
- **FR-005** The system shall provide an architecture hook (pluggable auth provider) for a future **on-premises Active Directory (LDAP/Kerberos) or ADFS/SAML** integration without changing the session/authorization model downstream, and shall never integrate with a cloud-hosted identity provider (see 08-system-architecture.md §7, 11-security-architecture.md §2).

### 1.2 User & Role Management

- **FR-010** The system shall allow an Administrator to create, edit, deactivate, and reactivate user accounts.
- **FR-011** The system shall allow an Administrator to assign exactly one of five roles (Administrator, Engineer, Reviewer, Chief Engineer, Viewer) per user.
- **FR-011a** The system shall allow an Administrator to tag an Engineer-role user with one or more Engineering Domains (06-data-dictionary.md §9j), used to route Cross-Domain Sign-Off (§1.3a).
- **FR-012** The system shall prevent deactivation of the last active Administrator account.
- **FR-013** The system shall allow a user to change their own password, enforcing the password policy in 11-security-architecture.md §4.
- **FR-014** The system shall allow an Administrator to force a password reset for any user.

### 1.3 Status Code Creation & Editing

- **FR-020** The system shall allow an Engineer or Administrator to create a new Status Code by specifying a Functional System Group (required) and Functional Subgroup (optional) and all mandatory attributes defined in 06-data-dictionary.md.
- **FR-021** The system shall NOT assign a fixed Status Code Identifier while a code is in Draft. It may offer a non-binding preview of the likely next identifier for display purposes only (`GET /status-codes/next-available`); the identifier is allocated exactly once, atomically, at the Draft→Review transition (05-governance-handbook.md §2, 07-database-design.md §7a).
- **FR-021a** The system shall allow an Administrator to override the automatically allocated identifier for a documented migration/reservation case, with the reason logged.
- **FR-022** The system shall reject creation or save of a Status Code Revision if any mandatory attribute is missing, malformed, or fails cross-field validation rules (06-data-dictionary.md "Validation" column).
- **FR-023** The system shall prevent creation of a duplicate `status_code_identifier` (unique constraint; see 07-database-design.md).
- **FR-023a** The system shall require at least one Turbine Platform to be selected before a revision can be submitted for Review.
- **FR-024** The system shall allow an Engineer to save an in-progress Status Code as Draft an unlimited number of times without triggering workflow transitions.
- **FR-025** The system shall NOT allow direct in-place editing of a Status Code Revision that is in Review, PendingApproval, Approved, Released, Deprecated, or Archived state; any change requires creating a new Draft revision from the current one (copy-on-write).
- **FR-025a** The system shall treat `access_rights_id` as a restricted field: an Engineer may propose a value while the revision is in Draft, but it is not authoritative until confirmed or overridden by the Administrator's Review sign-off (06-data-dictionary.md §2, SEC-013).
- **FR-026** The system shall allow an Engineer to withdraw/cancel a Draft, Review, or PendingApproval Change Request before it reaches Approved.

### 1.3a Cross-Domain Sign-Off

- **FR-027** The system shall determine, from the field-to-Engineering-Domain ownership mapping (06-data-dictionary.md §2a), which domains are required on a given revision, and shall flag any domain not covered by the originating Engineer's own domain tags as pending.
- **FR-028** The system shall allow the originating Engineer to request sign-off from an Engineer holding a required, pending domain, and shall surface that request on the target Engineer's Dashboard and Change Request list.
- **FR-029** The system shall block Submit-for-Review (422) while any required domain lacks a recorded `DomainSignoff`, and shall only accept a `DomainSignoff` from a user who actually holds the named Engineering Domain.

### 1.4 Change Request & Review Workflow

- **FR-030** The system shall require every creation of a new Status Code and every revision of an existing one to be represented as a Change Request (CR) that carries the proposed revision through the lifecycle.
- **FR-031** The system shall allow an Engineer to submit a Draft CR for Review, which allocates the Status Code Identifier (FR-021), transitions the associated revision from Draft to Review, and notifies eligible Reviewers and the Administrator.
- **FR-032** The system shall present Reviewers and the Administrator with a field-level diff between the proposed revision and the current Approved/Released revision of the same Status Code (or "new code" if none exists).
- **FR-033** The system shall allow a Reviewer to record an independent sign-off (approve or reject) on a CR in Review; rejection requires a mandatory comment and returns the revision to Draft, clearing both sign-off columns.
- **FR-034** The system shall allow an Administrator to record an independent sign-off (approve or reject) on a CR in Review, following the same rules as FR-033, and shall confirm or override any restricted field (FR-025a) at the moment of approval.
- **FR-035** The system shall automatically transition a CR from Review to PendingApproval, atomically with whichever sign-off action is recorded second, once both the Reviewer's and the Administrator's sign-offs are present (in either order).
- **FR-036** The system shall allow a Chief Engineer to record the final Approval decision (approve or reject) on a CR in PendingApproval; rejection requires a mandatory comment and returns the revision to Draft, clearing both prior sign-offs.
- **FR-037** The system shall prevent the Engineer who authored a CR from signing off or approving their own CR at any of the three decision points (Reviewer sign-off, Administrator sign-off, Chief Engineer approval), and shall additionally prevent the Chief Engineer decision from being made by whichever individuals already provided the Reviewer or Administrator sign-off on that same CR (BR-005).
- **FR-038** The system shall allow a Reviewer, Administrator, or Chief Engineer to add comments to a CR at any stage without changing its state.
- **FR-039** The system shall allow an Administrator to reassign or unassign a CR between Reviewers.

### 1.5 Release Management

- **FR-040** The system shall allow an Administrator to create a Release container with a name, target version label, description, and scope filter (e.g. Functional System Group, Functional Subgroup).
- **FR-041** The system shall list all non-sandbox Status Code Revisions in Approved state matching a Release's scope filter as candidates for inclusion.
- **FR-042** The system shall allow an Administrator to include/exclude individual candidate revisions before publishing.
- **FR-043** The system shall, upon publishing a Release, transition all included revisions from Approved to Released, stamp Effective Date, and mark the Release as immutable.
- **FR-044** The system shall prevent modification of a published Release's contents; a correction requires a new Release.
- **FR-045** The system shall allow export of any Release, or of the current set of all Released status codes, in CSV, JSON, and PDF formats, per the role-scoped catalogue-export matrix (11-security-architecture.md §3).
- **FR-046** The system shall allow export of a Draft/ad-hoc filtered working set, distinctly labeled "Not for distribution — unapproved data," restricted to Engineer/Reviewer/Administrator/Chief Engineer roles.
- **FR-047** The system shall allow an Administrator, and only an Administrator, to generate a full raw database export/backup, distinct from catalogue export (08-system-architecture.md §6, SEC-015).
- **FR-048** The system shall prevent a sandbox-flagged revision from ever being added to a Release candidate list or included in a published Release, enforced independently at the service layer and the database layer (07-database-design.md §5).

### 1.6 Deprecation & Archival

- **FR-050** The system shall allow an Administrator (or Engineer via CR, subject to the full three-decision-point cycle) to initiate deprecation of a Released Status Code, requiring a mandatory reason and an optional superseding identifier reference.
- **FR-051** The system shall allow an Administrator to archive a Deprecated Status Code after the configured minimum retention period has elapsed (05-governance-handbook.md §11); Archived codes become read-only.
- **FR-052** The system shall prevent deletion of any non-sandbox Status Code or Revision at any lifecycle state; removal from active use is only possible via Deprecated/Archived states.

### 1.6a Sandbox Status Codes

- **FR-053** The system shall allow an Administrator, and only an Administrator, to create a Status Code flagged `is_sandbox = true`, drawing its identifier from an isolated `StCd-T#####` band that never overlaps a real Functional System Group range.
- **FR-054** The system shall exclude sandbox-flagged records from default search results, catalogue exports, and Release candidate lists by construction, not by convention (FR-048).
- **FR-055** The system shall allow an Administrator, and only an Administrator, to permanently delete a sandbox-flagged Status Code, and shall reject any deletion attempt against a non-sandbox record regardless of role, enforced at both the service layer and a database trigger.
- **FR-056** The system shall record a `SANDBOX_DELETE` audit entry containing a full pre-delete snapshot of the deleted record, in the same transaction as the delete, so the fact of creation and deletion remains permanently traceable even though the record itself no longer exists.

### 1.7 Search, Filter, and Browse

- **FR-060** The system shall provide full-text search across Status Code Identifier, Title, and Description.
- **FR-061** The system shall provide filtering by Functional System Group, Functional Subgroup, Turbine Platform, Lifecycle State, Owner, Software Version, and sandbox flag (default excluded), individually or combined.
- **FR-062** The system shall provide sorting on any listed column, ascending or descending.
- **FR-063** The system shall paginate list results with a configurable page size (default 50, max 200).
- **FR-064** The system shall allow a Viewer or higher role to view the complete revision history of any non-Draft/Review/PendingApproval Status Code, including diffs between any two revisions; Draft/Review/PendingApproval-state data is visible to Engineer, Reviewer, Administrator, and Chief Engineer roles only (BR-009).

### 1.8 Audit Trail

- **FR-070** The system shall record an immutable audit log entry for every create, update, state transition, sign-off, approval, rejection, release, deprecation, archival, sandbox create/delete, login, failed login, role change, and export action, capturing actor, timestamp (UTC), entity type, entity ID, action, and before/after field values where applicable (12-audit-compliance.md).
- **FR-071** The system shall allow Administrators (and Reviewers/Chief Engineers, read-only, for records they are entitled to act on) to search and filter the audit log by actor, entity, action type, and date range.
- **FR-072** The system shall prevent any user, including Administrators, from editing or deleting audit log entries through the application.
- **FR-073** The system shall retain the audit trail for a deleted sandbox record indefinitely, even though the application provides no means of retrieving the record itself once deleted (FR-056).

### 1.9 API

- **FR-080** The system shall expose a versioned REST API (`/api/v1/...`) covering Status Codes, Revisions, Change Requests (incl. sign-off/approval/domain-sign-off endpoints), Releases, Users, Lookups, and Audit Log read access, per 09-api-specification.md.
- **FR-081** The system shall enforce the same role-based authorization on the API as on the UI; the API is not a privilege-escalation path.
- **FR-082** The system shall support API pagination, filtering, and sorting equivalent to the UI list capabilities (FR-061–FR-063).
- **FR-083** The system shall be reachable only from the internal corporate network in every deployment; no endpoint shall be exposed to the public internet, and no request shall be proxied through or dependent on a public-cloud service.

## 2. Non-Functional Requirements

### 2.1 Performance — NFR-001
Unchanged from v1 targets (13-test-strategy.md §5): 500ms p95 list/search at 20,000 revisions, 200ms p95 single-record read, 5s CSV/JSON export of 5,000 records, 15s PDF export of 5,000 records — now additionally validated for identifier-allocation contention within a single popular Functional System Group under concurrent submission (TC-025).

### 2.2 Availability — NFR-002
Unchanged from v1: 99.5% monthly availability during business hours, ≤ 4 hours/month scheduled maintenance.

### 2.3 Security — NFR-003
See 11-security-architecture.md. Summary: TLS 1.2+ only, on the internal network exclusively; no plaintext password storage/logging; CSRF protection on all state-changing endpoints; input validation and output encoding against injection; **no dependency on any public-cloud service, including for authentication, storage, or logging (NFR-003a, new in v2)**.

### 2.4 Scalability — NFR-004
Unchanged from v1: MVP architecture supports ≥ 50 concurrent named users and 20,000 revisions without breaching NFR-001; repository pattern preserves a PostgreSQL migration path.

### 2.5 Maintainability — NFR-005
Unchanged from v1: layered structure per 15-development-standards.md, business logic in the service layer, ≥ 80% line coverage on service-layer and validation code.

### 2.6 Auditability — NFR-006
Unchanged from v1, extended: 100% of state-changing actions (now including three decision points and sandbox create/delete) produce a corresponding audit log entry; retention ≥ 7 years, with the explicit sandbox-delete exception documented in 12-audit-compliance.md §3.

### 2.7 Usability — NFR-007
Unchanged from v1: core workflows completable by a trained user without external documentation; desktop-primary responsive layout down to 1024px.

### 2.8 Deployment Independence — NFR-008 (new in v2)
The system shall be deployable and fully operable on an isolated internal network with no outbound internet connectivity whatsoever — no feature in MVP scope may require reaching an external service to function. This is stricter than "no cloud dependency" alone: it is a testable claim (14-deployment-architecture.md §1) that the application continues to operate correctly with egress blocked entirely.

## 3. Business Rules

- **BR-001** A Status Code's identity is immutable once its identifier is allocated; it cannot be changed by editing, only superseded via deprecation.
- **BR-002** A Status Code has at most one revision flagged `is_current = true` at a time.
- **BR-003** Only one open (Draft, Review, or PendingApproval) revision may exist per Status Code at a time.
- **BR-004** A revision cannot transition to Released except via inclusion in a published Release, cannot reach Approved except via explicit Chief Engineer approval, and cannot reach PendingApproval except via both the Reviewer's and the Administrator's independent sign-off.
- **BR-005** No individual may both author and decide on the same Change Request at any of the three decision points (Reviewer sign-off, Administrator sign-off, Chief Engineer approval); the Chief Engineer additionally may not be whoever provided either of the two prior sign-offs on that CR.
- **BR-006** Deprecating a Status Code requires a reason; archiving requires the configured minimum retention period (default 180 days) to have elapsed since deprecation.
- **BR-007** A published Release's member revisions are immutable; correcting a released status code requires a new Draft revision, a new full three-decision-point cycle, and a new Release.
- **BR-008** Only Administrators may create, publish, or delete (pre-publish only) Releases.
- **BR-009** Viewers have read-only access to Approved, Released, Deprecated, and Archived data; Draft, Review, and PendingApproval-state data is visible only to Engineer, Reviewer, Administrator, and Chief Engineer roles.
- **BR-010** A sandbox-flagged Status Code may never be included in a Release, and is the only category of record that may be permanently deleted, and then only by an Administrator.
- **BR-011** Submit-for-Review is blocked while any Engineering-Domain-owned field lacks coverage from either the originating Engineer's own domain tags or a recorded `DomainSignoff`.
- **BR-012** The `access_rights_id` field is not authoritative until confirmed by the Administrator's Review sign-off, regardless of what value the originating Engineer proposed.

## 4. Constraints

- **C-001** MVP persistence is SQLite (single-file, file-based); this bounds MVP concurrent write throughput and requires the repository-pattern abstraction (NFR-004) to enable a later migration. SQLite is not intended as a permanent production datastore; see 16-mvp-roadmap.md for the Phase 3 migration trigger.
- **C-002** MVP authentication is session-based, internal user store only; on-premises AD/ADFS integration is out of scope for MVP (FR-005).
- **C-003** Backend framework is fixed to Python/Flask; frontend is server-rendered HTML/CSS/vanilla JavaScript, no external CDN dependency (11-security-architecture.md §12).
- **C-004** The application must run in the target on-premises deployment environment described in 14-deployment-architecture.md.
- **C-004a** No public cloud (SaaS/PaaS/IaaS) component may be introduced at any phase without an explicit, separate decision to relax C-004 (new in v2 — see 00-INDEX.md "Deployment Principle").
- **C-005** No bulk import feature exists in MVP; any legacy data migration is a one-time, human-reviewed project activity outside the application's feature set.

## 5. Assumptions

- **A-001** The initial user population is small (tens, not thousands, of named users across all five roles), consistent with NFR-004's 50-concurrent-user target.
- **A-002** Engineers, Reviewers, Administrators, Chief Engineers, and Viewers are employees or contractors with existing corporate accounts; user provisioning is manual (Administrator-driven) until on-prem AD/ADFS integration lands.
- **A-003** Status code catalogues across all nine Functional System Groups remain in the low tens of thousands of revisions over the system's MVP lifetime, consistent with NFR-001's sizing.
- **A-004** Technical Publications and any future SCADA/documentation-generation consumers will integrate against the versioned REST API or scheduled exports, over the internal network only; no direct database access will be granted to external systems.
- **A-005** The organization has an existing password/credential policy that CSCM Tool's password rules (11-security-architecture.md §4) can align with.
- **A-006** The real Functional Subgroup taxonomy will be supplied by Controls Engineering before production go-live; the placeholder seeded in this package (06-data-dictionary.md §9a) is structurally sufficient for development and testing in the meantime.
- **A-007** Chief Engineer is a distinct, sufficiently-staffed role in the organization such that the added approval step does not become a single-person bottleneck; this should be validated against actual staffing before go-live (16-mvp-roadmap.md §6 risk).

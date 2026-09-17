# 08. System Architecture Document — CSCM Tool

## 1. Architecture Overview

CSCM Tool (MVP) is a **monolithic, server-rendered web application**: Python/Flask backend, SQLite database, HTML/CSS/vanilla JavaScript frontend rendered via Jinja2 templates, with a REST API layer exposed alongside the server-rendered UI for future internal integrations. The entire system runs on a single local, on-premises server (or an on-prem virtualization cluster) with **no public-cloud (SaaS/PaaS/IaaS) component of any kind** — this is an explicit, non-negotiable deployment constraint (C-004, 14-deployment-architecture.md §1), not merely a default.

```
                         ┌─────────────────────────────┐
                         │   Web Browser (internal LAN) │
                         │  Server-rendered HTML/CSS/JS,│
                         │   session cookie             │
                         └──────────────┬───────────────┘
                                        │ HTTPS (TLS 1.2+, internal network only)
                         ┌──────────────▼───────────────┐
                         │   Flask Application (on-prem)  │
                         │ ┌───────────────────────────┐ │
                         │ │  Presentation (UI + API      │ │
                         │ │  blueprints)                 │ │
                         │ └──────────────┬────────────┘ │
                         │ ┌──────────────▼────────────┐ │
                         │ │  Service Layer (workflow,     │ │
                         │ │  dual-review + Chief Engineer │ │
                         │ │  approval, numbering, audit)  │ │
                         │ └──────────────┬────────────┘ │
                         │ ┌──────────────▼────────────┐ │
                         │ │  Repository Layer             │ │
                         │ └──────────────┬────────────┘ │
                         └────────────────┼───────────────┘
                                          │
                         ┌────────────────▼───────────────┐
                         │  SQLite Database File (local disk)│
                         │  = the Master Database (§6)        │
                         └───────────────────────────────────┘

   Future (Phase 2+, on-premises only — no cloud component is ever introduced):
   ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
   │ On-prem Active      │  │ Doc-generation tool│   │ SCADA / repositories│
   │ Directory / ADFS     │  │ (consumes REST API, │   │ (consume REST API,  │
   │ (auth provider)      │  │  internal network)   │   │  internal network)  │
   └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
```

## 1a. Presentation Layer & OneTool Shell (new 2026-09-17)

CSCM Tool's UI renders inside the shared OneTool platform shell (top bar, sidebar, navigation), per the OneTool design system supplied by the central tools team (10-ui-ux-specification.md §0). This affects only the `presentation`/`ui` component below — the shared shell is markup/CSS/JS that CSCM Tool includes and themes to, not a service CSCM Tool calls. **Authentication remains entirely CSCM Tool's own** (confirmed decision): the `auth` component is unaffected by this integration; only the visual chrome is shared, never identity, session, or credentials.

## 2. Component Diagram

| Component | Responsibility | Depends on |
|---|---|---|
| `presentation` (Flask Blueprint: `ui`) | Server-rendered pages, forms, navigation | `service` (via internal calls) |
| `api` (Flask Blueprint: `api_v1`) | JSON REST endpoints | `service` |
| `service` | Business rules, lifecycle transitions, numbering allocation, dual-review/Chief-Engineer-approval orchestration, Cross-Domain Sign-Off gating, validation, audit writes | `repository` |
| `repository` | Data access abstraction (one repository class per aggregate) | `models` (SQLAlchemy), DB connection |
| `auth` | Session management, password hashing, RBAC decorators (5 roles), pluggable on-premises auth provider interface | `service.user` |
| `export` | CSV/JSON/XLSX/PDF catalogue export (all roles per matrix) + full-database export/backup (Administrator only) | `service.release`, `service.status_code` |
| `audit` | Central audit-log writer used by all services | `repository.audit` |

Full detail and code layout: 18-claude-code-implementation-guide.md.

## 3. Deployment Diagram

See 14-deployment-architecture.md for complete environment detail — a single on-premises server (or on-prem cluster), reverse proxy terminating TLS, WSGI-hosted Flask app, local-disk SQLite file with nightly backup, all inside the corporate network with no external connectivity by default.

## 4. Data Flow Diagram (Change Request Lifecycle, v2)

```
[Engineer] --create Draft (select Functional Group [+Subgroup])--> [StatusCodeService.create_draft()]
      |                                    (identifier = NULL at this point)
      |
      +--[if cross-domain fields unset]--> flagged "awaiting domain input"
      |         |
      |         +--[second Engineer, correct domain]--> [DomainSignoffService.sign()] --> domain_signoff row
      |
      +--submit for Review--> [ChangeRequestService.submit()]
                  |
                  +--validates completeness + all domain sign-offs present
                  +--ALLOCATES status_code_identifier atomically (07-database-design.md §7a)
                  +--transitions Draft -> Review
                  |
      [Reviewer] --sign off--> [ChangeRequestService.reviewer_signoff()] --\
      [Administrator] --sign off--> [ChangeRequestService.admin_signoff()] --+--> on 2nd sign-off,
                                                                                system auto-transitions
                                                                                Review -> PendingApproval
                  |
      [Chief Engineer] --approve/reject--> [ChangeRequestService.chief_engineer_decide()]
                  |
                  +--approve--> PendingApproval -> Approved
                  +--reject (mandatory comment)--> PendingApproval -> Draft
                  |
      [Administrator] --publish Release (bundles Approved revisions)--> [ReleaseService.publish()]
                  |
                  +--atomic: Approved -> Released, effective_date stamped, release locked
```

Every arrow above writes exactly one (or, for the Release publish fan-out, one-per-item) `audit_log_entry` in the same transaction (12-audit-compliance.md).

## 5. Sequence Diagrams

### 5.1 Submit for Review (identifier allocation)
```
Engineer -> UI: click "Submit for Review"
UI -> API: POST /api/v1/change-requests/{id}/submit
API -> ChangeRequestService: submit(cr_id, actor=Engineer)
ChangeRequestService -> ValidationService: validate_revision(revision)
ChangeRequestService -> DomainSignoffService: all_required_domains_signed(revision)
alt validation fails OR domain sign-offs incomplete
    ChangeRequestService --> API: 422 (field errors / missing domain sign-offs)
else all clear
    ChangeRequestService -> Repository: BEGIN IMMEDIATE
    ChangeRequestService -> Repository: allocate_next_identifier(group, subgroup)  [07-database-design.md §7a]
    ChangeRequestService -> Repository: update status_code.status_code_identifier
    ChangeRequestService -> Repository: update revision.lifecycle_status = REVIEW
    ChangeRequestService -> Repository: update change_request.state = REVIEW, submitted_at
    ChangeRequestService -> AuditService: log(SUBMIT_FOR_REVIEW, IDENTIFIER_ALLOCATED)
    Repository -> SQLite: COMMIT
    ChangeRequestService --> API: 200 OK (StCd-01232 now visible)
end
```

### 5.2 Dual Review Sign-Off
```
Reviewer -> UI: click "Sign Off" (with optional comment)
UI -> API: POST /api/v1/change-requests/{id}/reviewer-signoff
API -> AuthZ: assert role == REVIEWER AND actor != cr.requested_by
API -> ChangeRequestService: reviewer_signoff(cr_id, actor, decision, comment)
ChangeRequestService -> Repository: BEGIN IMMEDIATE
ChangeRequestService -> Repository: insert review_comment (decision=REVIEWER_APPROVE|REJECT)
alt decision == REJECT
    ChangeRequestService -> Repository: revision.lifecycle_status = DRAFT; clear reviewer_signoff_by/at
else decision == APPROVE
    ChangeRequestService -> Repository: revision.reviewer_signoff_by/at = actor/now
    ChangeRequestService -> Repository: if revision.admin_signoff_by IS NOT NULL:
                                             revision.lifecycle_status = PENDING_APPROVAL
end
ChangeRequestService -> AuditService: log(REVIEWER_SIGNOFF)
Repository -> SQLite: COMMIT
```
(The Administrator sign-off endpoint is symmetric, with `admin_signoff_by/at` and the same second-signoff check against `reviewer_signoff_by`.)

### 5.3 Chief Engineer Approval
```
Chief Engineer -> UI: click "Approve" / "Reject"
UI -> API: POST /api/v1/change-requests/{id}/chief-engineer-decide
API -> AuthZ: assert role == CHIEF_ENGINEER AND actor NOT IN {requested_by, reviewer_signoff_by, admin_signoff_by}
API -> ChangeRequestService: chief_engineer_decide(cr_id, actor, decision, comment)
ChangeRequestService -> Repository: BEGIN IMMEDIATE
ChangeRequestService -> Repository: insert review_comment (CHIEF_ENGINEER_APPROVE|REJECT)
alt approve
    ChangeRequestService -> Repository: revision.chief_engineer_approved_by/date = actor/now; lifecycle_status = APPROVED
else reject
    ChangeRequestService -> Repository: revision.lifecycle_status = DRAFT; clear both sign-off pairs
end
ChangeRequestService -> AuditService: log(CHIEF_ENGINEER_APPROVE | CHIEF_ENGINEER_REJECT)
Repository -> SQLite: COMMIT
```

### 5.4 Sandbox Status Code Create/Delete
```
Administrator -> UI: "New Sandbox Status Code"
UI -> API: POST /api/v1/status-codes {is_sandbox: true, ...}
API -> StatusCodeService: create_sandbox(actor=Administrator)
StatusCodeService -> Repository: allocate from isolated StCd-T##### counter (never touches real ranges)
StatusCodeService -> AuditService: log(SANDBOX_CREATE)
...
Administrator -> UI: "Delete Sandbox Code"
UI -> API: DELETE /api/v1/status-codes/{id}
API -> AuthZ: assert role == ADMINISTRATOR AND status_code.is_sandbox == true
API -> StatusCodeService: delete_sandbox(id, actor)
StatusCodeService -> AuditService: log(SANDBOX_DELETE, before_value=full snapshot)
StatusCodeService -> Repository: DELETE FROM status_code WHERE id=:id   [DB trigger permits only is_sandbox=1]
Repository -> SQLite: COMMIT
```

## 6. Master Database & Integration Architecture

CSCM Tool's own on-premises SQLite database **is** the Master Database — there is no separate, external "master" system this application synchronizes with. The only ways data leaves the system:

| Consumer | Mechanism | Scope | Role Required |
|---|---|---|---|
| Technical Publications / manuals | Administrator- or role-scoped catalogue export (CSV/JSON/XLSX/PDF) of Approved/Released status codes | Approved/Released only, per role matrix | Per 11-security-architecture.md §3 (all roles except sandbox-only data) |
| Disaster recovery / migration | Full database export/backup | Entire database | **Administrator only** (FR-047, 04-domain-model.md §2.17) |
| Future documentation-generation tools, SCADA, software repositories (Phase 2+) | REST API pull, internal corporate network only, never internet-exposed, never a cloud endpoint | Released catalogues only | Scoped API token, Administrator-issued |

No system pushes data **into** CSCM Tool in MVP or any planned phase — status codes are authored exclusively inside the application (this is the entire premise of the tool per 01-executive-summary.md §1), so there is no inbound "connect to Master DB" integration to build; the relevant integration surface is entirely outbound/export, exactly as summarized above.

## 7. Authentication Provider Abstraction

The `auth` component defines an `AuthProvider` interface with one MVP implementation (`SessionPasswordAuthProvider`) and a reserved seam for a future **on-premises** identity provider:

```python
class AuthProvider(Protocol):
    def authenticate(self, credentials: dict) -> AuthenticatedUser | None: ...
    def get_login_url(self) -> str | None: ...   # None for session/password
```

**Correction from the original stack assumption:** the future SSO path is **on-premises Active Directory (LDAP/Kerberos) or on-prem ADFS/SAML federation**, not Azure AD/OIDC — Azure AD is a Microsoft-hosted cloud identity service and is incompatible with the no-cloud-infrastructure requirement (00-INDEX.md "Deployment Principle", 11-security-architecture.md §2, 14-deployment-architecture.md §1). Flask route handlers and the service layer depend only on `AuthenticatedUser`, never on `AuthProvider` implementation details, so this remains an additive change (16-mvp-roadmap.md Phase 2), just against a different, on-prem-compatible target.

## 8. Scalability, Caching, Backup Strategy

Unchanged in mechanism from v1 (08-system-architecture.md v1 §8–§10): MVP sizing targets, SQLite WAL-mode read concurrency, in-process lookup caching, nightly SQLite Online Backup API snapshots. All infrastructure referenced there is local/on-premises; no external or cloud storage target is introduced by this update.

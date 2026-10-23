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
| `auth` | Session management, password hashing, RBAC decorators (6 roles), pluggable on-premises auth provider interface | `service.user` |
| `export` | CSV/JSON/XLSX/PDF catalogue export (all roles per matrix) + full-database export/backup (Administrator only) | `service.release`, `service.status_code` |
| `audit` | Central audit-log writer used by all services; since v4 also the hash chain hook, verification and archiving (`app/audit_chain.py`) | `repository.audit` |
| `publication` *(v4)* | Export pipeline with profiles, audiences, languages, software versions, manifests, release notes, offline bundle (`export_service`, `manifest_service`, `audience_service`, `release_notes_service`, `translation_service`, `software_version_service`) | `service.release`, `service.status_code` |
| `governance extensions` *(v4)* | Step-up, delegation, SLA ageing and notices, change sets, field comments and checklists, attachments, KPIs (`auth_service`, `delegation_service`, `sla_service`, `notification_service`, `change_set_service`, `field_review_service`, `attachment_service`, `kpi_service`) | `service.change_request`, `repository` |
| `import` *(v4)* | Library import toolkit: template, dry run, update mode, reconciliation, error reports, background worker (`import_service`) | `service.status_code` |
| `integration` *(v4)* | Scoped API tokens, change feed, webhooks, fleet-feedback import, Hub-to-Main consolidation (`integration_service`, `occurrence_service`, `hub_consolidation_service`) | `service`, `repository` |
| `operations` *(v4)* | Backups with verified restore, readiness and metrics, health report, settings, logging, CLI jobs (`backup_service`, `observability`, `health_report_service`, `settings_service`, `cli`) | `repository`, OS scheduler |
| `i18n` *(v4)* | English/German interface catalogue, help content (`app/i18n.py`, `app/i18n_de.py`, `app/help_content.py`) | `presentation` |

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

## 5a. Added Request Flows (v4)

- **Step-up and delegation (FR-125, FR-126).** A decision route is guarded by `require_role_or_delegate`: the actor's role, or an active `delegation` for that role, admits the call; `AuthService.step_up` then verifies the password in the request body (once per request — a change-set decision reuses `g.step_up_verified`) and audits `STEP_UP_SUCCESS` / `STEP_UP_FAILURE`; only then does the service run its usual segregation-of-duties checks and write the audit entry naming actor and `on_behalf_of`.
- **Export (FR-100 … FR-111).** `ExportService._prepare` selects revisions (release, released set or working set), applies the audience filter and software-version filter, resolves translations, and builds the rows with the profile's columns; `_render` produces CSV/JSON/XLSX/PDF; `manifest_service` hashes the file(s) and signs the manifest; `_record` stores the `export_job` (hash, size, rows, options, manifest) and an audit entry; with `bundle` the data file, `MANIFEST.json` and the release notes are zipped.
- **Publish (FR-043, FR-106, FR-146).** Password check → state checks (Release still BUILDING, at least one item) → atomic transition of all items to Released with one audit entry each → commit → webhook dispatch *after* the commit (the candidate list, limited to the target versions, is built earlier by the release builder) (a delivery problem is recorded and never undoes or fails the publish).
- **Import (FR-048i … FR-048n).** Upload → header check → per-row evaluation (rules of manual entry plus duplicate and legacy-number checks) → dry run stops here, otherwise rows are applied one transaction each (create, update in place, new revision, skip) → error report CSV/XLSX → job COMPLETE; above the row threshold the apply phase runs in a worker thread and the request returns 202.
- **Audit write (FR-151).** Every `audit_log_entry` insert passes the `before_flush` hook, which reads the last stored `entry_hash` inside the same write transaction and chains the new rows in insertion order.

## 6. Master Database & Integration Architecture

CSCM Tool's own on-premises SQLite database **is** the Master Database — there is no separate, external "master" system this application synchronizes with. The only ways data leaves the system:

| Consumer | Mechanism | Scope | Role Required |
|---|---|---|---|
| Technical Publications / manuals | Administrator- or role-scoped catalogue export (CSV/JSON/XLSX/PDF) of Approved/Released status codes | Approved/Released only, per role matrix | Per 11-security-architecture.md §3 (all roles except sandbox-only data) |
| Disaster recovery / migration | Full database export/backup | Entire database | **Administrator only** (FR-047, 04-domain-model.md §2.17) |
| Documentation-generation tools, SCADA, software repositories | REST API pull, internal corporate network only, never internet-exposed, never a cloud endpoint | Released catalogues only (Viewer-level visibility) | Scoped, expiring API token, Administrator-issued (FR-144, SEC-027) |
| The same consumers, event-driven | `GET /changes` change feed (polling, ETag) and signed webhooks on `release.published` to private/loopback addresses | Release and lifecycle events | Token with scope `changes:read`; webhook secret (FR-145, FR-146, SEC-028) |
| Monitoring | `GET /health`, `GET /health/ready` (unauthenticated, no business data), `GET /metrics` (allow-listed networks, optional bearer token) | Operational state only | Network allow-list (SEC-029) |

No system pushes data **into** CSCM Tool — status codes are authored exclusively inside the application (this is the entire premise of the tool per 01-executive-summary.md §1), so there is no inbound "connect to Master DB" integration to build; the relevant integration surface is outbound/export, as summarized above. The only data that enters other than by typing is *file uploads started by a person*: the legacy library import (FR-048a, which creates Drafts only, BR-015) and the anonymised occurrence counts of the fleet-feedback import (FR-143, which change no status code).

## 7. Authentication Provider Abstraction

The `auth` component defines an `AuthProvider` interface with one MVP implementation (`SessionPasswordAuthProvider`) and a reserved seam for a future **on-premises** identity provider:

```python
class AuthProvider(Protocol):
    def authenticate(self, credentials: dict) -> AuthenticatedUser | None: ...
    def get_login_url(self) -> str | None: ...   # None for session/password
```

**Correction from the original stack assumption:** the future SSO path is **on-premises Active Directory (LDAP/Kerberos) or on-prem ADFS/SAML federation**, not Azure AD/OIDC — Azure AD is a Microsoft-hosted cloud identity service and is incompatible with the no-cloud-infrastructure requirement (00-INDEX.md "Deployment Principle", 11-security-architecture.md §2, 14-deployment-architecture.md §1). Flask route handlers and the service layer depend only on `AuthenticatedUser`, never on `AuthProvider` implementation details, so this remains an additive change (16-mvp-roadmap.md Phase 2), just against a different, on-prem-compatible target.

## 8. Scalability, Caching, Backup Strategy

MVP sizing targets, SQLite WAL-mode read concurrency, in-process lookup caching and nightly SQLite Online Backup API snapshots (now verified, see below). All infrastructure referenced there is local/on-premises; no external or cloud storage target is introduced by this update.

**Multi-process operation (v4, NFR-009).** Waitress may run as several processes against the one SQLite file: anything that must be consistent between them lives in the database (the login rate limit in `login_attempt`, the audit chain read from the last stored row inside the write transaction, number allocation under `BEGIN IMMEDIATE`); the in-process metrics registry is per process and each process is scraped separately. Large imports run in a daemon thread of the process that received the upload (FR-048n); the job row, not the thread, is the source of truth for progress, so another process or a restart can report it. Behind a reverse proxy the real client address reaches the rate limit through `CSCM_TRUSTED_PROXY` (`scripts/serve.py`).

**Backups, readiness and metrics (v4).** `flask backup-db` copies the live database with SQLite's online-backup API, proves the copy (integrity check, restore into a scratch database, row-count comparison, audit-chain check) and writes `backup_status.json`; `GET /health/ready` reads it together with the schema's Alembic head and the newest audit rows; `GET /metrics` exposes request, latency, lock-wait, queue and backup gauges (FR-150, FR-152, FR-153; procedures in 14-deployment-architecture.md §6–§8).

**Transaction modes (added 2026-10-21, NFR-004):** only writers take the SQLite write lock up front (`BEGIN IMMEDIATE`, required for race-safe identifier allocation, 07-database-design.md §7a). Read-only requests — `GET`/`HEAD`/`OPTIONS` not marked with `@writes_on_get` (`app/db_modes.py`; the export endpoints are, because they record an `ExportJob` and an audit entry) — use a deferred `BEGIN`, so in WAL mode readers neither block nor are blocked by a writer. Taking the write lock for every transaction serialised the whole application and produced `database is locked` errors with 50 concurrent users; `busy_timeout` is 15 s so writers queue instead of failing fast. Covered by `tests/performance/test_performance.py`.

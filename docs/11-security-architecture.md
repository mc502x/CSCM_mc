# 11. Security Architecture — CSCM Tool

## 1. Overview

CSCM Tool holds engineering-governed data with compliance/audit obligations (05-governance-handbook.md, 12-audit-compliance.md) and is deployed **exclusively on-premises, on a local server, with no public-cloud component of any kind** (00-INDEX.md "Deployment Principle", 14-deployment-architecture.md §1). Controls below are sized to that threat model while following OWASP baseline practice.

## 2. Authentication

- **SEC-001** Session-based authentication; credentials verified against `user.password_hash` using Argon2id (preferred) or bcrypt (cost ≥ 12). Plaintext/reversible storage is prohibited absolutely.
- **SEC-002** Session cookie attributes: `HttpOnly`, `Secure`, `SameSite=Strict`; identifier is a cryptographically random 128-bit+ value.
- **SEC-003** Idle session timeout 30 minutes; absolute session lifetime 12 hours.
- **SEC-004** Account lockout: 5 consecutive failed attempts locks the account for 15 minutes.
- **SEC-005** The authentication subsystem sits behind the `AuthProvider` interface (08-system-architecture.md §7) so a future SSO integration is additive. **Since v4.7 the Windows sign-in is built behind a gateway (SEC-033) and can be simulated on a developer machine; the long-term SSO target remains on-premises Active Directory (LDAP/Kerberos) or on-prem ADFS/SAML federation — not a cloud identity provider such as Azure AD.** This corrects the original stack assumption and is a hard requirement flowing from the no-cloud-infrastructure constraint; no OIDC/cloud-IdP code path may be introduced at any phase without an explicit, separate decision to relax that constraint.
- **SEC-006** (new 2026-09-17) CSCM Tool's integration with the shared OneTool platform (10-ui-ux-specification.md §0) is **visual only** — shared top bar, sidebar, design tokens, and component treatments. It shares no authentication, session, or credential mechanism with OneTool: `SessionPasswordAuthProvider` (and, later, the on-prem AD/ADFS provider above) remains CSCM Tool's sole identity source. No code path may accept a OneTool-issued session or token as proof of CSCM Tool identity without an explicit, separate decision to relax this boundary — confirmed explicitly by the business, not a default worth quietly reconsidering during implementation.

## 3. Authorization — Role-Based Access Control

Six fixed roles: Administrator, StCd Owner, Engineer, Reviewer, Chief Engineer, Viewer (00-INDEX.md "Roles"); the StCd Owner was added in v4.3 (FR-156, BR-024). Permission matrix (✓ = allowed; blank = denied; enforced identically at UI and API):

| Action                                                                    | Administrator  | Engineer              | Reviewer       | Chief Engineer                              | Viewer                     | StCd Owner |
| ------------------------------------------------------------------------- | -------------- | --------------------- | -------------- | ------------------------------------------- | -------------------------- | --- |
| View Approved/Released/Deprecated/Archived codes                          | ✓              | ✓                     | ✓              | ✓                                           | ✓                          | ✓ |
| View Draft/Review/PendingApproval-state codes                             | ✓              | ✓                     | ✓              | ✓                                           | —                          | ✓ |
| Create Status Code / Change Request                                       | ✓              | ✓                     | —              | —                                           | —                          | — |
| Create Sandbox Status Code                                                | ✓              | —                     | —              | —                                           | —                          | — |
| Delete Sandbox Status Code                                                | ✓              | —                     | —              | —                                           | —                          | — |
| Edit own Draft revision                                                   | ✓              | ✓                     | —              | —                                           | —                          | — |
| Provide Cross-Domain Sign-Off                                             | —              | ✓ (matching domain)   | —              | —                                           | —                          | — |
| Submit CR for Review (allocates identifier)                               | ✓              | ✓ (own CR)            | —              | —                                           | —                          | — |
| Reviewer sign-off (Review)                                                | —              | —                     | ✓ (not own CR) | —                                           | —                          | — |
| Administrator sign-off (Review)                                           | ✓ (not own CR) | —                     | —              | —                                           | —                          | — |
| Chief Engineer approval (PendingApproval)                                 | —              | —                     | —              | ✓ (not requester/reviewer/admin on this CR) | —                          | — |
| Build/Publish Release                                                     | ✓              | —                     | —              | —                                           | —                          | — |
| Deprecate Released code                                                   | ✓              | ✓ (via full CR cycle) | —              | —                                           | —                          | — |
| Archive Deprecated code                                                   | ✓              | —                     | —              | —                                           | —                          | — |
| Manage Users/Roles/Engineering Domain tags                                | ✓              | —                     | —              | —                                           | —                          | role only, among Viewer / Engineer / Reviewer (BR-024) |
| Manage all Lookup Vocabularies (incl. Functional Group/Subgroup/Platform) | ✓              | — (propose only)      | —              | —                                           | —                          | — |
| View Audit Log                                                            | ✓              | —                     | ✓ (scoped)     | ✓ (scoped)                                  | —                          | — |
| Export catalogue (CSV/JSON/XLSX/PDF)                                      | ✓              | ✓                     | ✓              | ✓                                           | ✓ (Approved/Released only) | ✓ |
| Export full database (password confirmation)                              | ✓              | —                     | —              | —                                           | —                          | — |
| Publish Release (password confirmation)                                   | ✓              | —                     | —              | —                                           | —                          | — |
| Delegate own decision role / act as delegate (decision actions only)      | ✓              | —                     | ✓              | ✓                                           | —                          | — |
| Attach / download evidence on a CR                                        | ✓              | ✓ (own CR)            | ✓ (download)   | ✓ (download)                                | —                          | — |
| Comment on a field; confirm review checklist                              | ✓              | —                     | ✓              | ✓ (comment)                                 | —                          | — |
| Create change sets / decide several requests in one sitting               | ✓              | ✓ (create)            | ✓ (decide)     | ✓                                           | —                          | — |
| Save / approve a translation                                              | ✓              | ✓ (save)              | ✓ (approve, not own) | —                                     | read approved only         | — |
| Manage export profiles, review checklist, settings                        | ✓              | —                     | —              | —                                           | —                          | — |
| Issue / revoke API tokens; manage webhooks                                | ✓              | —                     | —              | —                                           | —                          | — |
| View catalogue health report                                              | ✓              | —                     | ✓              | ✓                                           | —                          | — |
| View success metrics; import and view fleet feedback                      | ✓              | —                     | —              | ✓                                           | —                          | — |
| Backup status, audit-chain verification                                   | ✓              | —                     | —              | —                                           | —                          | — |
| Create users; force a password reset | ✓ | — | — | — | — | — |
| Change a user's role | ✓ (any role) | — | — | — | — | Viewer / Engineer / Reviewer only |
| Read change requests, change sets and the Hub mapping without acting | ✓ | ✓ | ✓ | ✓ | — | ✓ (read only) |

- **SEC-010** Authorization checks live in the service layer, not only route decorators/UI conditionals. Implemented as `require_roles()` (`app/domain/authz.py`) at the top of every role-restricted service entry point, raising `ForbiddenError` (HTTP 403); `tests/integration/test_governance_extras.py` calls each service directly with a wrong-role actor.
- **SEC-011** Segregation-of-duties is a hard server-side check at all three decision points (§3 of 09-api-specification.md): Reviewer sign-off, Administrator sign-off, and Chief Engineer approval each independently reject if the actor matches the CR's author or, for the Chief Engineer step, either of the two prior sign-offs. Since v4 it holds for **delegates** as well (they are checked as themselves, the two Review sign-offs must come from two different people) and for **change-set decisions** (each request is decided by its own service call with its own check).
- **SEC-012** Principle of least privilege: default role on new user creation is Viewer.
- **SEC-013** Restricted-field enforcement: each of the eight audience-access fields (corrected 2026-09-17 — replaces the single `access_rights_id`: `development_access`, `sales_access`, `tcc_access`, `service_access`, `turbine_operator_package_access`, `grid_operator_access`, `service_partner_access`, `customer_access`) on a revision may be written by an Engineer only while the revision is in `DRAFT`; none becomes authoritative until stamped by the Administrator's sign-off action, which is the sole path by which `admin_signoff_at` becomes non-null (06-data-dictionary.md §2d, "restricted field"). This is enforced in the service layer, not merely a UI convention.
- **SEC-014** `DELETE /status-codes/{id}` is authorized only when both `actor.role == ADMINISTRATOR` **and** `status_code.is_sandbox == true`; the second condition is additionally enforced by a database trigger (`trg_prevent_nonsandbox_delete`, 07-database-design.md §5) as defense in depth against a service-layer bug.
- **SEC-015** `POST /exports/full-database` (a `GET` before v4) is authorized only for `actor.role == ADMINISTRATOR` and needs the actor's password (SEC-026); no other role, including Chief Engineer, may reach it. A delegate never inherits it (delegation covers decision actions only, SEC-011, BR-017).


### 3a. Review of the role rights (2026-10-23)

The matrix above was reviewed role by role when the StCd Owner was added. What the review found, and what was done:

| Role | Finding | Outcome |
|---|---|---|
| Administrator | Holds data entry, the Administrator sign-off, publishing, lookups and user administration at once. Segregation of duties per change request (SEC-011) keeps the sign-offs apart, but the account is powerful. | Kept as the highest role (red). Handing out the three lower roles moved to the StCd Owner as well, so an Administrator is no longer needed for everyday role changes; creating users and the three upper roles stay here. |
| StCd Owner | New. Needs to see what is going on in the library and to place people, not to decide. | Read-only oversight of the workflow and the full catalogue; role changes among Viewer, Engineer, Reviewer; no decisions, no data entry, no import, no lookups, no audit log. |
| Chief Engineer | Final approval only; cannot see the user list or the lookups, which is right. | Unchanged. |
| Reviewer | Sees the audit log (scoped), the health report and decides the first review step. | Unchanged. |
| Engineer | Creates and edits Drafts, can import. Domain tags decide which cross-domain sign-offs the Engineer may give. | Unchanged. |
| Viewer | Sees decided data only. | Unchanged. |

Open points for the business (not built): (1) an StCd Owner who promotes somebody to Engineer cannot tag their engineering domains, so the new Engineer cannot give cross-domain sign-offs until an Administrator tags them — decide whether the owner may tag domains; (2) delegation covers Reviewer, Administrator and Chief Engineer only, the StCd Owner cannot be covered by a colleague; (3) whether the StCd Owner should read the audit log; (4) a second person's confirmation when an Administrator role is handed out.

## 4. Password Policy

12-char minimum, no mandatory character-class rules, breach-corpus blocklist, no mandatory expiry, last-5 reuse block, Argon2id/bcrypt storage, TLS-only transmission.

## 5. Session Management

Server-side session store, immediate revocation on logout/forced reset/deactivation, login rate limiting (10/IP/5min, 5/username/15min independently), CSRF synchronizer-token protection on all state-changing requests. Since v4 the rate-limit counters are rows in `login_attempt`, written inside the login request's write transaction, so they are shared by every worker process and survive a restart (NFR-009); behind a reverse proxy the real client address is taken from `X-Forwarded-For` only when the proxy is named in `CSCM_TRUSTED_PROXY`.

## 6. Input Validation

- **SEC-020** All input is validated server-side against the rules in 06-data-dictionary.md regardless of client-side validation state (client-side validation is a UX convenience only, never a trust boundary).
- **SEC-021** Parameterized queries / ORM bound parameters exclusively — no string-concatenated SQL anywhere in the codebase, enforced via code review checklist (15-development-standards.md).
- **SEC-022** All user-supplied text rendered in HTML (Title, Description, comments, justifications, the eight audience-access field labels) is output-encoded by the templating engine's auto-escaping (Jinja2 default autoescape must remain enabled; raw/`|safe` filters are prohibited on user-supplied content).
- **SEC-023** File export generation (CSV/XLSX/PDF) sanitizes any field that could trigger CSV formula injection (leading `=`, `+`, `-`, `@` characters are prefixed with a single quote or tab on export).
- **SEC-024** Any file-upload feature must go through file-type allow-listing, size limits, and storage outside the web root before it ships. The library import (05-governance-handbook.md §6b) was the first: uploaded CSV/XLSX files are validated for type and size before parsing, and the raw upload is never executed or served back to a browser. **Evidence attachments (v4, FR-130)** add: an allow-list (PDF, PNG, JPG, TXT, LOG, MD, CSV, XLSX, DOCX), content checks against the claimed type (magic bytes), at most 10 MB and 20 files per CR, a SHA-256 per file, storage under `instance/attachments` outside the web root, download only as an attachment (`Content-Disposition`, `nosniff`) to the working roles, removal only while the CR is a Draft. Import error reports neutralise values that start with a formula character. The `.st` program import (FR-048o, SEC-031) follows the same rules.
- **SEC-025** Every response carries standard security headers (`Content-Security-Policy` with self-only sources and no inline script, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, `Cache-Control: no-store` outside `/static/`, and HSTS on HTTPS requests). Implemented in `app/security_headers.py`; templates therefore carry no inline `<script>` or `on*=` handlers (`tests/system/test_security_headers.py`).

The Cross-Domain Sign-Off text fields and comment fields (`review_comment.comment_text`) follow the same output-encoding rule (SEC-022) as Title/Description.

## 7. Transport & Data Protection

TLS 1.2+ (internal network only — never internet-facing, per the no-cloud constraint), HSTS, standard security headers, OS-level ACL on the SQLite file. **Data-at-rest note specific to full-database exports (SEC-015):** the exported backup file carries the same sensitivity as the live database and must be stored with equivalent access control from the moment it is generated — the export feature itself does not weaken protection, but it does create a second copy of the Master Database that the Administrator is responsible for handling per this section (14-deployment-architecture.md §5).

## 8. Role-Based Access Control — Enforcement Points

API route decorator → service-layer check → database constraint/trigger → UI conditional rendering), now covering five roles and the additional decision/sandbox/export checks in §3.

## 9. Audit Trail (Security-Relevant Events)

Plus, since v4: `STEP_UP_SUCCESS`, `STEP_UP_FAILURE`, `DELEGATION_CREATE`, `DELEGATION_REVOKE`, `API_TOKEN_CREATE`, `API_TOKEN_REVOKE`, `WEBHOOK_CREATE`, `WEBHOOK_UPDATE`, `SETTINGS_CHANGE`, `ATTACHMENT_ADD`, `ATTACHMENT_DELETE`, `AUDIT_ARCHIVE`. Earlier: `REVIEWER_SIGNOFF`, `ADMIN_SIGNOFF`, `CHIEF_ENGINEER_APPROVE`, `CHIEF_ENGINEER_REJECT`, `DOMAIN_SIGNOFF`, `SANDBOX_CREATE`, `SANDBOX_DELETE`, `FULL_DATABASE_EXPORT`. Full catalogue: 12-audit-compliance.md §2.

## 10. OWASP Top 10 (2021) Control Mapping

A01 (Broken Access Control) now explicitly covering the five-role matrix and the three-decision-point segregation-of-duties model, and A04 (Insecure Design) explicitly covering the sandbox/real-record separation as a design-level control against accidental production pollution, not just a workflow nicety. v4 adds: A02 (Cryptographic Failures) — API tokens and webhook payloads use SHA-256 / HMAC-SHA-256, keys come from the environment and are never logged (§13); A07 (Identification and Authentication Failures) — step-up re-authentication, shared rate limiting; A08 (Software and Data Integrity Failures) — signed manifests, hash-chained audit log, verified backups; A09 (Logging and Monitoring Failures) — JSON request log file, readiness and metrics; A10 (SSRF) — webhook targets are restricted to private/loopback addresses and redirects are not followed (SEC-028).

## 11. Logging Standards

Structured JSON application logs (stderr, and since v4 optionally a rotating file `LOG_FILE`), never containing credentials, session tokens, API tokens, webhook secrets or step-up passwords, distinct from and complementary to the `audit_log_entry` compliance record of truth (12-audit-compliance.md §1).

## 12. No-Cloud Verification Checklist

Added in v2 as an explicit, standing check (to be re-run at every architecture review): no dependency on a public-cloud SaaS/PaaS/IaaS service anywhere in the stack; no cloud identity provider (§2); no cloud object storage for exports or backups (14-deployment-architecture.md §5); no CDN or external script/style source reachable only via the public internet in the UI (10-ui-ux-specification.md renders with local static assets only); no telemetry/analytics SDK phoning home to a third-party cloud endpoint. Any future proposal that would introduce one of these requires an explicit, separate decision — it is never a default.

**v4 re-check (2026-10-23):** nothing in the improvement pack contacts a public service. The only outbound connections are the optional SMTP relay named in `SMTP_HOST` (the organisation's own) and webhook POSTs to private/loopback addresses (SEC-028); with neither configured the application makes no outbound connection, and `test_whole_lifecycle_works_with_all_outbound_network_blocked` still passes. The offline lookup bundle and every page load nothing from the network.

## 13. v4 Security Controls (improvement pack)

- **SEC-026** *Step-up re-authentication (I-17, decision D-07).* Reviewer and Administrator sign-off, Chief Engineer decision, publishing a Release and the full-database export require the actor's own current password in the request. The check re-verifies the Argon2id hash, counts a failure toward the account lock-out of SEC-004, audits `STEP_UP_SUCCESS` / `STEP_UP_FAILURE`, never logs or stores the value, and answers 403 `step_up_required` / `step_up_failed`. One verification per request covers a whole change-set decision. `STEP_UP_REQUIRED=false` is a documented, deliberate deviation for test or lab systems only.
- **SEC-027** *Machine API tokens (I-29).* Random (`cscm_` + 256 bits), stored only as a SHA-256 hash, shown once, expiring (1–365 days), revocable, scoped (`catalogue:read`, `changes:read`). A token is honoured only as `Authorization: Bearer …` on `GET` operations that declare its scope, with **Viewer-level visibility** whoever owns the token, and stops working when revoked, expired or when its owner is deactivated. It can never write; it never bypasses the role matrix.
- **SEC-028** *Webhooks (I-29).* Targets must resolve to private, loopback or link-local addresses (`WEBHOOK_ALLOW_PUBLIC_TARGETS` is false and stays so), are re-validated at delivery, redirects are not followed, the timeout is 3 s, the body is signed `X-CSCM-Signature: sha256=<HMAC>` with a per-webhook secret shown once, and a failure is recorded and never affects the publish.
- **SEC-029** *Operational endpoints (I-21).* `/metrics` answers only clients inside `METRICS_ALLOWED_CIDRS` (loopback and RFC 1918 by default) or presenting `METRICS_TOKEN`, otherwise 403; it carries counts and timings, never business data. `/health` and `/health/ready` are unauthenticated and reveal only component states.
- **SEC-030** *Integrity keys and verification (I-06, I-18, I-09).* `MANIFEST_SIGNING_KEY` and `AUDIT_HMAC_KEY` are random values (≥ 32 characters) read from the environment or the protected configuration file (mode 640 / ACL), generated by the installer, kept in the organisation's password safe, and **not recoverable** — losing the audit key makes existing chain entries unverifiable. Backups are verified (integrity check, scratch restore, row counts, audit chain) and carry the same sensitivity as the database (§7).
- **SEC-031** *Program import (v4.2, FR-048o … FR-048w).* The `.st` upload accepts only `.st`, `.scl`, `.exp`, `.txt` and `.zip`; at most 2 MB per program file, 2,000 files and 50 MB unpacked per upload, at most 5,000 programs per file; ZIP members are used by base name only (no path ever reaches the file system) and nothing in a program is executed, compiled or served back. The preview keeps the upload under `instance/imports/staging/<token>` (a random 128-bit token) outside the web root; it belongs to the uploading user (403 for anybody else, including a replayed token), expires after 24 hours and is deleted on confirm or cancel; the confirmed source files are stored under `instance/imports/<job>/`. Upload and confirm are for Administrator and Engineer; the legacy mapping and a code's import source are for the four internal roles, never for Viewers, because they show titles and states of Drafts.
- **SEC-032** *Role administration (v4.3, FR-156, BR-024).* The user list (`GET /users`, `/admin/users`) is open to the Administrator and the StCd Owner; creating a user and the password reset are Administrator-only at the route and again in the service. `UserService.update_user` refuses an StCd Owner who changes anything but the role, and any role change that starts or ends outside Viewer, Engineer and Reviewer, with 403; the last active Administrator stays protected (FR-012). The StCd Owner's read access to the workflow is limited to the read-only routes `GET /change-requests`, `/change-requests/{id}`, its domain sign-offs, `/change-sets`, `/change-sets/{id}`, the Hub mapping and `/status-codes/{id}/where-used`; it can neither write nor decide anything. The migration that widens `user.ui_language` rebuilds the `user` table with foreign keys switched off and ends with a foreign-key check (migrations/env.py), so no table is left pointing at a discarded copy. Deleting a user (`POST /users/{id}/delete`) is Administrator-only, needs the Administrator's own password again (SEC-026), is refused for the own account and for the last active Administrator; an account with history is erased instead of removed (BR-025) and the audit log is not touched; the StCd Owner cannot deactivate or delete. Deleting a withdrawn code (S48, `POST /admin/withdrawn-codes/delete`) is Administrator-only, needs the password again and is refused for any code that has a revision.
- **SEC-033** *Windows sign-in and its simulation (v4.7, FR-163).* The gateway's identity header is a credential, so it is trusted only when `request.remote_addr` is in `WINDOWS_AUTH_TRUSTED_PROXIES` (empty by default: nobody); from any other address the header is ignored and the attempt is logged as a warning. The proxy must strip the header from incoming requests and set it itself from the authenticated Windows session (IIS/ARR: server variable; Apache: `RequestHeader set X-Remote-User %{REMOTE_USER}s`; nginx: `proxy_set_header X-Remote-User $remote_user`), and the application must not be reachable except through the proxy. The identity is matched by e-mail address, which cannot change (FR-162); no account is created on the fly, a deactivated account is refused, and the session that results is the ordinary one (SEC-002, SEC-003, same revocation on deactivation). `WINDOWS_AUTH_SIMULATE` lets a developer type an identity; it exists only in the development configuration and `create_app` refuses to start in production with it set, or with an unknown `AUTH_MODE`. In `windows` mode the password routes answer 403 so that a stolen password cannot bypass the gateway.

### 13.1 Threats and mitigations specific to v4

| Threat | Mitigation |
|---|---|
| An unattended browser approves or publishes | Step-up password per sensitive action (SEC-026) |
| A delegate becomes an escalation path | Decision actions only; SoD applies personally; audit names both (BR-017) |
| Audience export discloses a code to the wrong audience | Visibility is data; no confirmed value or `Covert` means hidden; Draft values never count (BR-016); a test checks that a hidden code is absent from every format |
| Someone edits the exported file after release | Manifest SHA-256, optional HMAC signature, offline verification (FR-103, FR-104) |
| Someone edits or removes audit rows with database access | Hash chain, anchor, weekly verification, append-only triggers (AUD-074) |
| Token leakage | Hash-only storage, short expiry, scopes, revocation, Viewer-level reach, read-only |
| Webhook or mail used to reach external systems | Private-address allow-list, no redirects; mail only through the organisation's relay |
| Malicious upload (attachment or import file) | Allow-list, magic-byte check, size and count limits, storage outside the web root, download-only, formula neutralisation (SEC-024) |
| Lost update overwrites engineering work | `row_version` check, 409 with the user's entries kept (FR-090) |
| Brute force across several worker processes | Rate limit in the database (NFR-009) |
| A bad backup is trusted | Every backup is restored into a scratch database and compared before it counts (FR-150) |

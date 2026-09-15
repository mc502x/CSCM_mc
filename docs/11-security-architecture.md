# 11. Security Architecture — CSCM Tool

## 1. Overview

CSCM Tool holds engineering-governed data with compliance/audit obligations (05-governance-handbook.md, 12-audit-compliance.md) and is deployed **exclusively on-premises, on a local server, with no public-cloud component of any kind** (00-INDEX.md "Deployment Principle", 14-deployment-architecture.md §1). Controls below are sized to that threat model while following OWASP baseline practice.

## 2. Authentication

- **SEC-001** Session-based authentication; credentials verified against `user.password_hash` using Argon2id (preferred) or bcrypt (cost ≥ 12). Plaintext/reversible storage is prohibited absolutely.
- **SEC-002** Session cookie attributes: `HttpOnly`, `Secure`, `SameSite=Strict`; identifier is a cryptographically random 128-bit+ value.
- **SEC-003** Idle session timeout 30 minutes; absolute session lifetime 12 hours.
- **SEC-004** Account lockout: 5 consecutive failed attempts locks the account for 15 minutes.
- **SEC-005** The authentication subsystem sits behind the `AuthProvider` interface (08-system-architecture.md §7) so a future SSO integration is additive. **The future SSO target is on-premises Active Directory (LDAP/Kerberos) or on-prem ADFS/SAML federation — not a cloud identity provider such as Azure AD.** This corrects the original stack assumption and is a hard requirement flowing from the no-cloud-infrastructure constraint; no OIDC/cloud-IdP code path may be introduced at any phase without an explicit, separate decision to relax that constraint.

## 3. Authorization — Role-Based Access Control

Five fixed roles: Administrator, Engineer, Reviewer, Chief Engineer, Viewer (00-INDEX.md "Roles"). Permission matrix (✓ = allowed; blank = denied; enforced identically at UI and API):

| Action | Administrator | Engineer | Reviewer | Chief Engineer | Viewer |
|---|---|---|---|---|---|
| View Approved/Released/Deprecated/Archived codes | ✓ | ✓ | ✓ | ✓ | ✓ |
| View Draft/Review/PendingApproval-state codes | ✓ | ✓ | ✓ | ✓ | — |
| Create Status Code / Change Request | ✓ | ✓ | — | — | — |
| Create Sandbox Status Code | ✓ | — | — | — | — |
| Delete Sandbox Status Code | ✓ | — | — | — | — |
| Edit own Draft revision | ✓ | ✓ | — | — | — |
| Provide Cross-Domain Sign-Off | — | ✓ (matching domain) | — | — | — |
| Submit CR for Review (allocates identifier) | ✓ | ✓ (own CR) | — | — | — |
| Reviewer sign-off (Review) | — | — | ✓ (not own CR) | — | — |
| Administrator sign-off (Review) | ✓ (not own CR) | — | — | — | — |
| Chief Engineer approval (PendingApproval) | — | — | — | ✓ (not requester/reviewer/admin on this CR) | — |
| Build/Publish Release | ✓ | — | — | — | — |
| Deprecate Released code | ✓ | ✓ (via full CR cycle) | — | — | — |
| Archive Deprecated code | ✓ | — | — | — | — |
| Manage Users/Roles/Engineering Domain tags | ✓ | — | — | — | — |
| Manage all Lookup Vocabularies (incl. Functional Group/Subgroup/Platform) | ✓ | — (propose only) | — | — | — |
| View Audit Log | ✓ | — | ✓ (scoped) | ✓ (scoped) | — |
| Export catalogue (CSV/JSON/PDF) | ✓ | ✓ | ✓ | ✓ | ✓ (Approved/Released only) |
| Export full database | ✓ | — | — | — | — |

- **SEC-010** Authorization checks live in the service layer, not only route decorators/UI conditionals.
- **SEC-011** Segregation-of-duties is a hard server-side check at all three decision points (§3 of 09-api-specification.md): Reviewer sign-off, Administrator sign-off, and Chief Engineer approval each independently reject if the actor matches the CR's author or, for the Chief Engineer step, either of the two prior sign-offs.
- **SEC-012** Principle of least privilege: default role on new user creation is Viewer.
- **SEC-013** Restricted-field enforcement: `access_rights_id` on a revision may be written by an Engineer only while the revision is in `DRAFT`; the value only becomes authoritative once stamped by the Administrator's sign-off action, which is the sole path by which `admin_signoff_at` becomes non-null (06-data-dictionary.md §2, "restricted field"). This is enforced in the service layer, not merely a UI convention.
- **SEC-014** `DELETE /status-codes/{id}` is authorized only when both `actor.role == ADMINISTRATOR` **and** `status_code.is_sandbox == true`; the second condition is additionally enforced by a database trigger (`trg_prevent_nonsandbox_delete`, 07-database-design.md §5) as defense in depth against a service-layer bug.
- **SEC-015** `GET /exports/full-database` is authorized only for `actor.role == ADMINISTRATOR`; no other role, including Chief Engineer, may reach it.

## 4. Password Policy

Unchanged from v1 (11-security-architecture.md v1 §4): 12-char minimum, no mandatory character-class rules, breach-corpus blocklist, no mandatory expiry, last-5 reuse block, Argon2id/bcrypt storage, TLS-only transmission.

## 5. Session Management

Unchanged in mechanism from v1: server-side session store, immediate revocation on logout/forced reset/deactivation, login rate limiting (10/IP/5min, 5/username/15min independently), CSRF synchronizer-token protection on all state-changing requests.

## 6. Input Validation

Unchanged in mechanism from v1 (SEC-020–SEC-024: server-side authoritative validation, parameterized queries only, Jinja2 auto-escaping never bypassed on user-supplied content, CSV formula-injection sanitization on export). The Cross-Domain Sign-Off text fields and comment fields (`review_comment.comment_text`) follow the same output-encoding rule as Title/Description.

## 7. Transport & Data Protection

Unchanged in mechanism from v1: TLS 1.2+ (internal network only — never internet-facing, per the no-cloud constraint), HSTS, standard security headers, OS-level ACL on the SQLite file. **Data-at-rest note specific to full-database exports (SEC-015):** the exported backup file carries the same sensitivity as the live database and must be stored with equivalent access control from the moment it is generated — the export feature itself does not weaken protection, but it does create a second copy of the Master Database that the Administrator is responsible for handling per this section (14-deployment-architecture.md §5).

## 8. Role-Based Access Control — Enforcement Points

Unchanged in structure from v1 (API route decorator → service-layer check → database constraint/trigger → UI conditional rendering), now covering five roles and the additional decision/sandbox/export checks in §3.

## 9. Audit Trail (Security-Relevant Events)

Unchanged in principle from v1 §9, plus: `REVIEWER_SIGNOFF`, `ADMIN_SIGNOFF`, `CHIEF_ENGINEER_APPROVE`, `CHIEF_ENGINEER_REJECT`, `DOMAIN_SIGNOFF`, `SANDBOX_CREATE`, `SANDBOX_DELETE`, `FULL_DATABASE_EXPORT`. Full catalogue: 12-audit-compliance.md §2.

## 10. OWASP Top 10 (2021) Control Mapping

Unchanged from v1 §10, with A01 (Broken Access Control) now explicitly covering the five-role matrix and the three-decision-point segregation-of-duties model, and A04 (Insecure Design) explicitly covering the sandbox/real-record separation as a design-level control against accidental production pollution, not just a workflow nicety.

## 11. Logging Standards

Unchanged from v1 §11: structured JSON application logs, never containing credentials or session tokens, distinct from and complementary to the `audit_log_entry` compliance record of truth (12-audit-compliance.md §1).

## 12. No-Cloud Verification Checklist

Added in v2 as an explicit, standing check (to be re-run at every architecture review): no dependency on a public-cloud SaaS/PaaS/IaaS service anywhere in the stack; no cloud identity provider (§2); no cloud object storage for exports or backups (14-deployment-architecture.md §5); no CDN or external script/style source reachable only via the public internet in the UI (10-ui-ux-specification.md renders with local static assets only); no telemetry/analytics SDK phoning home to a third-party cloud endpoint. Any future proposal that would introduce one of these requires an explicit, separate decision — it is never a default.

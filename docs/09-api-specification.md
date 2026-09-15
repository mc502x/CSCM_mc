# 09. API Specification — CSCM Tool

Full machine-readable contract: [artifacts/openapi.yaml](artifacts/openapi.yaml) (OpenAPI 3.0.3, v2.0.0). This document explains the conventions that apply across every endpoint.

## 1. Versioning

All endpoints are namespaced under `/api/v1`. The v2 documentation-package revision (this update) changes the *contract*, not the version prefix, since the application has not yet shipped — `/api/v1` remains correct for the first production release, which will already reflect this model. A genuinely breaking change post-launch requires `/api/v2`.

## 2. Authentication

MVP: session-cookie authentication (`cscm_session`, HttpOnly, Secure, SameSite=Strict), served entirely over the internal on-premises network. Future non-browser API consumers (documentation-generation tools, SCADA, software repositories — 08-system-architecture.md §6) will use a scoped, Administrator-issued API token (`Authorization: Bearer <token>`), still internal-network-only, never internet-exposed and never involving a cloud identity provider. Every endpoint requires authentication except `POST /auth/login`.

## 3. Authorization

Role-based across five roles (Administrator, Engineer, Reviewer, Chief Engineer, Viewer), enforced identically whether the request originates from the server-rendered UI or a direct API call. The canonical permission matrix is 11-security-architecture.md §3. Segregation-of-duties is enforced server-side on all three decision endpoints:
- `POST /change-requests/{id}/reviewer-signoff` — 403 if `actor.id == change_request.requested_by`.
- `POST /change-requests/{id}/admin-signoff` — 403 if `actor.id == change_request.requested_by`.
- `POST /change-requests/{id}/chief-engineer-decide` — 403 if `actor.id` matches the requester, the Reviewer sign-off, or the Administrator sign-off on this CR.

`DELETE /status-codes/{id}` (sandbox deletion) additionally requires `status_code.is_sandbox == true`; the same endpoint against a non-sandbox record returns 403 regardless of role.

`GET /exports/full-database` requires the Administrator role; no other role can reach it (04-domain-model.md §2.17).

## 4. Request/Response Conventions

Unchanged in shape from v1 (09-api-specification.md v1 §4): JSON bodies, ISO-8601 UTC timestamps, lookup-backed fields returned/accepted by `code` string (`functional_system_group: "WCNV"`, `turbine_platforms: ["2XM","3XM"]`, etc.) rather than internal surrogate IDs. `status_code_identifier` is `null` in every response until the revision reaches `REVIEW` or later.

## 5. Error Handling

| HTTP Status | Meaning | Body |
|---|---|---|
| 400 | Malformed request | `Error` |
| 401 | Not authenticated | `Error` |
| 403 | Not authorized (role, segregation-of-duties, sandbox-only-delete, domain-signoff-wrong-domain) | `Error` |
| 404 | Resource does not exist | `Error` |
| 409 | Conflict — duplicate identifier (should not occur given atomic allocation, but guarded), optimistic-concurrency mismatch, invalid state transition, open-CR-already-exists (BR-003), sandbox code added to a Release | `Error` |
| 422 | Semantically invalid input, OR required Cross-Domain Sign-Offs incomplete at Submit-for-Review | `ValidationErrorBody` |
| 429 | Rate limit exceeded (login attempts) | `Error` |
| 500 | Unexpected server error | `Error` |

## 6. Pagination, Filtering, Sorting

Unchanged in mechanism from v1 (`page`/`page_size` envelope, `sort` with `-` prefix). New filters on `GET /status-codes`: `functional_system_group`, `functional_subgroup`, `turbine_platform`, `is_sandbox` (defaults to `false`, so sandbox records never appear in default search results — matching their exclusion from catalogues). Full-text search (`q`) now covers `status_code_identifier` instead of the retired `code_number`.

## 7. Endpoint Summary

| Method | Path | Purpose | Min. Role |
|---|---|---|---|
| POST | `/auth/login` | Authenticate | — (public) |
| POST | `/auth/logout` | End session | Viewer |
| GET | `/auth/me` | Current user | Viewer |
| GET/POST | `/users` | List/create users | Administrator |
| GET/PATCH | `/users/{id}` | Get/update user, incl. Engineering Domain tags | Administrator |
| GET/POST | `/status-codes` | List/search; create new Draft or sandbox code | Viewer (GET), Engineer (POST), Administrator (POST with `is_sandbox: true`) |
| GET | `/status-codes/{id}` | Current revision | Viewer |
| DELETE | `/status-codes/{id}` | Permanently delete a sandbox code | Administrator (sandbox only) |
| GET/POST | `/status-codes/{id}/revisions` | Revision history; open new revision | Viewer (GET), Engineer (POST) |
| GET | `/status-codes/{id}/revisions/{a}/diff/{b}` | Field diff | Viewer |
| GET | `/status-codes/next-available` | Non-binding preview of the next identifier | Engineer, Administrator |
| PATCH | `/revisions/{id}` | Edit a Draft revision | Engineer (own CR) |
| GET | `/change-requests` | Review/approval queues / my submissions | Engineer/Reviewer/Administrator/Chief Engineer |
| GET | `/change-requests/{id}` | CR detail | Engineer/Reviewer/Administrator/Chief Engineer |
| POST | `/change-requests/{id}/submit` | Draft → Review; allocates identifier | Engineer (own CR) |
| POST | `/change-requests/{id}/reviewer-signoff` | 1 of 2 required Review sign-offs | Reviewer (not own CR) |
| POST | `/change-requests/{id}/admin-signoff` | 2 of 2 required Review sign-offs | Administrator (not own CR) |
| POST | `/change-requests/{id}/chief-engineer-decide` | PendingApproval → Approved/Draft | Chief Engineer (not requester/reviewer/admin on this CR) |
| POST | `/change-requests/{id}/withdraw` | Cancel own open CR | Engineer (own CR) |
| GET/POST | `/change-requests/{id}/domain-signoffs` | List/record Cross-Domain Sign-Offs | Engineer (matching domain) |
| GET/POST | `/releases` | List/create releases | Viewer (GET), Administrator (POST) |
| GET | `/releases/{id}` | Release detail | Viewer |
| GET | `/releases/{id}/candidates` | Approved, non-sandbox candidates | Administrator |
| PUT | `/releases/{id}/items` | Set included revisions | Administrator |
| POST | `/releases/{id}/publish` | Publish (atomic) | Administrator |
| GET | `/releases/{id}/export` | Export catalogue | Per role matrix |
| GET | `/exports/full-database` | Full raw database export/backup | **Administrator only** |
| GET | `/lookups/{vocabulary}` | Controlled vocabulary values, incl. Functional Groups/Subgroups/Platforms/Domains | Viewer |
| GET | `/audit-log` | Search audit trail | Administrator (Reviewer/Chief Engineer: scoped read) |

## 8. Idempotency & Concurrency

Unchanged in mechanism from v1 (optimistic concurrency on Draft edits, idempotent publish). Additional note: identifier allocation on `POST /change-requests/{id}/submit` is race-safe by construction (07-database-design.md §7a) — two concurrent submissions in the same Functional Group/Subgroup can never receive the same number; the loser of the race simply receives the next number after, not an error.

## 9. Rate Limiting

Unchanged from v1 (`POST /auth/login` rate-limited per IP and per username independently).

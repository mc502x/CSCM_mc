# 16. MVP Roadmap — CSCM Tool

## 1. Phasing Overview

| Phase | Theme | Outcome |
|---|---|---|
| Phase 1 (MVP) | Core governance: create, dual-review, Chief Engineer approval, release, audit, sandbox testing | Production-ready system of record replacing document-first status code authoring, fully on-premises |
| Phase 2 | Enterprise integration (on-premises only) | On-prem Active Directory/ADFS SSO, internal-network API tokens for external consumers, first live integration (documentation generation tool or SCADA), real Functional Subgroup taxonomy in place |
| Phase 3 | Scale & automation | PostgreSQL migration (if warranted), webhook-based push integrations (internal network only), configurable/multi-stage workflows if governance needs grow further |

## 2. Phase 1 — MVP

**Scope:** all FR/NFR/BR items in 03-srs.md, the full 7-state lifecycle with dual-review-then-Chief-Engineer-approval (05-governance-handbook.md), Functional System Group/Subgroup numbering with `StCd-XXXXX` identifiers, Turbine Platform multi-select, Cross-Domain Sign-Off, sandbox status codes, REST API (contract-complete, internal-consumer-only), UI, security controls, audit — all running entirely on-premises with no cloud component (14-deployment-architecture.md §1).

**Explicit exclusions:** on-prem AD/ADFS SSO itself (the hook is built, the integration is not — FR-005), live external integrations, bulk legacy import, configurable approval chains beyond the fixed Reviewer+Administrator+Chief-Engineer model, mobile-optimized layout, localization.

**Resolved since v2.0:** the real Functional Subgroup taxonomy has been supplied and is seeded directly (06-data-dictionary.md §9a) — no longer a placeholder. The `15000–15999` range is likewise resolved: confirmed as deliberate free capacity (alongside `10000–10999`, `14000–14999`, `16000–16999`), not an unclassified gap — no further action needed on it.

**Exit criteria:**
- All P1 test cases in 13-test-strategy.md §8 pass.
- At least one full UAT pass signed off (13-test-strategy.md §7, §10), including the dual-review, Chief Engineer approval, Cross-Domain Sign-Off, and sandbox-delete scenarios specifically.
- Security checklist executed with no unresolved High/Critical findings, including the no-cloud verification checklist (11-security-architecture.md §12).
- ~~The `15000–15999` range classified into (or added as) a Functional System Group~~ — resolved: confirmed free/reserved capacity, no classification needed.
- Technical Publications team has successfully produced one manual section sourced from a CSCM Tool export end-to-end.

## 3. Phase 2 — Enterprise Integration (On-Premises Only)

- On-premises Active Directory (LDAP/Kerberos) or ADFS/SAML authentication provider (behind the existing `AuthProvider` interface, 08-system-architecture.md §7; FR-005), including group-to-role mapping policy — explicitly **not** a cloud identity provider.
- Scoped API token issuance for machine consumers on the internal network only (09-api-specification.md §2).
- Multi-role support for users if operational need is confirmed.
- Revisit mobile/responsive scope if Viewer-role field usage on tablets/phones proves common.
- Confirm the final Functional Subgroup taxonomy has been in stable production use and re-validate numbering-capacity headroom per group.

**Trigger for starting Phase 2:** Phase 1 in stable production use for at least one full quarterly Release cycle with success metrics trending toward target.

## 4. Phase 3 — Scale & Automation

Unchanged in substance from v1 (16-mvp-roadmap.md v1 §4): evaluate PostgreSQL migration against observed volume/contention; webhook-based push notification on Release publish (internal network only — no cloud message broker); reassess whether the fixed Reviewer+Administrator+Chief-Engineer model remains sufficient only if governance complexity has genuinely grown.

## 5. Priority Matrix (Phase 1 Internal Sequencing)

| Capability | Business Value | Technical Risk/Complexity | Priority |
|---|---|---|---|
| Data model + 7-state lifecycle engine | Critical — everything depends on this | Medium-High (more states than v1) | P0 |
| Auth + 5-role RBAC | Critical | Low-Medium | P0 |
| Functional Group/Subgroup numbering + atomic identifier allocation | Critical — replaces the entire original numbering scheme | Medium-High (concurrency-sensitive) | P0 |
| Status Code create/edit (Draft) + validation | Critical | Medium | P0 |
| Cross-Domain Sign-Off gating | High — explicit business requirement, blocks Submit without it | Medium | P0 |
| Dual Review sign-off (Reviewer + Administrator) | Critical — the core governance value proposition | Medium | P0 |
| Chief Engineer approval | Critical — explicit new governance requirement | Low-Medium | P0 |
| Audit trail (incl. sandbox-delete snapshot) | Critical, compliance requirement | Low-Medium | P0 |
| Search/browse/filter | High | Low | P1 |
| Release management + publish (sandbox-exclusion enforced) | Critical | Medium-High | P0 |
| Catalogue export (CSV/JSON/XLSX/PDF) | High | Medium | P1 |
| Full-database export (Administrator only) | Medium — explicit new requirement, narrow scope | Low | P1 |
| Sandbox status codes (create/delete) | Medium — explicit new requirement | Low-Medium | P1 |
| Deprecation/Archival | Medium | Low | P1 |
| User/lookup administration (incl. Engineering Domain tags, Functional Group/Subgroup/Platform vocab) | High | Medium | P1 |
| REST API (beyond internal UI needs) | Medium for MVP, High for future value | Medium | P1 |
| Revision diff view | Medium | Low-Medium | P2 |

## 6. Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| *(retired 2026-09-17)* The `15000–15999` range remains unclassified | — | — | Resolved: confirmed free/reserved capacity alongside `10000–10999`, `14000–14999`, `16000–16999`; an Administrator can assign a new Functional System Group into any of them later via FR-048g without a schema change |
| Legacy status code data creates pressure to bulk-import, undermining governance-first principle | High | High | Unchanged from v1: one-time, human-reviewed re-entry through the real workflow, never a bulk import feature |
| Identifier-allocation contention under concurrent submission within one popular Functional Group | Low-Medium | Low (SQLite `BEGIN IMMEDIATE` serializes correctly; worst case is added latency, not incorrect numbers) | Performance-tested explicitly (TC-025); repository pattern keeps PostgreSQL migration available if contention proves material |
| Dual-review-plus-approval sequence slows throughput versus the original single-Reviewer model | Medium | Medium — undermines the "faster manual production" value proposition if turnaround degrades materially | Track sign-off and approval turnaround KPIs separately from week one; Administrator can still reassign Reviewer load |
| Cross-Domain Sign-Off requests stall in practice (second Engineer unavailable) | Medium | Medium | Dashboard/queue visibility (S8/S10a in 10-ui-ux-specification.md) makes outstanding requests hard to miss; revisit if turnaround data shows a bottleneck |
| Sandbox codes accidentally treated as production data by a downstream consumer | Low (system enforces exclusion structurally) | High if it occurred | `is_sandbox` excluded from default search, catalogue export, and Release candidates at the query/trigger level, not just UI convention (07-database-design.md §5) |
| No-cloud constraint conflicts with a convenient off-the-shelf cloud service later in the project | Medium | Medium | Standing verification checklist (11-security-architecture.md §12) reviewed at every architecture decision point, not just at go-live |
| Scope creep toward configurable workflows or SSO before Phase 1 ships | Medium | Medium | Explicit out-of-scope statement reinforced in sprint planning |

## 7. Effort Estimation (T-Shirt Sizing)

| Epic (see 17-implementation-backlog.md) | Size |
|---|---|
| EPIC-01 Foundation (scaffold, auth, 5-role RBAC, DB schema/migrations) | L |
| EPIC-02 Status Code Data Model, Numbering & Validation | L (up from M — Functional Group/Subgroup allocation adds complexity) |
| EPIC-03 Cross-Domain Sign-Off | M (new epic) |
| EPIC-04 Dual Review & Chief Engineer Approval Workflow | L (up from M — three decision points instead of one) |
| EPIC-05 Search, Browse, Filter, Revision History/Diff | M |
| EPIC-06 Release Management (build/publish/export, sandbox-exclusion) | L |
| EPIC-07 Sandbox Status Codes | S (new epic) |
| EPIC-08 Deprecation & Archival | S |
| EPIC-09 User & Lookup Administration (incl. new vocabularies) | M |
| EPIC-10 Audit Trail & Reporting | M |
| EPIC-11 REST API Hardening & OpenAPI Conformance | M |
| EPIC-12 Security Hardening, Compliance & No-Cloud Verification | M |
| EPIC-13 Non-functional: Performance, Deployment, Monitoring | M |
| EPIC-14 Library Import (new 2026-09-17) | M |
| EPIC-15 OneTool Shell Integration & UX Fixes (new 2026-09-17: no-data-loss-on-failure, inline field help, design system adoption) | M |
| EPIC-16 Subgroup & Group Administration (new 2026-09-17) | S |

Sizing scale unchanged: S ≈ 1 sprint, M ≈ 2 sprints, L ≈ 3–4 sprints, small (2–4 engineer) team; see 18-claude-code-implementation-guide.md §7 for sequencing.

## 8. Corrections Log (2026-09-17)

Grounded against a real 897-row export of the live status code library and the legacy tool's screenshot, this update corrects several assumptions made without real data: Functional Subgroup is mandatory, not optional; subgroup names and the WTUR nine-way split replace an earlier, incorrect hand-typed summary; `status_category`/`available_group`/`alarm`/delay fields/reset-and-brake programs all use different real types than originally assumed; the single Access Rights enum is replaced by eight independent audience fields; CSV/XLSX library import is now in scope (reversing the original "no bulk import" position) but still requires full governance per row; export formats gain XLSX; and the UI adopts the OneTool shared design system for its visual shell while keeping its own authentication. See 06-data-dictionary.md's provenance note and 19-glossary.md for the full corrected vocabulary.

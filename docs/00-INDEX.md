# Controller Status Code Management Tool (CSCM Tool)
## Software Delivery Documentation Package

**Document Set Version:** 2.0
**Date:** 2026-09-15
**Status:** Baseline for Development (v2 — functional-group numbering, dual-review/Chief Engineer approval, on-premises only)

This package is the complete, self-contained requirements and design basis for building the CSCM Tool without additional requirements gathering. It is intended to be read as a set; cross-references between documents use document numbers (e.g. "see 07-database-design.md"). Version 2.0 supersedes v1.0: Controller Type (Main/Hub) numbering has been replaced by Functional System Group numbering, the identifier format is now `StCd-XXXXX`, a Chief Engineer role and a dual-review-then-approve workflow have been introduced, Turbine Platform multi-select and platform-variant handling have been added, sandbox/test status codes are now supported, and every document has been checked for on-premises-only deployment (no cloud infrastructure).

**Open items still pending your input (see individual documents for TBD markers):** the real Functional Subgroup taxonomy per Functional System Group (currently placeholder), and the full attribute example status code you referenced but which did not reach this session — both are flagged inline wherever they affect a document.

## Document Set

| # | Document | File |
|---|----------|------|
| 01 | Executive Summary | [01-executive-summary.md](01-executive-summary.md) |
| 02 | Product Requirements Document (PRD) | [02-prd.md](02-prd.md) |
| 03 | Software Requirements Specification (SRS) | [03-srs.md](03-srs.md) |
| 04 | Domain Model Specification | [04-domain-model.md](04-domain-model.md) |
| 05 | Status Code Governance Handbook | [05-governance-handbook.md](05-governance-handbook.md) |
| 06 | Data Dictionary | [06-data-dictionary.md](06-data-dictionary.md) |
| 07 | Database Design Document | [07-database-design.md](07-database-design.md) |
| 08 | System Architecture Document | [08-system-architecture.md](08-system-architecture.md) |
| 09 | API Specification | [09-api-specification.md](09-api-specification.md) |
| 10 | UI/UX Specification | [10-ui-ux-specification.md](10-ui-ux-specification.md) |
| 11 | Security Architecture | [11-security-architecture.md](11-security-architecture.md) |
| 12 | Audit & Compliance Specification | [12-audit-compliance.md](12-audit-compliance.md) |
| 13 | Test Strategy | [13-test-strategy.md](13-test-strategy.md) |
| 14 | Deployment Architecture | [14-deployment-architecture.md](14-deployment-architecture.md) |
| 15 | Development Standards | [15-development-standards.md](15-development-standards.md) |
| 16 | MVP Roadmap | [16-mvp-roadmap.md](16-mvp-roadmap.md) |
| 17 | Implementation Backlog | [17-implementation-backlog.md](17-implementation-backlog.md) |
| 18 | Claude Code Implementation Guide | [18-claude-code-implementation-guide.md](18-claude-code-implementation-guide.md) |
| 19 | Glossary (living document — update with every change) | [19-glossary.md](19-glossary.md) |

## Supplementary Artifacts

| Artifact | File | Referenced By |
|----------|------|----------------|
| SQLite DDL | [artifacts/schema.sql](artifacts/schema.sql) | 07-database-design.md |
| OpenAPI 3.0 Specification | [artifacts/openapi.yaml](artifacts/openapi.yaml) | 09-api-specification.md |

## Naming & Terminology Baseline

Full definitions live in [19-glossary.md](19-glossary.md); this is the quick-reference subset used throughout the package.

- **Status Code** — the master governed record, identified by its Status Code Identifier.
- **Status Code Identifier (StCd)** — `StCd-XXXXX`, a five-digit zero-padded number equal to the code's position within its Functional System Group's numeric range, e.g. `StCd-01232`. Not assigned until Draft → Review.
- **Status Code Revision** — a specific versioned instance of a Status Code's attributes, carrying its own lifecycle state.
- **Functional System Group** — the classification and numbering axis (replaces the former Controller Type field). Nine groups; see 05-governance-handbook.md §2.
- **Functional Subgroup** — sub-division of a Functional System Group owning a numeric sub-band (placeholder taxonomy, TBD — see 06-data-dictionary.md §9a).
- **Turbine Platform** — multi-select classification (minimum `2XM`, `3XM`, `4XM`).
- **Change Request (CR)** — a proposal to create a new Status Code or revise an existing one, routed through the dual-review-then-approval workflow.
- **Release** — a named, dated, immutable bundle of Released status code revisions exported as a catalogue.
- **Lifecycle State** — one of `Draft`, `Review`, `PendingApproval`, `Approved`, `Released`, `Deprecated`, `Archived` (see 05-governance-handbook.md).
- **Sandbox Status Code** — Administrator-only test record, deletable, never part of a Release.

## Roles

| Role | Organizational Equivalent |
|---|---|
| Administrator | Product Owner Controls Software / Component Owner Controls Software |
| Engineer | Controls engineer or cross-functional engineer (tagged with an Engineering Domain) |
| Reviewer | Sub-PO for Status Codes |
| Chief Engineer | Final approval authority |
| Viewer | Read-only consumer |

## Functional System Group Numbering Table

| Range | Functional System Group | Prefix |
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

## Requirement Identifier Conventions

| Prefix | Meaning | Defined In |
|--------|---------|------------|
| `FR-###` | Functional Requirement | 03-srs.md |
| `NFR-###` | Non-Functional Requirement | 03-srs.md |
| `BR-###` | Business Rule | 03-srs.md, 05-governance-handbook.md |
| `SEC-###` | Security Control | 11-security-architecture.md |
| `AUD-###` | Audit/Compliance Requirement | 12-audit-compliance.md |
| `TC-###` | Test Case | 13-test-strategy.md |
| `EPIC-##` / `US-###` | Backlog Epic / User Story | 17-implementation-backlog.md |

## Deployment Principle

The system runs entirely on local, on-premises servers. No public cloud (SaaS/PaaS/IaaS) component of any kind is used anywhere in this design, including for future authentication (on-premises Active Directory / ADFS, not a cloud identity provider) — see 08-system-architecture.md §7 and 14-deployment-architecture.md §1.

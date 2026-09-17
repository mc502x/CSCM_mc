# Controller Status Code Management Tool (CSCM Tool)
## Software Delivery Documentation Package

**Document Set Version:** 3.0
**Date:** 2026-09-17
**Status:** Baseline for Development (v3 — real field model grounded in the live library export, Hub Controller groups, mandatory subgroups, library import, OneTool visual integration)

This package is the complete, self-contained requirements and design basis for building the CSCM Tool without additional requirements gathering. It is intended to be read as a set; cross-references between documents use document numbers (e.g. "see 07-database-design.md"). **Version history:** v1.0 → v2.0 replaced Controller Type (Main/Hub) numbering with Functional System Group numbering, introduced the `StCd-XXXXX` identifier format, the Chief Engineer role, the dual-review-then-approve workflow, Turbine Platform multi-select, sandbox/test status codes, and on-premises-only deployment. v2.0 → v3.0 (2026-09-17) grounded the entire attribute set in a real 897-row export of the live status code library (correcting Status Category, Available Group, Alarm, delay fields, and replacing the single Access Rights enum with eight independent audience fields), made Functional Subgroup mandatory, added three Hub Controller Functional System Groups (11000–13999) alongside the nine Main Controller ones, added CSV/XLSX library import (fully governed, not a bypass), added Administrator-created subgroups and whole new Functional System Groups, added XLSX to export formats, and adopted the OneTool shared design system for the UI shell while keeping CSCM Tool's own authentication.

**Open items still pending your input:** (1) the exact meaning of `Covert` across several audience-access vocabularies is unconfirmed (06-data-dictionary.md §9d); (2) the descriptive labels for Available Group codes and the eight numeric Program Reference fields are not available from the source export and need Controls Engineering input (06-data-dictionary.md §2c, §9c). The single-file `StCd_4960.st` example is superseded — the 2026-09-17 update grounds the entire data dictionary in a real 897-row export of the live library instead, which is more complete than one example file would have been. `10000–10999`, `14000–14999`, `15000–15999`, and `16000–16999` are confirmed free/reserved capacity for future Functional System Groups — no longer an open item.

**Field-model correction (2026-09-17):** the attribute set, Functional Subgroup names, and several field types in this package were corrected against a real export of the live status code library and a legacy-tool screenshot. Functional Subgroup is now mandatory (never optional); see 16-mvp-roadmap.md §8 "Corrections Log" and 06-data-dictionary.md's provenance note for the full list. CSV/XLSX library import is now in scope (reversing the earlier "no bulk import" position, still fully governed per row — 05-governance-handbook.md §6b), and the UI adopts the shared OneTool design system for its visual shell while keeping its own authentication (10-ui-ux-specification.md §0).

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
- **Functional Subgroup** — sub-division of a Functional System Group owning a numeric sub-band, **mandatory on every Status Code, never optional**; real taxonomy seeded, with deliberate reserved blocks for future additions and Administrator-created new subgroups (06-data-dictionary.md §9a).
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
| 1000–1999 | Converter & Grid Interface | WCNV |
| 2000–2999 | Generator System | WGEN |
| 3000–3999 | Meteorology & Nacelle Environment | WNAC |
| 4000–4999 | Rotor & Pitch System | WROT |
| 5000–5999 | Tower & Structure | WTOW |
| 6000–6999 | Transformer & MV System | WTRF |
| 7000–7999 | Drivetrain & Gearbox | WTRM |
| 8000–8999 | Yaw System | WYAW |
| 9000–9999 | Turbine Control & Operation | WTUR |
| 10000–10999 | *(free — reserved for a new Functional System Group)* | — |
| 11000–11999 | Hub Controller Control System | WTUR *(reused — different range from 9000–9999)* |
| 12000–12999 | Hub Controller Rotor & Pitch | WROT *(reused — different range from 4000–4999)* |
| 13000–13999 | Wind Farm / Plant Dispatch | WPPD |
| 14000–14999 | *(free — reserved for a new Functional System Group)* | — |
| 15000–15999 | *(free — reserved for a new Functional System Group)* | — |
| 16000–16999 | *(free — reserved for a new Functional System Group)* | — |

Each group subdivides into real Functional Subgroups owning numeric sub-bands, with deliberate reserved (unassigned) blocks for future growth — see 05-governance-handbook.md §2 and 06-data-dictionary.md §9a for the full subgroup list (38 subgroups across 12 groups as of 2026-09-17). `code` (the prefix) is unique together with `range_start`, not on its own — `WTUR` and `WROT` each identify two different groups, one Main Controller and one Hub Controller.

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

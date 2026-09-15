# 01. Executive Summary — CSCM Tool

## 1. Business Problem

Wind turbine Main Controller and Hub Controller software generate large, growing catalogues of status codes (faults, warnings, operational states, informational messages). Today these codes are typically authored inside engineering notes, spreadsheets, or directly inside technical manuals and specification documents. This creates five compounding problems: **(1) No single source of truth** — the same code number can exist with conflicting descriptions in different manuals, service bulletins, or SCADA configuration exports, because each document is edited independently. **(2) No governance** — status codes are added or changed by whoever edits the document next, with no mandatory review, approval, or sign-off before a code becomes authoritative. **(3) No traceability** — there is no reliable way to answer "who changed this code, when, why, and what did it say before," a requirement for engineering change control and for any future functional-safety or quality audit. **(4) No release discipline** — manuals are regenerated ad hoc; there is no concept of a versioned, approved status code catalogue that a given software build, manual edition, or SCADA integration can be pinned to. **(5) Duplication and drift** — because status codes are copy-pasted between documents rather than referenced from one place, duplicate or near-duplicate codes accumulate over time, and downstream documents silently drift out of sync with engineering intent.

## 2. Business Value

CSCM Tool inverts the current document-first workflow: status codes are created, cross-domain-completed, dual-reviewed, Chief-Engineer-approved, versioned, and released inside CSCM Tool first, and every downstream artifact (technical manuals, specifications, SCADA tag lists, future software repositories) is derived from CSCM Tool, not the other way around. It delivers authoritative data (one record per code, classified by Functional System Group, with one current approved state at any time), controlled change (every change to a status code goes through a seven-state lifecycle — Draft, Review, PendingApproval, Approved, Released, Deprecated, Archived — with named accountability at each of three distinct decision points: Reviewer, Administrator, and Chief Engineer), full history (every revision of every status code is retained and queryable), repeatable trustworthy exports (Approved/Released catalogues exported on demand, with full-database export reserved to the Administrator for disaster-recovery and migration purposes), and elimination of duplicate/conflicting codes through a numbering scheme tied directly to the turbine's functional subsystems rather than an arbitrary sequence.

## 3. Expected Outcomes

| Outcome | Description |
|---|---|
| Single system of record | All Main Controller and Hub Controller status codes exist in exactly one authoritative place, classified by Functional System Group instead of the former Controller Type split. |
| Governed lifecycle with real accountability | No status code reaches Released status without cross-domain-complete authorship, independent Reviewer and Administrator sign-off, and a separate Chief Engineer approval. |
| Full audit trail | Every create, edit, sign-off, approval, rejection, release, deprecation, and sandbox test event is logged immutably with actor and timestamp. |
| Faster manual production | Technical writers pull an approved, versioned export instead of manually re-collating status codes from multiple sources. |
| Safe test capability | Administrators can create and permanently delete sandbox status codes for testing and training without ever touching production numbering or manuals. |
| Foundation for automation | REST API and structured export formats enable future, strictly on-premises integration with documentation generation, software repositories, and SCADA systems, without re-architecting the data model. |
| Fully on-premises operation | No public cloud component anywhere in the system, including authentication — a hard deployment constraint, not a default. |

## 4. Success Metrics

| Metric | Target (post-MVP, first 2 quarters of production use) |
|---|---|
| % of status codes with unknown/undocumented owner | 0% |
| Duplicate identifiers created | 0 (enforced by uniqueness constraint and atomic allocation; see 07-database-design.md) |
| Median time from Change Request submission to Approved (through all three decision points) | ≤ 7 business days |
| % of Released status codes with complete audit trail from Draft, including both sign-offs and the Chief Engineer approval | 100% |
| Manual technical-writing rework caused by status code inconsistency | Reduced by ≥ 80% vs. baseline |
| Export catalogue adoption | 100% of new manual editions sourced from a CSCM Tool export within 2 releases of go-live |
| Cross-Domain Sign-Off turnaround (when required) | ≤ 3 business days |
| System availability (production) | ≥ 99.5% monthly, per NFR-002 (03-srs.md) |

## 5. Scope Boundary (Summary)

In scope for MVP: status code lifecycle management with Functional System Group/Subgroup-based numbering, Turbine Platform multi-select classification, Cross-Domain Sign-Off, the three-decision-point approval workflow, revision history, release management, sandbox test codes, catalogue export (role-scoped) and full-database export (Administrator-only), role-based access control across five roles, full audit logging, and an internal-network-only REST API — all running on local, on-premises infrastructure with no cloud component. Out of scope for MVP: on-premises Active Directory/ADFS SSO integration itself (the hook is built, not wired up), automated push integration to documentation generation tools/software repositories/SCADA systems, multi-tenant/multi-OEM support, and the final Functional Subgroup taxonomy (currently a structural placeholder pending Controls Engineering input). See 02-prd.md §6 for the complete scope statement.

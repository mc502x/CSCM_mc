# 19. Glossary — CSCM Tool

This glossary is a living document. Any change to terminology, roles, lifecycle states, or domain concepts elsewhere in this package must be reflected here in the same pull request (see 15-development-standards.md §6). Terms are alphabetical.

**Access Rights** — Classification field controlling who may act on a status code operationally (Service, Customer, OEM Only, Level 1–4). Proposed by the authoring Engineer but only authoritative once confirmed by the Administrator during their mandatory Review sign-off (see 06-data-dictionary.md §2, 11-security-architecture.md §3).

**Administrator** — System role. Organizationally equivalent to the Product Owner Controls Software / Component Owner Controls Software. Owns user administration, lookup/vocabulary governance, Release publishing, database export, sandbox status codes, and is one of the two mandatory Review sign-offs (05-governance-handbook.md §7).

**Approved** — Lifecycle state reached once a Chief Engineer has approved a status code revision that has already completed dual Review sign-off. Awaiting inclusion in a Release.

**Archived** — Terminal lifecycle state for long-retained, inactive status codes, reached from Deprecated after the minimum retention period.

**Audit Log Entry** — Immutable system record of every state-changing action (12-audit-compliance.md). Never edited or deleted, with one narrow exception: the deletion of a Sandbox Status Code, which is itself logged (the deletion event persists even though the underlying record does not).

**Chief Engineer** — System role. Performs the final Approval decision after both required Review sign-offs (Reviewer and Administrator) are complete. Cannot approve a change request they authored (segregation of duties).

**Code Number** — See Status Code Identifier (StCd).

**Cross-Domain Sign-Off** — The workflow step where a second Engineer, holding an Engineering Domain the originating Engineer does not, completes the fields tagged to that domain before a Change Request can be submitted for Review (05-governance-handbook.md §6a).

**Deprecated** — Lifecycle state for a previously Released status code that is no longer active but is retained for historical/service reference.

**Draft** — Initial, freely editable lifecycle state. A status code in Draft has no fixed Status Code Identifier — the identifier is allocated only when the Change Request is submitted for Review (05-governance-handbook.md §2).

**Engineer** — System role. A controls engineer or cross-functional engineer (e.g. electrical, mechanical) who authors and edits status codes. Tagged with one or more Engineering Domains.

**Engineering Domain** — Classification of an Engineer's specialty (e.g. Controls, Electrical, Mechanical, Grid, Safety). Used to route Cross-Domain Sign-Off requirements.

**Functional Subgroup** — A sub-division of a Functional System Group, owning a numeric sub-band within the group's range. Placeholder taxonomy pending confirmation by Controls Engineering (06-data-dictionary.md §9a).

**Functional System Group** — The primary classification and numbering axis for status codes, replacing the former Main/Hub Controller Type split. Nine groups, each with a fixed 1000-number range and a four-letter prefix (WCNV, WGEN, WNAC, WROT, WTOW, WTRF, WTRM, WYAW, WTUR) — see 05-governance-handbook.md §2.

**Master Database** — CSCM Tool's own on-premises server database. It is the single system of record; no external "master" system exists upstream of it. Data leaves only via Administrator-triggered export (08-system-architecture.md §6).

**PendingApproval** — Lifecycle state entered automatically once both required Review sign-offs (Reviewer and Administrator) are recorded. Awaiting Chief Engineer decision.

**Platform Variant Link** — An optional cross-reference between two independent Status Code records that represent the same underlying condition on different Turbine Platforms. Used when a code was renamed or regenerated between platforms rather than being modeled as a single multi-platform record (05-governance-handbook.md §2a).

**Product Owner** — Organizational title equivalent to the Administrator role in CSCM Tool.

**Release** — A named, versioned, immutable bundle of Approved status code revisions, published by the Administrator.

**Released** — Lifecycle state reached when a revision is included in a published Release; authoritative and citable.

**Reviewer** — System role. Organizationally the Sub-PO for Status Codes. One of the two mandatory Review sign-offs, alongside the Administrator.

**Review** — Lifecycle state entered on submission. Requires two independent sign-offs (Reviewer and Administrator) before automatically advancing to PendingApproval. Either sign-off may reject back to Draft with a mandatory comment.

**Sandbox Status Code** — A test-only status code created by an Administrator, drawn from an isolated `StCd-T#####` identifier band outside the real Functional System Group ranges. Never included in a Release, catalogue export, or manual. The only category of record that may be permanently deleted (05-governance-handbook.md §12).

**Segregation of Duties** — The rule that no single person may both author and decide on the same Change Request at any of the three decision points (Reviewer sign-off, Administrator sign-off, Chief Engineer approval).

**Status Code** — The governed identity record for a wind turbine controller status/fault/warning condition, identified by its Status Code Identifier (StCd).

**Status Code Identifier (StCd)** — The five-digit, zero-padded human identifier, e.g. `StCd-01232`. The numeric value is the code's position within its Functional System Group's range (e.g. 1000–1999 for Converter/Grid Interface), so the identifier itself encodes classification. Fixed only at the Draft → Review transition, never before.

**Status Code Revision** — A specific versioned set of attribute values for a Status Code, carrying its own lifecycle state.

**Turbine Platform** — A multi-select classification (minimum seed values `2XM`, `3XM`, `4XM`, extensible) indicating which turbine platform(s) a status code revision applies to. See Platform Variant Link for cross-platform divergence handling.

**Viewer** — System role. Read-only consumer of Approved/Released/Deprecated/Archived data.

**WCNV / WGEN / WNAC / WROT / WTOW / WTRF / WTRM / WYAW / WTUR** — Four-letter prefixes identifying each Functional System Group (Converter/Grid Interface, Generator, Meteorology/Environment/Nacelle Monitoring, Pitch System/Hub, Tower/Oscillation Monitoring, Transformer/MV Switchgear, Drive Train/Gearbox/Hydraulic/Rotor Brake, Yaw System, Turbine Control/Safety/Operational States/SCADA respectively). Displayed alongside the StCd identifier for cross-reference, not part of the identifier itself.

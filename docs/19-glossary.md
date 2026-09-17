# 19. Glossary — CSCM Tool

This glossary is a living document. Any change to terminology, roles, lifecycle states, or domain concepts elsewhere in this package must be reflected here in the same pull request (see 15-development-standards.md §6). Terms are alphabetical.

**Administrator** — System role. Organizationally equivalent to the Product Owner Controls Software / Component Owner Controls Software. Owns user administration, lookup/vocabulary governance (incl. creating new Functional Subgroups), Release publishing, database export, sandbox status codes, and is one of the two mandatory Review sign-offs (05-governance-handbook.md §7).

**Approved** — Lifecycle state reached once a Chief Engineer has approved a status code revision that has already completed dual Review sign-off. Awaiting inclusion in a Release.

**Archived** — Terminal lifecycle state for long-retained, inactive status codes, reached from Deprecated after the minimum retention period.

**Audience Access Fields** — Eight independent governed fields (Development, Sales, TCC, Service, Turbine Operator Package, Grid Operator, Service Partner, Customer), each with its own real vocabulary, controlling visibility per audience (corrected 2026-09-17 from a real library export; replaces the earlier single "Access Rights" enum). Proposed by the authoring Engineer but only authoritative once confirmed by the Administrator's Review sign-off (06-data-dictionary.md §2d, §9d).

**Audit Log Entry** — Immutable system record of every state-changing action (12-audit-compliance.md). Never edited or deleted, with one narrow exception: the deletion of a Sandbox Status Code, which is itself logged (the deletion event persists even though the underlying record does not).

**Available Group** — A numeric availability-accounting code (corrected 2026-09-17: real data uses a plain integer, not a lettered A–D group). Soft-validated against the currently-observed set; descriptive labels not yet available from source data (06-data-dictionary.md §9c).

**Chief Engineer** — System role. Performs the final Approval decision after both required Review sign-offs (Reviewer and Administrator) are complete. Cannot approve a change request they authored, or one they already signed off on as Reviewer or Administrator (segregation of duties).

**Code Number** — See Status Code Identifier (StCd).

**Cross-Domain Sign-Off** — The workflow step where a second Engineer, holding an Engineering Domain the originating Engineer does not, completes the fields tagged to that domain before a Change Request can be submitted for Review (05-governance-handbook.md §6a).

**Deprecated** — Lifecycle state for a previously Released status code that is no longer active but is retained for historical/service reference.

**Draft** — Initial, freely editable lifecycle state. A status code in Draft has no fixed Status Code Identifier — the identifier is allocated only when the Change Request is submitted for Review (05-governance-handbook.md §2).

**Engineer** — System role. A controls engineer or cross-functional engineer (e.g. electrical, mechanical) who authors and edits status codes. Tagged with one or more Engineering Domains.

**Engineering Domain** — Classification of an Engineer's specialty (e.g. Controls, Electrical, Mechanical, Grid, Safety). Used to route Cross-Domain Sign-Off requirements.

**Functional Subgroup** — A sub-division of a Functional System Group, **mandatory on every Status Code — never optional** (corrected 2026-09-17). Most subgroups own a 100-number sub-band aligned to the hundreds digit of the identifier (e.g. `010xx` = 01000–01099); within Turbine Control & Operation, several subgroups share the `099xx` block in finer ten-number sub-bands. The real taxonomy, corrected 2026-09-17 against an authoritative row-level export (the earlier hand-typed summary used incorrect subgroup names), is seeded in full (06-data-dictionary.md §9a). Unassigned blocks within a group are deliberate reserved capacity — an Administrator can create a new subgroup there at any time, provided it does not overlap an existing one.

**Functional System Group** — The primary classification and numbering axis for status codes. Twelve groups as of 2026-09-17: nine Main Controller groups (WCNV, WGEN, WNAC, WROT, WTOW, WTRF, WTRM, WYAW, WTUR, ranges 1000–9999) plus three Hub Controller groups added from a real export (WTUR 11000–11999, WROT 12000–12999, WPPD 13000–13999) — see 05-governance-handbook.md §2. The four-letter prefix is **not** a unique key on its own: `WTUR` and `WROT` are each intentionally reused across a Main Controller group and a Hub Controller group with a different numeric range — always resolve by range, not prefix alone. `10000–10999`, `14000–14999`, `15000–15999`, and `16000–16999` are confirmed free/reserved capacity for future groups, not currently assigned to anything.

**Import Job** — A record of a CSV or XLSX status code library upload (new 2026-09-17). Every row that passes validation becomes an ordinary Draft Change Request subject to the full governance cycle — import is a faster data-entry path, never a bypass (05-governance-handbook.md §6b). Row failures are reported per-row and create nothing.

**Legacy Reference Number** — Free-text field on a Status Code preserving a pre-migration/source-system number (e.g. the old "Status Code Number" seen in the legacy tool) carried through library import, for traceability only — never mistaken for the governed StCd identifier (06-data-dictionary.md §1, §12).

**Logical Node** / **Node Value** — Derived, read-only technical addressing fields on a Status Code Revision, always equal to the parent Functional System Group's prefix and sort order respectively. Exist in the real export as their own columns but carry no information CSCM Tool doesn't already have from the group assignment (06-data-dictionary.md §2e).

**Master Database** — CSCM Tool's own on-premises server database. It is the single system of record; no external "master" system exists upstream of it. Data leaves only via Administrator-triggered export (08-system-architecture.md §6).

**OneTool** — The shared internal tools platform CSCM Tool integrates with visually (shared top bar, sidebar, design tokens, and component treatments — 10-ui-ux-specification.md §0). CSCM Tool keeps its own login and credential store; only the visual shell is shared, not authentication (confirmed decision, 2026-09-17).

**PendingApproval** — Lifecycle state entered automatically once both required Review sign-offs (Reviewer and Administrator) are recorded. Awaiting Chief Engineer decision.

**Platform Variant Link** — An optional cross-reference between two independent Status Code records that represent the same underlying condition on different Turbine Platforms. Used when a code was renamed or regenerated between platforms rather than being modeled as a single multi-platform record (05-governance-handbook.md §2a).

**Product Owner** — Organizational title equivalent to the Administrator role in CSCM Tool.

**Program Reference Fields** — Eight numeric fields (Yaw Program, Manual Reset Program, Auto Reset Program, Converter Reactive Power Program, Brake Program, Umrichterprogramm GSC, Umrichterprogramm MSC, Yaw Bearing Lubrication Program) referencing controller-firmware subroutine numbers CSCM Tool does not itself govern — soft-validated against observed values, not hard-enforced lookups, since the descriptive meaning of each code is not available from source data (06-data-dictionary.md §2c).

**Release** — A named, versioned, immutable bundle of Approved status code revisions, published by the Administrator.

**Released** — Lifecycle state reached when a revision is included in a published Release; authoritative and citable.

**Reviewer** — System role. Organizationally the Sub-PO for Status Codes. One of the two mandatory Review sign-offs, alongside the Administrator.

**Review** — Lifecycle state entered on submission. Requires two independent sign-offs (Reviewer and Administrator) before automatically advancing to PendingApproval. Either sign-off may reject back to Draft with a mandatory comment.

**Sandbox Status Code** — A test-only status code created by an Administrator, drawn from an isolated `StCd-T#####` identifier band outside the real Functional System Group ranges. Never included in a Release, catalogue export, or manual. The only category of record that may be permanently deleted (05-governance-handbook.md §12).

**Segregation of Duties** — The rule that no single person may both author and decide on the same Change Request at any of the three decision points (Reviewer sign-off, Administrator sign-off, Chief Engineer approval).

**Status Code** — The governed identity record for a wind turbine controller status/fault/warning condition, identified by its Status Code Identifier (StCd).

**Status Code Identifier (StCd)** — The five-digit, zero-padded human identifier, e.g. `StCd-01232`. The numeric value is the code's position within its Functional System Group's range (e.g. 1000–1999 for Converter & Grid Interface), so the identifier itself encodes classification. Fixed only at the Draft → Review transition, never before.

**Status Code Revision** — A specific versioned set of attribute values for a Status Code, carrying its own lifecycle state. Field set corrected 2026-09-17 against a real 897-row library export — see 06-data-dictionary.md's provenance note for the full list of corrections (Status Category is Error/Warning/Info; Available Group is numeric; Alarm is boolean; Set/Reset Delay are free text with unit; Manual and Automatic Reset are separate fields; eight Audience Access fields replace the single Access Rights enum; eight numeric Program Reference fields; repeated-error escalation fields; Logical Node/Node Value derived fields).

**Turbine Platform** — A multi-select classification (minimum seed values `2XM`, `3XM`, `4XM`, extensible) indicating which turbine platform(s) a status code revision applies to. See Platform Variant Link for cross-platform divergence handling.

**Viewer** — System role. Read-only consumer of Approved/Released/Deprecated/Archived data.

**WCNV / WGEN / WNAC / WROT / WTOW / WTRF / WTRM / WYAW / WTUR / WPPD** — Four-letter prefixes identifying each Functional System Group (Converter & Grid Interface, Generator System, Meteorology & Nacelle Environment, Rotor & Pitch System, Tower & Structure, Transformer & MV System, Drivetrain & Gearbox, Yaw System, Turbine Control & Operation, and Wind Farm / Plant Dispatch respectively). `WROT` and `WTUR` each also identify a second, Hub Controller group with a different numeric range (12000–12999 and 11000–11999 respectively, added 2026-09-17) — see Functional System Group. Displayed alongside the StCd identifier for cross-reference, not part of the identifier itself.

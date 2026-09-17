# CSCM Tool — Controller Status Code Management Tool

Governed system of record for Senvion 4XM/3XM/2XM wind turbine Main Controller and Hub Controller status codes: creation, cross-domain completion, dual review (Reviewer + Product Owner), Chief Engineer approval, release management, and full audit trail. Status codes are created and governed **in this tool**, never imported from manuals — technical manuals and specifications are derived from it, not the other way around.

## Status

This repository currently holds the **v3.0 software delivery documentation package** (`docs/`) — the complete requirements, architecture, and design basis for the application, grounded in a real 897-row export of the live status code library and a 264-row Hub Controller export. Implementation has not started yet. See [docs/00-INDEX.md](docs/00-INDEX.md) for the full document set and version history, and [docs/18-claude-code-implementation-guide.md](docs/18-claude-code-implementation-guide.md) for the build plan.

## Quick Facts

- **Identifier format:** `StCd-XXXXX` (five digits), assigned only when a Change Request is submitted for Review — never while still in Draft.
- **Classification & numbering:** by Functional System Group and mandatory Functional Subgroup — 12 groups total: nine Main Controller groups (1000–9999) plus three Hub Controller groups (11000–13999, `WTUR`/`WROT` intentionally reused with different ranges, `WPPD` new) — see [docs/05-governance-handbook.md](docs/05-governance-handbook.md). `10000–10999`, `14000–14999`, `15000–15999`, and `16000–16999` are confirmed free capacity for future groups; an Administrator can assign a new group or subgroup into any free range without a schema change.
- **Roles:** Administrator (Product Owner / Component Owner Controls Software), Engineer, Reviewer (Sub-PO for Status Codes), Chief Engineer, Viewer.
- **Lifecycle:** Draft → Review (dual sign-off: Reviewer + Administrator) → PendingApproval → Approved (Chief Engineer) → Released → Deprecated → Archived.
- **Library import:** CSV/XLSX upload creates Draft Change Requests only — every imported row still passes the full governance cycle before Release.
- **UI:** shares the OneTool platform's visual shell (top bar, sidebar, design tokens); CSCM Tool keeps its own login and credential store.
- **Deployment:** fully on-premises. No public cloud component anywhere in the design.

## Repository Layout

```
docs/                 Software delivery documentation package (start at docs/00-INDEX.md)
  artifacts/           Executable SQL schema and OpenAPI contract
cscm_tool/             Application source (Flask backend, server-rendered UI) — not yet created
```

## Open Items Before Production Go-Live

- The exact meaning of `Covert` across several audience-access vocabularies (Sales, TCC, Service, etc.) is unconfirmed (`docs/06-data-dictionary.md` §9d).
- Descriptive labels for the 23 Available Group codes and the eight numeric Program Reference fields (Brake Program, Yaw Program, etc.) are not available from the source exports and need Controls Engineering input (`docs/06-data-dictionary.md` §2c, §9c).
- Whether `software_version` belongs on `StatusCodeRevision` or on `Release` is still open (`docs/06-data-dictionary.md` §2).

Resolved since the last README update: the Functional Subgroup taxonomy is real and seeded (27 Main + 11 Hub = 38 subgroups); `15000–15999` and its neighboring free ranges are confirmed reserved capacity, not a classification gap.

## Contributing

See [docs/15-development-standards.md](docs/15-development-standards.md) for coding standards, git workflow, and the Definition of Done. Any change to terminology, roles, or lifecycle states must update [docs/19-glossary.md](docs/19-glossary.md) in the same PR.

## License

Proprietary — internal Senvion Wind Technology use only. Not for external distribution.

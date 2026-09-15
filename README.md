# CSCM Tool — Controller Status Code Management Tool

Governed system of record for Senvion 4XM/3XM/2XM wind turbine Main Controller and Hub Controller status codes: creation, cross-domain completion, dual review (Reviewer + Product Owner), Chief Engineer approval, release management, and full audit trail. Status codes are created and governed **in this tool**, never imported from manuals — technical manuals and specifications are derived from it, not the other way around.

## Status

This repository currently holds the **v2.0 software delivery documentation package** (`docs/`) — the complete requirements, architecture, and design basis for the application. Implementation has not started yet. See [docs/00-INDEX.md](docs/00-INDEX.md) for the full document set and [docs/18-claude-code-implementation-guide.md](docs/18-claude-code-implementation-guide.md) for the build plan.

## Quick Facts

- **Identifier format:** `StCd-XXXXX` (five digits), assigned only when a Change Request is submitted for Review — never while still in Draft.
- **Classification & numbering:** by Functional System Group (Converter/Grid Interface, Generator, Meteorology/Nacelle, Pitch/Hub, Tower, Transformer/Switchgear, Drive Train, Yaw, Turbine Control/Safety/SCADA), each with a fixed numeric range — see [docs/05-governance-handbook.md](docs/05-governance-handbook.md).
- **Roles:** Administrator (Product Owner / Component Owner Controls Software), Engineer, Reviewer (Sub-PO for Status Codes), Chief Engineer, Viewer.
- **Lifecycle:** Draft → Review (dual sign-off) → PendingApproval → Approved (Chief Engineer) → Released → Deprecated → Archived.
- **Deployment:** fully on-premises. No public cloud component anywhere in the design.

## Repository Layout

```
docs/                 Software delivery documentation package (start at docs/00-INDEX.md)
  artifacts/           Executable SQL schema and OpenAPI contract
cscm_tool/             Application source (Flask backend, server-rendered UI) — not yet created
```

## Open Items Before Production Go-Live

- **Functional Subgroup taxonomy** is currently a structural placeholder pending the real list from Controls Engineering (`docs/06-data-dictionary.md` §9a).
- **A `15000–15999` status code range exists in the live 4XM codebase** (`Yogi/2XM/#15000-15999`) that is not yet represented in the documented Functional System Group table and needs classification.
- **A representative real status code example** (`StCd_4960.st`) is referenced but not yet reviewed against the data dictionary's attribute set.

## Contributing

See [docs/15-development-standards.md](docs/15-development-standards.md) for coding standards, git workflow, and the Definition of Done. Any change to terminology, roles, or lifecycle states must update [docs/19-glossary.md](docs/19-glossary.md) in the same PR.

## License

Proprietary — internal Senvion Wind Technology use only. Not for external distribution.

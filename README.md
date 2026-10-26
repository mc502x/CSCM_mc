# CSCM Tool — Controller Status Code Management Tool

Governed system of record for Senvion 4XM/3XM/2XM wind turbine Main Controller and Hub Controller status codes: creation, cross-domain completion, dual review (Reviewer + Product Owner), Chief Engineer approval, release management, and full audit trail. Status codes are created and governed **in this tool**, never imported from manuals — technical manuals and specifications are derived from it, not the other way around.

## Status

This repository holds the **v4.0 software delivery documentation package** (`docs/`) — requirements, architecture and design basis, grounded in a real 897-row export of the live status code library and a 264-row Hub Controller export — and the **implementation** (`cscm_tool/`). Version 4 (2026-10-23) implements all 36 improvement ideas of [docs/21-improvement-ideas.md](docs/21-improvement-ideas.md) on top of the Phase 1 baseline: concurrency control, an import toolkit, audience- and profile-scoped publication with signed manifests, software-version binding, SLAs, delegation and step-up re-authentication, a hash-chained audit log, verified backups, a German interface, scoped API tokens, installers and CI. [docs/20-traceability-matrix.md](docs/20-traceability-matrix.md) maps each requirement to code and tests; the generated [docs/24-test-report.md](docs/24-test-report.md) is the authoritative record of what was run and what it returned. What is *not* done is listed in [docs/20-traceability-matrix.md](docs/20-traceability-matrix.md) §6 and in the new improvement list of docs/21.

## Quick Facts

- **Identifier format:** `StCd-XXXXX` (five digits), assigned only when a Change Request is submitted for Review — never while still in Draft.
- **Classification & numbering:** by Functional System Group and mandatory Functional Subgroup — 12 groups total: nine Main Controller groups (1000–9999) plus three Hub Controller groups (11000–13999, `WTUR`/`WROT` intentionally reused with different ranges, `WPPD` new) — see [docs/05-governance-handbook.md](docs/05-governance-handbook.md). `10000–10999`, `14000–14999`, `15000–15999`, and `16000–16999` are confirmed free capacity for future groups; an Administrator can assign a new group or subgroup into any free range without a schema change.
- **Roles:** Administrator (Product Owner / Component Owner Controls Software), Engineer, Reviewer (Sub-PO for Status Codes), Chief Engineer, Viewer.
- **Lifecycle:** Draft → Review (dual sign-off: Reviewer + Administrator) → PendingApproval → Approved (Chief Engineer) → Released → Deprecated → Archived.
- **Library import:** CSV/XLSX upload creates Draft Change Requests only — every imported row still passes the full governance cycle before Release. Since v4 with a template, a dry run, an update mode and a reconciliation report.
- **Status code import from the generated programs (v4.2):** `StCd_<n>.st` files (several at once, a folder or a ZIP) are previewed per program, ticked and imported as ordinary Drafts that reserve the number the program carries and join one change set; the legacy → new mapping (Main and Hub, one direction only) is listed and exported. See `docs/03-srs.md` §1.16.
- **Decisions need your password** (v4): Reviewer and Administrator sign-off, Chief Engineer approval, publishing and the full backup are re-authenticated; a delegate acts as themselves, for decisions only.
- **Publishing** (v4): export profiles, audience / language / software-version scoping, manifests with SHA-256 hashes (optionally signed), release notes, an offline lookup page.
- **Operations** (v4): verified nightly backups, tamper-evident audit log, `/health/ready` and `/metrics`, installers for Windows Server and Linux, CI definitions.
- **UI:** shares the OneTool platform's visual shell (top bar, sidebar, design tokens); CSCM Tool keeps its own login and credential store.
- **Deployment:** fully on-premises. No public cloud component anywhere in the design.

## Repository Layout

```
docs/                 Software delivery documentation package (start at docs/00-INDEX.md)
  artifacts/           Executable SQL schema (+ optional FTS5 schema), OpenAPI contract, test run history
cscm_tool/             Application source (Flask backend, server-rendered UI), test suite,
                       scripts/ (report generator, CI runner, production entry point, PostgreSQL ratchet)
                       and deploy/ (Linux and Windows installers, systemd units)
.gitea/workflows/      CI definition for the internal Gitea server (also .gitlab-ci.yml)
```

## Open Items Before Production Go-Live

- The exact meaning of `Covert` across several audience-access vocabularies (Sales, TCC, Service, etc.) is unconfirmed (`docs/06-data-dictionary.md` §9d).
- Descriptive labels for the 23 Available Group codes and the eight numeric Program Reference fields (Brake Program, Yaw Program, etc.) are not available from the source exports and need Controls Engineering input (`docs/06-data-dictionary.md` §2c, §9c).
- Business confirmations that v4 answered with a safe default (03-srs.md §6): `Covert` treated as not visible (D-02), English + German content (D-03), in-app notices with optional mail (D-04), HMAC-signed manifests (D-05). Please confirm or change them.
- Deployment checks that only the target environment can prove: a real installation, TLS, egress block, the restore drill, key custody, a screen-reader pass (docs/20 §6).
- The application has never been run on PostgreSQL; only an inventory and a ratchet exist (docs/07 §12).

Resolved: `software_version` is now a range per revision plus the versions a Release targets (D-01); the Functional Subgroup taxonomy is real and seeded (27 Main + 11 Hub = 38 subgroups); `15000–15999` and its neighboring free ranges are confirmed reserved capacity, not a classification gap.

## Contributing

See [docs/15-development-standards.md](docs/15-development-standards.md) for coding standards, git workflow, and the Definition of Done. Any change to terminology, roles, or lifecycle states must update [docs/19-glossary.md](docs/19-glossary.md) in the same PR.

## License

Proprietary — internal Senvion Wind Technology use only. Not for external distribution.

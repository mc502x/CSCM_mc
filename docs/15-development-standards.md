# 15. Development Standards — CSCM Tool

## 1. Folder Structure

See 18-claude-code-implementation-guide.md §2 for the complete, authoritative folder layout used during implementation (package root `cscm_tool/`). Summary of top-level conventions:

```
cscm_tool/
├── app/
│   ├── __init__.py            # application factory (create_app(config_name, overrides)), engine hooks
│   ├── api/v1/                # REST blueprints (one module per area; _errors.py maps service errors)
│   ├── ui/                    # server-rendered UI blueprints
│   ├── models/                # SQLAlchemy ORM models (operations.py holds the v4 tables)
│   ├── repositories/          # repository pattern (status_code_repository, fts)
│   ├── services/              # business logic, workflow, validation, publication, operations
│   ├── auth/                  # providers, RBAC decorators (declare `view.access`), rate limit
│   ├── export/                # CSV/JSON/XLSX/PDF/offline-bundle + full-database export
│   ├── audit/ audit_chain.py audit_hash.py   # audit writer; hash chain, verification, archive
│   ├── observability.py logging_config.py    # metrics registry, JSON request log
│   ├── i18n.py i18n_de.py help_content.py    # English/German catalogue and help text
│   ├── cli.py                 # `flask` jobs: backup-db, verify-backup, audit-verify, send-reminders, …
│   ├── templates/             # Jinja2 templates
│   └── static/                # CSS/JS (no external/CDN sources — 11-security-architecture.md §12)
├── migrations/                # Alembic revision chain (07-database-design.md §11)
├── scripts/                   # generate_test_report.py, ci.py, serve.py, pg_readiness.py, gen_api_summary.py, gen_translations_doc.py
├── deploy/linux/ deploy/windows/   # installers, systemd units, scheduled-task scripts, nginx sample
├── tests/
│   ├── unit/ integration/ system/ performance/ fixtures/
│   └── conftest.py helpers.py
└── pyproject.toml requirements.txt .env.example
docs/                          # this documentation package (repository root, next to cscm_tool/)
.gitea/workflows/ci.yml  .gitlab-ci.yml  .gitattributes   # at the repository root
```

## 1a. OneTool Design System Compliance (new 2026-09-17)

All UI code (templates, CSS, JS) must use the shared OneTool design tokens, typography (Manrope/Inter), and component treatments (10-ui-ux-specification.md §0) rather than introducing new colors, fonts, or button/card styles. Before any UI PR is merged: render inside the shared shell with the CSCM Tool nav item active, and verify desktop, collapsed-sidebar, tablet, keyboard-only, loading, error, and empty states, per the design system's own integration checklist. Authentication (`app/auth/`) is explicitly out of scope for this integration — it stays CSCM Tool's own.

## 2. Coding Standards

PEP 8 via `black`/`ruff` (line length 100; long SQL strings and banners in `tests/` are exempt from E501), type hints required on service/repository signatures (`mypy`), no business logic in route handlers, no raw SQL string concatenation, configuration values as named constants, vanilla JS with no framework and no CDN-hosted dependency (11-security-architecture.md §12 — every static asset is vendored locally, never fetched from an external host at runtime or build time).

## 3. Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Python modules/files | `snake_case` | `change_request_service.py` |
| Python classes | `PascalCase` | `ChangeRequestService` |
| Python functions/variables | `snake_case` | `reviewer_signoff()` |
| SQLAlchemy model classes | Singular `PascalCase` | `StatusCodeRevision` |
| Database tables/columns | `snake_case`, singular | `status_code_revision` |
| API URL paths | plural, kebab/lowercase | `/api/v1/change-requests` |
| API JSON fields | `snake_case` | `status_code_identifier` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_PAGE_SIZE` |
| Git branches | `type/short-description` | `feature/dual-review-workflow` |
| Requirement IDs in code comments/commits | as defined in 00-INDEX.md | `FR-033`, `BR-005` |

## 4. API Standards

Contract-first against `artifacts/openapi.yaml`: every new endpoint ships with schema entries, a system test, and a role declaration on the route (`require_role…` / `login_required` set `view.access`; `allow_token(scope)` for token-readable GETs) — the route inventory test then checks it for all five roles, and `python scripts/gen_api_summary.py --write` regenerates the endpoint table of 09-api-specification.md. Breaking changes require a version bump.

## 5. Database Standards

All schema changes via reversible, guarded and idempotent Alembic migrations (07-database-design.md §11; a frozen copy of the previous schema in `tests/fixtures/` proves the upgrade), no ad hoc schema edits, new tables/columns reflected in the same PR across 06-data-dictionary.md, 07-database-design.md, and `artifacts/schema.sql`, every foreign key indexed unless proven unnecessary.

## 6. Documentation Standards

- This `docs/` package is the living source of truth; a PR that changes behavior described by a specific FR/NFR/BR/SEC/AUD identifier must update that document in the same PR.
- **Glossary discipline (new in v2):** any PR that introduces, renames, or retires a term, role, lifecycle state, or domain concept must update [19-glossary.md](19-glossary.md) in the same PR — the glossary is treated as a required artifact, not optional polish, per the explicit instruction that it "be kept updated with every change."
- **Paragraph formatting:** prose paragraphs in every document under `docs/` are written as a single continuous source line (no manual mid-paragraph line breaks); only tables, code blocks, and list items may span multiple source lines. This applies to new and edited content alike — an edit that reintroduces hard-wrapped paragraphs should be corrected before merge.
- Code comments explain **why**, not **what**; no commented-out code is committed.
- Every service-layer public method has a docstring stating its pre/postconditions and which FR/BR it implements, e.g. `"""Records the Administrator sign-off. Enforces BR-005 and may confirm a restricted field. See FR-034."""`.

## 7. Testing Standards

Tests required in the same PR as new logic/endpoints, deterministic (no wall-clock or ordering dependence), a fresh in-memory SQLite database and a fresh instance directory per test (a SQLite file with `CSCM_TEST_DB=file`). A test module's docstring cites the TC and requirement ids it covers (`TC-0nn. Requirements: FR-…`) so the report can account for every requirement (13-test-strategy.md §12). The suite is verified three ways before a release (13-test-strategy.md §11).

## 8. Dependency Management

Pinned requirements (`requirements.txt`: runtime first, tooling after the `# --- dev` marker, which the installers cut at), `pip-audit` in CI blocking on new High/Critical findings, zero external JS dependencies by default, any exception vendored/pinned and never loaded from an external CDN at runtime — consistent with the no-cloud, on-premises-only constraint (11-security-architecture.md §12), which is a stricter reason for this rule than offline-deployment convenience alone.

## 9. Git Workflow

Trunk-based, short-lived feature branches, CI gate (lint/format/type/tests/`bandit`/`pip-audit`) required green before merge, no direct pushes to `main`.

## 10. Pull Request Process

Standard checklist, with the glossary-update requirement (§6) added to the standard PR checklist alongside the existing documentation-update requirement.

## 11. Definition of Done

Approved PR merged, acceptance criteria demonstrated, tests passing at coverage target, relevant documentation **and glossary** updated to match actual behavior, no known High/Critical security findings, deployed and smoke-tested in Staging at least once before counting toward a release milestone.

**Living artefacts (added 2026-10-21).** Any change to the software also updates, in the same PR: the test report — regenerate it with `python cscm_tool/scripts/generate_test_report.py` (runs the full suite, coverage and the static gates, and appends to the run history; never edit `24-test-report.md` by hand); the traceability matrix `20-traceability-matrix.md` when a requirement's code or evidence moves (the report flags matrix citations that no longer resolve to a test); and, when behaviour visible to users or integrators changes, the software description `22-software-description.md`, the user manual `23-user-manual.md` and `artifacts/openapi.yaml`. Generated blocks (the endpoint table of 09-api-specification.md, the test report) are regenerated, never edited by hand, and `tests/system/test_docs_consistency.py` must be green. A PR whose report verdict is not PASS is not done.

## 12. v4 Conventions

- **Quality gates** (all must be clean before merge; `scripts/ci.py` runs them): `black --check app tests migrations/versions`, `ruff check app tests migrations/versions`, `mypy app wsgi.py`, `bandit -q -r app`, `pip-audit -r requirements.txt` (advisories in development-only tools are accepted and listed in the report; a runtime advisory fails the gate).
- **No `assert` for control flow in `app/`** (bandit B101) — raise a domain error; no silent `except: pass`.
- **SQL built from names** is allowed only from constants and carries `# nosec B608` with the reason; user input only ever reaches the database through bound parameters (SEC-021).
- **Secrets** (keys, tokens, passwords, webhook secrets) come from the environment or the protected configuration file, are never logged, never stored in clear (tokens are hashed), and are shown once when generated (SEC-030).
- **New SQLite-specific code** (a trigger, `BEGIN IMMEDIATE`, `GLOB`, a `sqlite3` call, FTS) must be justified: `python scripts/pg_readiness.py --check` fails when the count grows, and the baseline is lowered with `--update-baseline` when it shrinks (NFR-014).
- **User-visible strings in templates** are wrapped in `_()` and get a German entry in `app/i18n_de.py`; new help text lives in `app/help_content.py` and new terms in 19-glossary.md (`test_i18n`, `test_search_and_help`).
- **Accessibility**: every new control has a label or accessible name, tables use `<th scope="col">`, colours come from the tokens (`test_accessibility`).
- **Releases**: raise `VERSION` in `app/version.py` and `version` in `pyproject.toml` (`test_version` keeps them equal), then run `python scripts/ci.py --pdf` (the pipeline, then the four PDFs of the release) and tag the commit `v<VERSION>`. The version is shown in the menu, on the login page and in `/api/v1/health`; the PDFs are `dist/docs/v<VERSION>/CSCM-Tool_v<VERSION>_{Full-Documentation,Software-Description,User-Manual,Test-Report}.pdf` (not committed; attach them to the release).
- **Line endings**: Linux-executed files (`*.sh`, `deploy/linux/*`) keep LF whatever `core.autocrlf` says (`.gitattributes`).
- **Documents**: numbers quoted in prose (operations, tables, triggers, action codes) are checked against the code by `test_docs_consistency`; regenerate generated blocks (endpoint table, test report) instead of editing them.

# 15. Development Standards — CSCM Tool

## 1. Folder Structure

See 18-claude-code-implementation-guide.md §2 for the complete, authoritative folder layout used during implementation (package root `cscm_tool/`). Summary of top-level conventions:

```
cscm_tool/
├── app/
│   ├── __init__.py            # application factory
│   ├── api/                   # REST API blueprints (v1)
│   ├── ui/                    # server-rendered UI blueprints
│   ├── models/                # SQLAlchemy ORM models
│   ├── repositories/          # repository pattern implementations
│   ├── services/               # business logic / workflow / validation
│   ├── auth/                  # auth providers (on-prem only), RBAC decorators
│   ├── export/                # CSV/JSON/XLSX/PDF + full-database export
│   ├── audit/                 # audit log writer
│   ├── templates/             # Jinja2 templates
│   └── static/                # CSS/JS (no external/CDN sources — 11-security-architecture.md §12)
├── migrations/                # Alembic migration scripts
├── tests/
│   ├── unit/
│   ├── integration/
│   └── system/
├── docs/                      # this documentation package
└── config.py
```

## 1a. OneTool Design System Compliance (new 2026-09-17)

All UI code (templates, CSS, JS) must use the shared OneTool design tokens, typography (Manrope/Inter), and component treatments (10-ui-ux-specification.md §0) rather than introducing new colors, fonts, or button/card styles. Before any UI PR is merged: render inside the shared shell with the CSCM Tool nav item active, and verify desktop, collapsed-sidebar, tablet, keyboard-only, loading, error, and empty states, per the design system's own integration checklist. Authentication (`app/auth/`) is explicitly out of scope for this integration — it stays CSCM Tool's own.

## 2. Coding Standards

Unchanged in mechanism from v1 (15-development-standards.md v1 §2): PEP 8 via `black`/`ruff`, type hints required on service/repository signatures (`mypy`), no business logic in route handlers, no raw SQL string concatenation, configuration values as named constants, vanilla JS with no framework and no CDN-hosted dependency (11-security-architecture.md §12 — every static asset is vendored locally, never fetched from an external host at runtime or build time).

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

Unchanged in mechanism from v1: contract-first against `artifacts/openapi.yaml`, every new endpoint ships with schema entries, a system test, and an authorization-matrix test entry; breaking changes require a version bump.

## 5. Database Standards

Unchanged in mechanism from v1 (§5): all schema changes via reversible Alembic migrations, no ad hoc schema edits, new tables/columns reflected in the same PR across 06-data-dictionary.md, 07-database-design.md, and `artifacts/schema.sql`, every foreign key indexed unless proven unnecessary.

## 6. Documentation Standards

- This `docs/` package is the living source of truth; a PR that changes behavior described by a specific FR/NFR/BR/SEC/AUD identifier must update that document in the same PR.
- **Glossary discipline (new in v2):** any PR that introduces, renames, or retires a term, role, lifecycle state, or domain concept must update [19-glossary.md](19-glossary.md) in the same PR — the glossary is treated as a required artifact, not optional polish, per the explicit instruction that it "be kept updated with every change."
- **Paragraph formatting:** prose paragraphs in every document under `docs/` are written as a single continuous source line (no manual mid-paragraph line breaks); only tables, code blocks, and list items may span multiple source lines. This applies to new and edited content alike — an edit that reintroduces hard-wrapped paragraphs should be corrected before merge.
- Code comments explain **why**, not **what**; no commented-out code is committed.
- Every service-layer public method has a docstring stating its pre/postconditions and which FR/BR it implements, e.g. `"""Records the Administrator sign-off. Enforces BR-005 and may confirm a restricted field. See FR-034."""`.

## 7. Testing Standards

Unchanged in mechanism from v1 (§7): tests required in the same PR as new logic/endpoints, deterministic (no wall-clock or ordering dependence), fresh temp-file/in-memory SQLite per test.

## 8. Dependency Management

Unchanged in mechanism from v1 (§8): pinned lockfile, `pip-audit` in CI blocking on new High/Critical findings, zero external JS dependencies by default, any exception vendored/pinned and never loaded from an external CDN at runtime — consistent with the no-cloud, on-premises-only constraint (11-security-architecture.md §12), which is a stricter reason for this rule than offline-deployment convenience alone.

## 9. Git Workflow

Unchanged in mechanism from v1 (§9): trunk-based, short-lived feature branches, CI gate (lint/format/type/tests/`bandit`/`pip-audit`) required green before merge, no direct pushes to `main`.

## 10. Pull Request Process

Unchanged in mechanism from v1 (§10), with the glossary-update requirement (§6) added to the standard PR checklist alongside the existing documentation-update requirement.

## 11. Definition of Done

Unchanged in structure from v1 (§11): approved PR merged, acceptance criteria demonstrated, tests passing at coverage target, relevant documentation **and glossary** updated to match actual behavior, no known High/Critical security findings, deployed and smoke-tested in Staging at least once before counting toward a release milestone.

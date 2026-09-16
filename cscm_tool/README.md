# CSCM Tool — Application

Flask backend for the Controller Status Code Management Tool. See the root [../README.md](../README.md) and the [../docs/](../docs/00-INDEX.md) package for the full requirements/design basis this code implements.

## Status

EPIC-01–04, EPIC-06, and EPIC-08 complete (`docs/17-implementation-backlog.md`): application factory, health endpoint, the full v2 SQLAlchemy model set, the baseline Alembic migration applying `docs/artifacts/schema.sql`, session-based authentication with account lockout and rate limiting (FR-001–FR-004), CSRF protection, RBAC/user administration (FR-010–FR-014), Status Code creation with field/cross-field validation (FR-020–FR-029), atomic Functional Group/Subgroup identifier allocation (FR-021, `docs/07-database-design.md` §7a), sandbox codes (FR-053–FR-056), Cross-Domain Sign-Off (FR-027–FR-029), the full submit → dual-review → Chief-Engineer-approval workflow with segregation-of-duties enforcement (FR-030–FR-039, BR-004/BR-005), Release Management (build/candidates/items/publish, CSV/JSON/PDF catalogue export, Administrator-only full-database backup — FR-040–FR-048, SEC-015), and Deprecation/Archival: Engineer- or Administrator-initiated deprecation via the same dual-review + Chief-Engineer-approval cycle, plus direct Administrator archive (retention-period-gated, BR-006) and reinstate (FR-050–FR-052). Not yet built: the audit-log read/search API (EPIC-10) and the server-rendered UI — see `docs/18-claude-code-implementation-guide.md` §8 for the coding order.

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate   # .venv/bin/activate on Linux/macOS
pip install -r requirements.txt
cp .env.example .env     # then edit SECRET_KEY for anything beyond local dev
```

## Running

```bash
flask db upgrade      # creates instance/cscm.db from the baseline migration + seed data
flask create-admin    # bootstraps the first Administrator account (prompts, or pass --username/--email/--full-name/--password)
flask run
```

`GET /api/v1/health` should return `{"status": "ok"}`. Log in with `POST /api/v1/auth/login`; every other state-changing request needs an `X-CSRFToken` header fetched from `GET /api/v1/auth/csrf-token` first (see `app/api/v1/auth_routes.py`).

## Testing

```bash
pytest
```

Every test gets a fresh in-memory SQLite database migrated through the same Alembic revision used everywhere else (`tests/conftest.py`), per `docs/15-development-standards.md` §7.

## Code quality gates (docs/15-development-standards.md §2, §8)

```bash
black app tests migrations/versions wsgi.py
ruff check app tests migrations/versions wsgi.py
mypy app wsgi.py
bandit -r app
pip-audit
```

## Database migrations

The initial migration (`migrations/versions/9dc07a07a48b_*.py`) applies `docs/artifacts/schema.sql` verbatim rather than relying on Alembic autogenerate, so its CHECK constraints, partial indexes, and triggers are exactly what's documented. Any schema change after this baseline must still be its own reversible Alembic migration, and be reflected in the same PR in `docs/06-data-dictionary.md`, `docs/07-database-design.md`, and `docs/artifacts/schema.sql`.

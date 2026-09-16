# CSCM Tool — Application

Flask backend for the Controller Status Code Management Tool. See the root [../README.md](../README.md) and the [../docs/](../docs/00-INDEX.md) package for the full requirements/design basis this code implements.

## Status

Foundation scaffold only (EPIC-01 FEAT-01.1/01.2, `docs/17-implementation-backlog.md`): application factory, health endpoint, the full v2 SQLAlchemy model set, and the baseline Alembic migration applying `docs/artifacts/schema.sql`. Auth, RBAC, the numbering/review/approval services, and the UI have not been built yet — see `docs/18-claude-code-implementation-guide.md` §8 for the coding order.

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
flask run
```

`GET /api/v1/health` should return `{"status": "ok"}`.

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

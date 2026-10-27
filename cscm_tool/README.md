# CSCM Tool — Application

Flask backend for the Controller Status Code Management Tool. See the root [../README.md](../README.md) and the [../docs/](../docs/00-INDEX.md) package for the full requirements/design basis this code implements.

## Status

**v4 (2026-10-23):** the improvement pack of `../docs/21-improvement-ideas.md` (I-01 … I-36) is implemented, specified in `../docs/03-srs.md` §1.10–§1.15 and traced to tests in [`../docs/20-traceability-matrix.md`](../docs/20-traceability-matrix.md); the generated [`../docs/24-test-report.md`](../docs/24-test-report.md) holds the current test, coverage and quality-gate results. New in v4: optimistic concurrency, reference/duplicate warnings and Where-used, the import toolkit, export profiles / audiences / manifests / release notes / offline bundle, software versions, translations (English + German), SLA ageing and reminders, delegation, step-up re-authentication, change sets, field comments and review checklists, evidence, catalogue health, saved searches, fleet feedback, API tokens / change feed / webhooks, Hub-to-Main consolidation, ranked search, verified backups, the audit hash chain, readiness and metrics, the German UI, installers and CI. The API is `docs/artifacts/openapi.yaml` v4.0.0 (171 operations); the schema has 65 tables. **v4.2:** status codes can be imported from the generated `StCd_<n>.st` programs with a preview, multi-select and the legacy → new mapping (`app/importers/stcd.py`, `scripts/read_stcd.py` for the command line; `../docs/03-srs.md` §1.16). **v4.7:** the e-mail address of a user is fixed (FR-162); sign-in with the Windows account behind an authenticating gateway, simulated on a developer machine (`AUTH_MODE`, `WINDOWS_AUTH_*` in `.env.example`; FR-163, SEC-033); the translation review inside the application (sidebar *Translations*; FR-164, `../docs/26-translations.md`).

**Earlier:** v3 (2026-09-17) reworked the field set to match a real export of the live library (mandatory Functional Subgroup, eight audience-access lookups, Hub Controller groups); the Phase 1 backend epics (EPIC-01–04, 06, 08–10) and the server-rendered UI are complete. The UI (`../docs/10-ui-ux-specification.md`) is Jinja2 with vanilla JS/CSS — no CDN, no framework (`../docs/11-security-architecture.md` §12) — and uses the same service layer as the JSON API.

## Setup

The quickest way, the same in every shell and from any folder: `python scripts/first_start.py` (from the repository root: `python cscm_tool/scripts/first_start.py`). It does the steps below and prints the start command; see [../DEPLOYMENT-QUICKSTART.md](../DEPLOYMENT-QUICKSTART.md) for the error messages and the production installers. By hand:

```bash
python -m venv .venv
.venv/Scripts/activate   # .venv/bin/activate on Linux/macOS
pip install -r requirements.txt
cp .env.example .env     # then edit SECRET_KEY for anything beyond local dev (every setting is documented in the file)
```

## Running

```bash
flask db upgrade      # creates instance/cscm.db from the baseline migration + seed data
flask create-admin    # bootstraps the first Administrator account (prompts; or --username/--email/--full-name/--password; or CSCM_ADMIN_* environment variables)
flask run             # development; production: python scripts/serve.py (Waitress) or the installer below
```

`GET /api/v1/health` should return `{"status": "ok"}`; `GET /api/v1/health/ready` reports database, schema, audit chain and backup state. Log in with `POST /api/v1/auth/login`; every other state-changing request needs an `X-CSRFToken` header fetched from `GET /api/v1/auth/csrf-token` first (see `app/api/v1/auth_routes.py`).

## Operations (v4)

```bash
flask backup-db [--dest DIR] [--keep N]   # online backup, proven by a scratch restore; non-zero exit if it fails
flask verify-backup FILE                   # integrity + restore + audit-chain check of any backup file
flask audit-verify                         # verify the audit hash chain; non-zero exit if broken
flask audit-archive --dest DIR             # archive (never delete) entries past the retention period
flask send-reminders                       # in-app notices (and mail, if SMTP_* is set) for stalled requests
flask verify-export FILE MANIFEST          # check an exported file against its manifest, without the database
python scripts/pg_readiness.py [--check]   # inventory of SQLite-specific code (PostgreSQL readiness ratchet)
python scripts/gen_api_summary.py --write  # regenerate the endpoint table of docs/09
python scripts/gen_translations_doc.py --write  # regenerate the translation catalogue of docs/26 (after changing a string)
python scripts/gen_translations_doc.py --xlsx ar -o out/  # the review sheet of one language for a native speaker (or: --xlsx all)
```

Installation and upgrade on a server: `sudo deploy/linux/install.sh [--dry-run]` or `powershell -ExecutionPolicy Bypass -File deploy\windows\install.ps1 [-DryRun]` — see `../docs/14-deployment-architecture.md` §4a. CI: `python scripts/ci.py` (`.gitea/workflows/ci.yml`, `.gitlab-ci.yml`).

## Testing

```bash
pytest                         # everything, including the load tests
pytest -m "not performance"    # skip the load tests
pytest tests/performance -s    # NFR-001 / NFR-004 load tests, prints the measured latencies
python scripts/generate_test_report.py                      # methodology 1: file order + gates; rewrites docs/24-test-report.md
python scripts/generate_test_report.py --order shuffle:7    # methodology 2: shuffled order (also: reverse)
python scripts/generate_test_report.py --db file            # methodology 3: every test on a real SQLite file
```

By default every test gets a fresh in-memory SQLite database migrated through the same Alembic revision used everywhere else (`tests/conftest.py`) and its own instance directory, per `docs/15-development-standards.md` §7; `CSCM_TEST_DB=file` uses a file instead. The three verification methodologies are defined in `docs/13-test-strategy.md` §11.

## Code quality gates (docs/15-development-standards.md §2, §8)

```bash
black app tests migrations/versions scripts wsgi.py
ruff check app tests migrations/versions scripts wsgi.py
mypy app wsgi.py
bandit -q -r app
pip-audit -r requirements.txt
```

## Database migrations

The initial migration (`migrations/versions/9dc07a07a48b_*.py`) applies `docs/artifacts/schema.sql` verbatim rather than relying on Alembic autogenerate, so its CHECK constraints, partial indexes, and triggers are exactly what's documented. Any schema change after this baseline must still be its own reversible Alembic migration, and be reflected in the same PR in `docs/06-data-dictionary.md`, `docs/07-database-design.md`, and `docs/artifacts/schema.sql`.

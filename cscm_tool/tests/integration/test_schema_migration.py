"""US-003/US-004 acceptance criteria: fresh DB matches docs/artifacts/schema.sql
exactly, and all documented lookup rows are seeded. v3 (2026-09-17): field
model grounded in a real export of the live status code library, plus three
new Hub Controller Functional System Groups."""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    LookupFunctionalSubgroup,
    LookupFunctionalSystemGroup,
    LookupTurbinePlatform,
    Role,
)

EXPECTED_TABLES = {
    "role",
    "lookup_engineering_domain",
    "lookup_functional_system_group",
    "lookup_functional_subgroup",
    "lookup_turbine_platform",
    "lookup_available_group",
    "lookup_development_access",
    "lookup_sales_access",
    "lookup_tcc_access",
    "lookup_service_access",
    "lookup_top_access",
    "lookup_grid_operator_access",
    "lookup_service_partner_access",
    "lookup_customer_access",
    "user",
    "user_engineering_domain",
    "status_code",
    "status_code_revision",
    "status_code_revision_platform",
    "import_job",
    "change_request",
    "review_comment",
    "domain_signoff",
    "domain_signoff_request",
    "release",
    "release_item",
    "audit_log_entry",
    "export_job",
}


def test_all_documented_tables_exist(app):
    with app.app_context():
        inspector = inspect(db.engine)
        assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))


def test_twelve_functional_system_groups_seeded(app):
    """9 Main Controller groups + 3 Hub Controller groups (WTUR/WROT/WPPD
    in the 11000-13999 range), added 2026-09-17."""
    with app.app_context():
        assert db.session.query(LookupFunctionalSystemGroup).count() == 12


def test_functional_system_group_code_is_reused_for_hub_controller(app):
    """WTUR and WROT are each intentionally reused for a second,
    numerically distinct Hub Controller group (docs/06-data-dictionary.md
    §9) — uniqueness is on (code, range_start), not code alone."""
    with app.app_context():
        wtur_rows = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(LookupFunctionalSystemGroup.code == "WTUR")
            .all()
        )
        assert {g.range_start for g in wtur_rows} == {9000, 11000}


def test_thirty_eight_functional_subgroups_seeded(app):
    with app.app_context():
        assert db.session.query(LookupFunctionalSubgroup).count() == 38


def test_five_roles_seeded(app):
    with app.app_context():
        assert db.session.query(Role).count() == 5


def test_three_turbine_platforms_seeded(app):
    with app.app_context():
        codes = {p.code for p in db.session.query(LookupTurbinePlatform).all()}
        assert codes == {"2XM", "3XM", "4XM"}


def test_foreign_keys_enforced(app):
    """SEC/BR data-integrity depends on FK enforcement being on for every
    connection (docs/18-claude-code-implementation-guide.md §6)."""
    with app.app_context():
        result = db.session.execute(text("PRAGMA foreign_keys")).scalar()
        assert result == 1


def test_only_sandbox_status_codes_can_be_deleted(app):
    """Exercises trg_prevent_nonsandbox_delete from docs/artifacts/schema.sql."""
    with app.app_context():
        group = db.session.query(LookupFunctionalSystemGroup).first()
        subgroup = (
            db.session.query(LookupFunctionalSubgroup)
            .filter(LookupFunctionalSubgroup.functional_system_group_id == group.id)
            .first()
        )
        db.session.execute(
            text(
                "INSERT INTO user (username, email, password_hash, full_name, role_id, created_at) "
                "VALUES ('t1', 't1@example.com', 'x', 'Test User', 2, '2026-01-01T00:00:00Z')"
            )
        )
        user_id = db.session.execute(text("SELECT id FROM user WHERE username = 't1'")).scalar()
        db.session.execute(
            text(
                "INSERT INTO status_code "
                "(functional_system_group_id, functional_subgroup_id, is_sandbox, "
                "owner_id, created_at) "
                "VALUES (:group_id, :subgroup_id, 0, :owner_id, '2026-01-01T00:00:00Z')"
            ),
            {"group_id": group.id, "subgroup_id": subgroup.id, "owner_id": user_id},
        )
        db.session.commit()
        status_code_id = db.session.execute(
            text("SELECT id FROM status_code WHERE owner_id = :owner_id"), {"owner_id": user_id}
        ).scalar()

        with pytest.raises(IntegrityError):  # trg_prevent_nonsandbox_delete RAISE(ABORT, ...)
            db.session.execute(
                text("DELETE FROM status_code WHERE id = :id"), {"id": status_code_id}
            )
            db.session.commit()
        db.session.rollback()


def _alembic_cfg():
    from pathlib import Path

    from alembic.config import Config

    migrations = Path(__file__).resolve().parents[2] / "migrations"
    cfg = Config(str(migrations / "alembic.ini"))
    cfg.set_main_option("script_location", str(migrations))
    return cfg


def _schema_objects():
    inspector = inspect(db.session.connection())
    triggers = {
        row[0]
        for row in db.session.execute(text("SELECT name FROM sqlite_master WHERE type = 'trigger'"))
    }
    result = {
        "request_table": "domain_signoff_request" in inspector.get_table_names(),
        "lookup_description": "description"
        in {c["name"] for c in inspector.get_columns("lookup_sales_access")},
        "assigned_reviewer": "assigned_reviewer_id"
        in {c["name"] for c in inspector.get_columns("change_request")},
        "audit_triggers": {"trg_audit_no_update", "trg_audit_no_delete"} <= triggers,
        "password_history": "user_password_history" in inspector.get_table_names(),
    }
    db.session.remove()  # release the read transaction before Alembic opens its own
    return result


def test_second_migration_is_reversible_and_idempotent(app):
    """A database already at the earlier baseline is brought up to date by the
    follow-on migration; on a fresh database (which got everything from the
    baseline) it is a no-op."""
    from alembic import command

    with app.app_context():
        assert all(_schema_objects().values())

        command.downgrade(_alembic_cfg(), "9dc07a07a48b")
        old = _schema_objects()
        assert not old["request_table"] and not old["lookup_description"]
        assert not old["audit_triggers"] and not old["password_history"]

        command.upgrade(_alembic_cfg(), "head")
        assert all(_schema_objects().values())
        command.upgrade(_alembic_cfg(), "head")  # idempotent re-run
        assert all(_schema_objects().values())

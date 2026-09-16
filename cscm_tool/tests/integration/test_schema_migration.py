"""US-003/US-004 acceptance criteria: fresh DB matches docs/artifacts/schema.sql
exactly, and all documented lookup rows are seeded."""

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import LookupFunctionalSystemGroup, LookupTurbinePlatform, Role

EXPECTED_TABLES = {
    "role",
    "lookup_engineering_domain",
    "lookup_functional_system_group",
    "lookup_functional_subgroup",
    "lookup_turbine_platform",
    "lookup_status_category",
    "lookup_availability_group",
    "lookup_brake_program",
    "lookup_reset_program",
    "lookup_operational_state",
    "lookup_access_rights",
    "lookup_alarm_behaviour",
    "user",
    "user_engineering_domain",
    "status_code",
    "status_code_revision",
    "status_code_revision_platform",
    "change_request",
    "review_comment",
    "domain_signoff",
    "release",
    "release_item",
    "audit_log_entry",
    "export_job",
}


def test_all_documented_tables_exist(app):
    with app.app_context():
        inspector = inspect(db.engine)
        assert EXPECTED_TABLES.issubset(set(inspector.get_table_names()))


def test_nine_functional_system_groups_seeded(app):
    with app.app_context():
        assert db.session.query(LookupFunctionalSystemGroup).count() == 9


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
                "(functional_system_group_id, is_sandbox, owner_id, created_at) "
                "VALUES (:group_id, 0, :owner_id, '2026-01-01T00:00:00Z')"
            ),
            {"group_id": group.id, "owner_id": user_id},
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

"""Schema v4.1 (migration c9e2a4b6d815): PrgIdx_GUi on the status code, the controller-specific
revision columns and the user-group levels. The facts under test were read from generated
StCd_*.st programs (Main 1000-1010, Hub 14000/14005/14025); see docs/06-data-dictionary.md
sections 1, 2c, 2d, 2f and 9d.9."""

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from tests.conftest import MIGRATIONS_DIR

PREVIOUS_HEAD = "a1d4f6b8c203"

NEW_REVISION_COLUMNS = {
    "converter_reset_program",
    "hydraulic_pump_program",
    "gearbox_oil_pump_program",
    "gearbox_oil_fan_program",
    "gearbox_oil_heating_program",
    "generator_fan_program",
    "generator_heating_program",
    "generator_bearing_lubrication_program",
    "rotor_bearing_lubrication_program",
    "anemometer_heating_program",
    "medium_voltage_cb_program",
    "tower_fan_program",
    "transformer_oil_pump_program",
    "zero_load_operation",
    "pitch_error_program",
    "pitch_warning_program",
    "rotor_brake_program",
    "stop_program_40_flag",
    "stop_program_80_flag",
    "manual_operation_flag",
    "automatic_operation_flag",
    "vane_position_flag",
    "operating_mode_mask",
    "task_call_frequency",
    "availability_calc",
}


def _cfg():
    cfg = AlembicConfig(str(MIGRATIONS_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    return cfg


def _user() -> int:
    db.session.execute(
        text(
            "INSERT INTO user (username, email, password_hash, full_name, role_id, created_at) "
            "VALUES ('pg', 'pg@example.com', 'x', 'PrgIdx Tester', 2, '2026-01-01T00:00:00Z')"
        )
    )
    return db.session.execute(text("SELECT id FROM user WHERE username = 'pg'")).scalar()


def _code(user_id: int, prg_idx=None, sandbox=0) -> int:
    group, subgroup = db.session.execute(
        text("SELECT functional_system_group_id, id FROM lookup_functional_subgroup LIMIT 1")
    ).one()
    db.session.execute(
        text(
            "INSERT INTO status_code (functional_system_group_id, functional_subgroup_id, "
            "is_sandbox, owner_id, prg_idx) VALUES (:g, :s, :sb, :o, :p)"
        ),
        {"g": group, "s": subgroup, "sb": sandbox, "o": user_id, "p": prg_idx},
    )
    return db.session.execute(text("SELECT max(id) FROM status_code")).scalar()


def _revision(code_id: int, user_id: int, lifecycle="DRAFT") -> int:
    db.session.execute(
        text(
            "INSERT INTO status_code_revision (status_code_id, revision_number, title, description, "
            "status_category, available_group, set_delay, reset_delay, owner_id, created_by, "
            "lifecycle_status) VALUES (:c, 1, 'Rotor overspeed', 'Rotor speed above the limit.', "
            "'ERROR', 7, '0 ms', '200ms', :u, :u, :l)"
        ),
        {"c": code_id, "u": user_id, "l": lifecycle},
    )
    return db.session.execute(text("SELECT max(id) FROM status_code_revision")).scalar()


def test_prg_idx_is_an_optional_uint_that_is_unique_among_real_codes(app):
    with app.app_context():
        user = _user()
        _code(user, 14066)
        _code(user)  # NULL while a Draft or not yet imported: any number of them
        _code(user)
        _code(user, 65535)
        db.session.commit()
        for bad in (0, 65536, -1):
            with pytest.raises(IntegrityError):
                _code(user, bad)
            db.session.rollback()
        with pytest.raises(IntegrityError):  # the same block twice
            _code(user, 14066)
        db.session.rollback()
        _code(user, 14066, sandbox=1)  # a sandbox code never blocks a real number
        db.session.commit()


def test_prg_idx_is_frozen_once_a_revision_was_released(app):
    with app.app_context():
        user = _user()
        code = _code(user, 18926)
        revision = _revision(code, user)
        db.session.execute(
            text("UPDATE status_code SET prg_idx = 18927 WHERE id = :c"), {"c": code}
        )
        db.session.commit()  # a Draft may still be corrected
        db.session.execute(
            text("UPDATE status_code_revision SET lifecycle_status = 'RELEASED' WHERE id = :r"),
            {"r": revision},
        )
        db.session.commit()
        with pytest.raises(IntegrityError, match="cannot be changed"):
            db.session.execute(
                text("UPDATE status_code SET prg_idx = 18930 WHERE id = :c"), {"c": code}
            )
        db.session.rollback()
        with pytest.raises(IntegrityError, match="cannot be changed"):
            db.session.execute(
                text("UPDATE status_code SET prg_idx = NULL WHERE id = :c"), {"c": code}
            )
        db.session.rollback()

        legacy = _code(user)  # a released code without a number can still receive one
        _revision(legacy, user, "RELEASED")
        db.session.execute(
            text("UPDATE status_code SET prg_idx = 14071 WHERE id = :c"), {"c": legacy}
        )
        db.session.commit()


def test_leaving_draft_without_prg_idx_is_blocked_only_once_the_switch_is_on(app):
    with app.app_context():
        user = _user()
        before_switch = _revision(_code(user), user)
        db.session.execute(
            text("UPDATE status_code_revision SET lifecycle_status = 'REVIEW' WHERE id = :r"),
            {"r": before_switch},
        )
        db.session.commit()  # inert by default: the application does not collect the field yet

        db.session.execute(
            text("INSERT INTO app_setting (key, value) VALUES ('status_code.require_prg_idx', '1')")
        )
        blocked = _revision(_code(user), user)
        db.session.commit()
        with pytest.raises(IntegrityError, match="needs its PrgIdx_GUi"):
            db.session.execute(
                text("UPDATE status_code_revision SET lifecycle_status = 'REVIEW' WHERE id = :r"),
                {"r": blocked},
            )
        db.session.rollback()

        allowed = _revision(_code(user, 14097), user)
        sandbox = _revision(_code(user, sandbox=1), user)
        for revision in (allowed, sandbox):
            db.session.execute(
                text("UPDATE status_code_revision SET lifecycle_status = 'REVIEW' WHERE id = :r"),
                {"r": revision},
            )
        db.session.commit()


def test_new_revision_columns_start_at_zero_or_not_captured(app):
    with app.app_context():
        user = _user()
        revision = _revision(_code(user), user)
        row = (
            db.session.execute(
                text("SELECT * FROM status_code_revision WHERE id = :r"), {"r": revision}
            )
            .mappings()
            .one()
        )
        assert NEW_REVISION_COLUMNS <= set(row)
        for name in NEW_REVISION_COLUMNS:
            expected = 0 if name.endswith("_program") else None
            assert row[name] == expected, name
        with pytest.raises(IntegrityError):  # the operating-mode mask is 20 bits at most
            db.session.execute(
                text("UPDATE status_code_revision SET operating_mode_mask = 1048576 WHERE id = :r"),
                {"r": revision},
            )
        db.session.rollback()
        db.session.execute(
            text(
                "UPDATE status_code_revision SET operating_mode_mask = 59 WHERE id = :r"
            ),  # 0b111011
            {"r": revision},
        )
        db.session.commit()


def test_the_locked_revision_trigger_covers_the_new_content_columns(app):
    with app.app_context():
        user = _user()
        revision = _revision(_code(user), user, "APPROVED")
        db.session.commit()
        for column, value in (("rotor_brake_program", 20), ("operating_mode_mask", 59)):
            with pytest.raises(IntegrityError, match="Cannot edit a revision"):
                db.session.execute(
                    text(f"UPDATE status_code_revision SET {column} = :v WHERE id = :r"),
                    {"v": value, "r": revision},
                )
            db.session.rollback()


def test_the_sixteen_user_group_slots_map_slots_one_to_eight_to_the_audiences(app):
    with app.app_context():
        rows = db.session.execute(
            text("SELECT slot, audience_code, is_active FROM lookup_user_group_slot ORDER BY slot")
        ).all()
        assert [r[0] for r in rows] == list(range(16))
        audiences = [r[1] for r in rows if r[1]]
        assert audiences == [
            "DEVELOPMENT",
            "SALES",
            "TCC",
            "SERVICE",
            "TURBINE_OPERATOR_PACKAGE",
            "GRID_OPERATOR",
            "SERVICE_PARTNER",
            "CUSTOMER",
        ]
        assert [r[0] for r in rows if r[1]] == list(range(1, 9))
        assert {r[0] for r in rows if not r[2]} == {0, 9, 10, 11, 12, 13, 14, 15}


def test_user_group_levels_are_bytes_and_unique_per_revision_and_slot(app):
    with app.app_context():
        user = _user()
        revision = _revision(_code(user), user)
        slot = db.session.execute(
            text("SELECT id FROM lookup_user_group_slot WHERE slot = 5")
        ).scalar()
        insert = text(
            "INSERT INTO status_code_revision_user_group "
            "(status_code_revision_id, user_group_slot_id, read_level, write_level) "
            "VALUES (:r, :s, :rd, :wr)"
        )
        db.session.execute(insert, {"r": revision, "s": slot, "rd": 1, "wr": 10})
        db.session.commit()
        with pytest.raises(IntegrityError):
            db.session.execute(insert, {"r": revision, "s": slot, "rd": 1, "wr": 15})
        db.session.rollback()
        other = db.session.execute(
            text("SELECT id FROM lookup_user_group_slot WHERE slot = 6")
        ).scalar()
        with pytest.raises(IntegrityError):
            db.session.execute(insert, {"r": revision, "s": other, "rd": 1, "wr": 256})
        db.session.rollback()


def test_default_levels_are_seeded_only_where_the_programs_agree(app):
    with app.app_context():

        def level(table, code):
            return db.session.execute(
                text(
                    f"SELECT default_read_level, default_write_level FROM {table} WHERE code = :c"
                ),
                {"c": code},
            ).one()

        assert level("lookup_top_access", "PREVENTIVE_MAINTENANCE") == (1, 10)
        assert level("lookup_top_access", "TROUBLESHOOTING") == (1, 15)
        assert level("lookup_development_access", "OPERATION_CONTROL") == (1, 20)
        assert level("lookup_service_partner_access", "EXT_SERVICE_PROVIDER") == (1, 15)
        assert level("lookup_customer_access", "SEE_ONLY") == (1, 50)
        assert level("lookup_customer_access", "COVERT") == (50, 50)
        # the same named value carried 10 on one code and 20 on another: no default
        assert level("lookup_service_access", "SERVICE_AND_MAINTENANCE") == (None, None)
        assert level("lookup_tcc_access", "TELENOTDIENST") == (None, None)


def test_the_migration_is_reversible_and_re_applies_cleanly(app):
    with app.app_context():
        db.session.remove()
        command.downgrade(_cfg(), PREVIOUS_HEAD)
        inspector = inspect(db.engine)
        assert "prg_idx" not in {c["name"] for c in inspector.get_columns("status_code")}
        assert not (
            NEW_REVISION_COLUMNS
            & {c["name"] for c in inspector.get_columns("status_code_revision")}
        )
        assert "lookup_user_group_slot" not in inspector.get_table_names()
        assert "status_code_revision_user_group" not in inspector.get_table_names()
        triggers = {
            r[0]
            for r in db.session.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'"))
        }
        assert "trg_prevent_edit_locked_revision" in triggers
        assert (
            not {
                "trg_prevent_prg_idx_change_after_release",
                "trg_require_prg_idx_for_review",
            }
            & triggers
        )
        db.session.remove()

        command.upgrade(_cfg(), "head")
        inspector = inspect(db.engine)
        assert "prg_idx" in {c["name"] for c in inspector.get_columns("status_code")}
        assert NEW_REVISION_COLUMNS <= {
            c["name"] for c in inspector.get_columns("status_code_revision")
        }
        assert (
            db.session.execute(text("SELECT COUNT(*) FROM lookup_user_group_slot")).scalar() == 16
        )
        assert (
            db.session.execute(
                text(
                    "SELECT default_write_level FROM lookup_top_access WHERE code = 'TROUBLESHOOTING'"
                )
            ).scalar()
            == 15
        )
        assert db.session.execute(
            text("SELECT name FROM sqlite_master WHERE name = 'ux_status_code_prg_idx'")
        ).first()
        db.session.remove()

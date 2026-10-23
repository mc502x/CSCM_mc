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


def test_six_roles_seeded(app):
    with app.app_context():
        assert db.session.query(Role).count() == 6
        assert db.session.query(Role).filter_by(code="STCD_OWNER").one().id == 6


def test_nineteen_languages_seeded_with_country_letters_left_and_the_flag_right(app):
    from app.models.lookup import LookupLanguage

    with app.app_context():
        labels = {
            lang.code: lang.label
            for lang in db.session.query(LookupLanguage).order_by(LookupLanguage.sort_order)
        }
    # Arabic is followed by the ten languages of v4.5, in the order they were asked for
    assert list(labels) == [
        "en",
        "de",
        "fr",
        "hi",
        "ar",
        "bn",
        "mr",
        "te",
        "ta",
        "gu",
        "ur",
        "kn",
        "or",
        "ml",
        "pa",
        "es",
        "it",
        "da",
        "ka",
    ]
    india, pakistan = "\U0001f1ee\U0001f1f3", "\U0001f1f5\U0001f1f0"
    expected = {
        "en": ("GB", "English", "\U0001f1ec\U0001f1e7"),
        "de": ("DE", "Deutsch", "\U0001f1e9\U0001f1ea"),
        "fr": ("FR", "Fran\u00e7ais", "\U0001f1eb\U0001f1f7"),
        "hi": ("IN", "Hindi", india),
        "ka": ("GE", "Georgian", "\U0001f1ec\U0001f1ea"),
        "ar": ("SA", "Arabic", "\U0001f1f8\U0001f1e6"),
        "bn": ("IN", "Bengali", india),
        "mr": ("IN", "Marathi", india),
        "te": ("IN", "Telugu", india),
        "ta": ("IN", "Tamil", india),
        "gu": ("IN", "Gujarati", india),
        "ur": ("PK", "Urdu", pakistan),
        "kn": ("IN", "Kannada", india),
        "or": ("IN", "Odia", india),
        "ml": ("IN", "Malayalam", india),
        "pa": ("IN", "Punjabi", india),
        "es": ("ES", "Espa\u00f1ol", "\U0001f1ea\U0001f1f8"),
        "it": ("IT", "Italiano", "\U0001f1ee\U0001f1f9"),
        "da": ("DK", "Dansk", "\U0001f1e9\U0001f1f0"),
    }
    for code, (letters, name, flag) in expected.items():
        assert labels[code].startswith(letters + " ") and labels[code].endswith(" " + flag), code
        if code in ("en", "de", "fr", "es", "it", "da"):
            assert name in labels[code]
        else:
            assert f"({name})" in labels[code]  # the native name plus the English one


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


def test_first_subgroup_of_every_main_group_covers_the_first_200_numbers(app):
    """Rule of 2026-10-22: e.g. Tower 5000-5199, Generator 2000-2199; the next
    subgroup of each group begins after it and never overlaps."""
    with app.app_context():
        groups = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(LookupFunctionalSystemGroup.range_start < 10000)
            .all()
        )
        assert len(groups) == 9
        for group in groups:
            subgroups = (
                db.session.query(LookupFunctionalSubgroup)
                .filter(LookupFunctionalSubgroup.functional_system_group_id == group.id)
                .order_by(LookupFunctionalSubgroup.sub_range_start)
                .all()
            )
            first = subgroups[0]
            assert (first.sub_range_start, first.sub_range_end) == (
                group.range_start,
                group.range_start + 199,
            ), group.code
            for earlier, later in zip(subgroups, subgroups[1:], strict=False):
                assert later.sub_range_start > earlier.sub_range_end, (group.code, later.code)


def test_no_placeholder_group_is_seeded(app):
    """Only the 12 real groups exist out of the box; free ranges stay free."""
    with app.app_context():
        codes = {g.code for g in db.session.query(LookupFunctionalSystemGroup).all()}
        assert "WNEW" not in codes
        assert db.session.query(LookupFunctionalSystemGroup).count() == 12


def test_hub_sub_bands_are_aligned_to_the_hundreds_of_their_prefix(app):
    """docs/05-governance-handbook.md section 2: `123xx` owns 12300-12399; a band shorter than a
    hundred is named by its first ten (`1110x` 11100-11149, `1115x` 11150-11199). No code has a dash
    or a letter after the x."""
    import re

    with app.app_context():
        rows = (
            db.session.query(LookupFunctionalSubgroup, LookupFunctionalSystemGroup)
            .join(
                LookupFunctionalSystemGroup,
                LookupFunctionalSystemGroup.id
                == LookupFunctionalSubgroup.functional_system_group_id,
            )
            .filter(LookupFunctionalSystemGroup.range_start >= 11000)
            .all()
        )
        assert len(rows) == 11
        for subgroup, group in rows:
            match = re.match(r"^(\d{3,4})(x{1,2})$", subgroup.code)
            assert match, subgroup.code
            digits, free = match.groups()
            expected_start = int(digits) * 10 ** len(free)
            assert subgroup.sub_range_start == expected_start, subgroup.code
            assert subgroup.sub_range_start >= group.range_start
            assert subgroup.sub_range_end <= group.range_end
            assert subgroup.sub_range_end > subgroup.sub_range_start


def test_subgroup_codes_have_no_dash_and_no_letter_after_the_x(app):
    import re

    with app.app_context():
        codes = [s.code for s in db.session.query(LookupFunctionalSubgroup).all()]
    assert len(codes) == 38
    assert all(re.fullmatch(r"\d{3,4}x{1,2}", c) for c in codes), codes
    assert len(set(codes)) == len(codes)
    assert {"0990x", "0993x", "0996x", "0999x", "110xx", "1110x", "1115x", "1205x"} <= set(codes)

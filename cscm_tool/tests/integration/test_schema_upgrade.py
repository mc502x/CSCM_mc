"""Upgrading a database that was created by the previous release (Alembic d6f8b0c2e4a3, schema v3)
to v4: nothing is lost, the new columns and tables appear, the audit chain is back-filled and
verifies, the search index is filled, and an upgraded database ends up with the same shape as a
fresh one. The v3 database is built from tests/fixtures/schema_d6f8b0c2e4a3.sql, a frozen copy of
that release's schema, because the baseline migration always executes the *current* schema.

TC-045. Requirements: AUD-074, FR-148, FR-147, BR-016.
"""

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig

from app import create_app
from app.audit_chain import AuditChainService
from app.audit_hash import GENESIS
from app.extensions import db
from app.models.status_code import StatusCodeRevision
from tests.conftest import MIGRATIONS_DIR

FROZEN = Path(__file__).resolve().parents[1] / "fixtures" / "schema_d6f8b0c2e4a3.sql"
OLD_HEAD = "d6f8b0c2e4a3"


def _cfg():
    cfg = AlembicConfig(str(MIGRATIONS_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    return cfg


def _build_v3_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(FROZEN.read_text(encoding="utf-8"))
    connection.execute(
        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
    )
    connection.execute("INSERT INTO alembic_version VALUES (?)", (OLD_HEAD,))
    role = connection.execute("SELECT id FROM role WHERE code = 'ENGINEER'").fetchone()[0]
    connection.execute(
        "INSERT INTO user (id, username, email, password_hash, full_name, role_id) "
        "VALUES (1, 'old', 'old@example.com', 'x', 'Old User', ?)",
        (role,),
    )
    group, sub = connection.execute(
        "SELECT g.id, s.id FROM lookup_functional_system_group g JOIN lookup_functional_subgroup s "
        "ON s.functional_system_group_id = g.id WHERE g.code = 'WCNV' AND s.code = '010xx'"
    ).fetchone()
    for n in (1, 2):
        connection.execute(
            "INSERT INTO status_code (id, functional_system_group_id, functional_subgroup_id, owner_id) "
            "VALUES (?, ?, ?, 1)",
            (n, group, sub),
        )
        connection.execute(
            "INSERT INTO status_code_revision (status_code_id, revision_number, title, description, "
            "status_category, available_group, set_delay, reset_delay, owner_id, created_by) "
            "VALUES (?, 1, ?, 'Created before the upgrade.', 'ERROR', 27, '10ms', '2min', 1, 1)",
            (n, f"Legacy converter code {n}"),
        )
    connection.execute(
        "INSERT INTO import_job (id, requested_by, source_format, source_file_reference, row_count) "
        "VALUES (1, 1, 'CSV', 'imports/1/source.csv', 2)"
    )
    connection.execute(
        "INSERT INTO change_request (status_code_revision_id, cr_type, requested_by, import_job_id) "
        "VALUES (1, 'IMPORT', 1, 1)"
    )
    for n in range(1, 5):
        connection.execute(
            "INSERT INTO audit_log_entry (entity_type, entity_id, action, request_id) "
            "VALUES ('StatusCode', ?, 'CREATE', 'legacy')",
            (n,),
        )
    connection.commit()
    connection.close()


@pytest.fixture()
def upgraded(tmp_path):
    path = tmp_path / "old.db"
    _build_v3_database(path)
    application = create_app("testing", {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{path.as_posix()}"})
    application.instance_path = str(tmp_path)
    with application.app_context():
        command.upgrade(_cfg(), "head")
    yield application, path
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def _columns(connection) -> dict[str, list[str]]:
    tables = [
        r[0]
        for r in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "AND name NOT LIKE 'alembic_%' AND name NOT LIKE 'status_code_fts%' ORDER BY name"
        )
    ]
    return {
        t: sorted(r[1] for r in connection.execute(f'PRAGMA table_info("{t}")')) for t in tables
    }


def test_existing_data_survives_the_upgrade(upgraded):
    _, path = upgraded
    connection = sqlite3.connect(path)
    assert connection.execute("SELECT COUNT(*) FROM status_code").fetchone()[0] == 2
    titles = [
        r[0] for r in connection.execute("SELECT title FROM status_code_revision ORDER BY id")
    ]
    assert titles == ["Legacy converter code 1", "Legacy converter code 2"]
    assert connection.execute("SELECT username FROM user").fetchone()[0] == "old"
    assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] != OLD_HEAD


def test_new_columns_default_sensibly_on_old_rows(upgraded):
    _, path = upgraded
    connection = sqlite3.connect(path)
    row = connection.execute(
        "SELECT row_version, updated_at, remedy_text, applies_from_version_id FROM status_code_revision"
    ).fetchone()
    assert row[0] == 1 and row[2] is None and row[3] is None
    assert connection.execute("SELECT ui_language FROM user").fetchone()[0] == "en"


def test_covert_is_not_visible_and_the_other_audiences_still_are(upgraded):
    _, path = upgraded
    connection = sqlite3.connect(path)
    covert = connection.execute(
        "SELECT audience_visible FROM lookup_customer_access WHERE code = 'COVERT'"
    ).fetchone()
    assert covert == (0,)
    visible = connection.execute(
        "SELECT COUNT(*) FROM lookup_customer_access WHERE code != 'COVERT' AND audience_visible = 1"
    ).fetchone()[0]
    assert visible >= 1


def test_hub_groups_become_hub_controller_groups(upgraded):
    _, path = upgraded
    connection = sqlite3.connect(path)
    rows = connection.execute(
        "SELECT range_start >= 11000, controller_type FROM lookup_functional_system_group"
    ).fetchall()
    assert len(rows) == 12
    assert all(kind == ("HUB" if is_hub else "MAIN") for is_hub, kind in rows)
    assert sum(1 for is_hub, _ in rows if is_hub) == 3


def test_hub_sub_bands_are_shifted_to_the_hundreds_by_the_upgrade(upgraded):
    """The v3 database still has the legacy x001 bands; the upgrade aligns them."""
    _, path = upgraded
    connection = sqlite3.connect(path)
    bands = {
        code: (start, end)
        for code, start, end in connection.execute(
            "SELECT code, sub_range_start, sub_range_end FROM lookup_functional_subgroup "
            "WHERE sub_range_start >= 11000"
        )
    }
    assert bands["123xx"] == (12300, 12399) and bands["110xx"] == (11000, 11099)
    assert bands["1110x"] == (11100, 11149) and bands["130xx"] == (13000, 13099)


def test_the_subgroup_codes_lose_their_letters_and_dashes_in_the_upgrade(upgraded):
    _, path = upgraded
    connection = sqlite3.connect(path)
    codes = [r[0] for r in connection.execute("SELECT code FROM lookup_functional_subgroup")]
    assert not [c for c in codes if "-" in c or c[-1].isalpha() and c[-1] != "x"], codes
    assert {"0990x", "0996x", "1205x", "1115x"} <= set(codes)


def test_the_languages_and_export_profiles_are_seeded(upgraded):
    _, path = upgraded
    connection = sqlite3.connect(path)
    assert {r[0] for r in connection.execute("SELECT code FROM lookup_language")} == {
        "en",
        "de",
        "fr",
        "hi",
        "ka",
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
    }
    assert connection.execute("SELECT COUNT(*) FROM export_profile").fetchone()[0] == 3


def test_the_table_rebuilds_leave_every_foreign_key_intact(upgraded):
    """import_job (revision b3f5a7c9d124) and user (d4a6c8e0f236) are rebuilt to widen a CHECK; the
    tables that reference them must still point at them, not at the discarded copy."""
    _, path = upgraded
    connection = sqlite3.connect(path)
    schema = " ".join(r[0] or "" for r in connection.execute("SELECT sql FROM sqlite_master"))
    assert "import_job_old" not in schema and "user_old" not in schema
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert (
        connection.execute(
            "SELECT COUNT(*) FROM change_request c JOIN import_job j ON j.id = c.import_job_id"
        ).fetchone()[0]
        == 1
    )
    connection.execute("UPDATE user SET ui_language = 'ka' WHERE id = 1")  # CHECK accepts it now
    connection.execute("UPDATE user SET ui_language = 'ml' WHERE id = 1")  # ... and any two letters
    connection.execute(
        "INSERT INTO import_job (requested_by, source_format, source_file_reference, row_count) VALUES (1, 'ST', 'x', 0)"
    )
    assert (
        connection.execute("SELECT COUNT(*) FROM role WHERE code = 'STCD_OWNER'").fetchone()[0] == 1
    )


def test_old_audit_rows_are_chained_and_the_chain_verifies(upgraded):
    application, path = upgraded
    connection = sqlite3.connect(path)
    assert (
        connection.execute(
            "SELECT COUNT(*) FROM audit_log_entry WHERE entry_hash IS NULL"
        ).fetchone()[0]
        == 0
    )
    first = connection.execute(
        "SELECT prev_hash FROM audit_log_entry ORDER BY id LIMIT 1"
    ).fetchone()[0]
    assert first == GENESIS
    with application.app_context():
        assert AuditChainService.verify(update_anchor=False)["ok"] is True


def test_the_migrated_hash_equals_what_the_application_would_have_written(upgraded):
    """Migration and application share one canonical form (app/audit_hash.py)."""
    application, path = upgraded
    with application.app_context():
        from app.services.audit_service import AuditService

        AuditService.log("StatusCode", 1, "UPDATE", actor=None, after={"title": "x"})
        db.session.commit()
        assert AuditChainService.verify(update_anchor=False)["ok"] is True  # old rows + a new one


def test_the_search_index_is_filled_with_the_old_codes(upgraded):
    application, _ = upgraded
    with application.app_context():
        from app.repositories import fts

        if not fts.available():
            pytest.skip("this SQLite build has no FTS5")
        hits = db.session.execute(
            db.text("SELECT COUNT(*) FROM status_code_fts WHERE status_code_fts MATCH 'converter'")
        ).scalar()
        assert hits == 2


def test_the_upgraded_database_works_for_a_whole_workflow(upgraded):
    application, path = upgraded
    with application.app_context():
        from app.services.user_service import UserService

        UserService.create_user(
            username="newbie",
            email="n@example.com",
            full_name="N",
            role_code="ENGINEER",
            password="a genuinely long passphrase",
            actor=None,
        )
        assert db.session.query(StatusCodeRevision).count() == 2
    client = application.test_client()
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": "newbie", "password": "a genuinely long passphrase"},
        ).status_code
        == 200
    )
    listing = client.get("/api/v1/status-codes?q=converter").get_json()
    assert listing["total"] == 2


def test_an_upgraded_database_has_the_same_shape_as_a_fresh_one(upgraded, app):
    _, path = upgraded
    upgraded_shape = _columns(sqlite3.connect(path))
    # the fresh test database is in memory: read its shape through SQLAlchemy
    with app.app_context():
        fresh_shape = {}
        for (table,) in db.session.execute(
            db.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "AND name NOT LIKE 'alembic_%' AND name NOT LIKE 'status_code_fts%' ORDER BY name"
            )
        ):
            fresh_shape[table] = sorted(
                r[1] for r in db.session.execute(db.text(f'PRAGMA table_info("{table}")'))
            )
    assert set(upgraded_shape) == set(fresh_shape)
    differences = {
        t: (upgraded_shape[t], fresh_shape[t])
        for t in fresh_shape
        if upgraded_shape[t] != fresh_shape[t]
    }
    assert differences == {}


def test_every_trigger_of_a_fresh_database_exists_after_the_upgrade(upgraded, app):
    _, path = upgraded
    names = lambda c: {  # noqa: E731
        r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    }
    with app.app_context():
        fresh = {
            r[0]
            for r in db.session.execute(
                db.text("SELECT name FROM sqlite_master WHERE type='trigger'")
            )
        }
    assert fresh <= names(sqlite3.connect(path))


def test_a_second_upgrade_is_a_no_op_and_the_downgrade_returns_to_v3_with_the_data(upgraded):
    application, path = upgraded
    with application.app_context():
        command.upgrade(_cfg(), "head")
    with application.app_context():
        db.session.remove()
        command.downgrade(_cfg(), OLD_HEAD)
    connection = sqlite3.connect(path)
    tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "change_set" not in tables and "notification" not in tables
    assert connection.execute("SELECT COUNT(*) FROM status_code_revision").fetchone()[0] == 2
    columns = {r[1] for r in connection.execute("PRAGMA table_info(status_code_revision)")}
    assert "row_version" not in columns and "title" in columns
    assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == OLD_HEAD
    with application.app_context():
        db.session.remove()
        command.upgrade(_cfg(), "head")  # and forward again
    assert (
        sqlite3.connect(path).execute("SELECT COUNT(*) FROM status_code_revision").fetchone()[0]
        == 2
    )


def test_import_job_is_rebuilt_for_programs_without_losing_rows_or_references(upgraded):
    """v4.2: the CHECK of import_job.source_format has to widen to 'ST', which SQLite can only do by
    rebuilding the table; change_request must keep pointing at it, and its row must survive."""
    _, path = upgraded
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    assert connection.execute(
        "SELECT source_format, change_set_id, row_count FROM import_job WHERE id = 1"
    ).fetchone() == ("CSV", None, 2)
    assert connection.execute("SELECT import_job_id FROM change_request").fetchone() == (1,)
    targets = {r[2] for r in connection.execute("PRAGMA foreign_key_list(change_request)")}
    assert "import_job" in targets and "import_job_old" not in targets
    connection.execute(
        "INSERT INTO import_job (requested_by, source_format, source_file_reference, row_count) "
        "VALUES (1, 'ST', 'imports/2', 3)"
    )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO import_job (requested_by, source_format, source_file_reference, row_count) "
            "VALUES (1, 'PDF', 'x', 1)"
        )
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "import_source_item" in tables and "import_job_old" not in tables
    assert "reserved_identifier" in {
        r[1] for r in connection.execute("PRAGMA table_info(status_code)")
    }

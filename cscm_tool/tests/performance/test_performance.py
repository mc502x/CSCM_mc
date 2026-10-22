"""NFR-001, TC-024, TC-025, NFR-004: performance targets on a temp-file SQLite
database (docs/13-test-strategy.md §5).

Targets: p95 <= 500 ms list/search at 20,000 revisions across all Functional
System Groups, p95 <= 200 ms single-record read, 5 s CSV/JSON export of 5,000
records, 15 s PDF export of 5,000 records, and concurrent identifier
allocation within one popular group that stays correct (no duplicates, no
gaps) and fast."""

import statistics
import threading
import time
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig

from app import create_app
from app.auth.rate_limit import reset_for_testing
from app.config import CONFIG_BY_NAME, TestingConfig
from app.extensions import db
from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup
from app.services.numbering_service import NumberingService
from app.services.user_service import UserService
from tests.helpers import PASSWORD

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
TOTAL_REVISIONS = 20_000
EXPORT_RECORDS = 5_000

pytestmark = pytest.mark.performance


def p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    return ordered[max(0, int(round(0.95 * len(ordered))) - 1)]


@pytest.fixture()
def file_app(tmp_path, monkeypatch):
    class PerfConfig(TestingConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'perf.db'}"

    monkeypatch.setitem(CONFIG_BY_NAME, "perf", PerfConfig)
    application = create_app("perf")
    with application.app_context():
        cfg = AlembicConfig(str(MIGRATIONS_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
        command.upgrade(cfg, "head")
    reset_for_testing()
    yield application
    with application.app_context():
        db.engine.dispose()


def _seed(app, total: int):
    """Bulk-inserts `total` Released revisions spread across every Functional
    System Group/Subgroup (raw SQL: this measures reads, not the write path)."""
    with app.app_context():
        user = UserService.create_user(
            username="perf",
            email="perf@example.com",
            full_name="Perf User",
            role_code="ENGINEER",
            password=PASSWORD,
            actor=None,
        )
        owner_id = user.id
        pairs = [
            (g.id, s.id)
            for g, s in db.session.query(LookupFunctionalSystemGroup, LookupFunctionalSubgroup)
            .filter(
                LookupFunctionalSubgroup.functional_system_group_id
                == LookupFunctionalSystemGroup.id
            )
            .all()
        ]
        codes, revisions = [], []
        for i in range(1, total + 1):
            group_id, subgroup_id = pairs[i % len(pairs)]
            codes.append((i, f"StCd-{i:05d}", group_id, subgroup_id, owner_id))
            revisions.append(
                (
                    i,
                    i,
                    f"Perf status code {i} converter trip",
                    f"Synthetic description number {i} for load testing of search.",
                    owner_id,
                )
            )
        conn = db.session.connection()
        conn.exec_driver_sql(
            "INSERT INTO status_code (id, status_code_identifier, functional_system_group_id,"
            " functional_subgroup_id, is_sandbox, owner_id, created_at)"
            " VALUES (?, ?, ?, ?, 0, ?, '2026-01-01T00:00:00.000Z')",
            codes,
        )
        conn.exec_driver_sql(
            "INSERT INTO status_code_revision (id, status_code_id, revision_number, is_current,"
            " title, description, status_category, available_group, set_delay, reset_delay,"
            " owner_id, lifecycle_status, created_by, created_at)"
            " VALUES (?, ?, 1, 1, ?, ?, 'ERROR', 27, '10ms', '2min', ?, 'RELEASED', ?,"
            " '2026-01-01T00:00:00.000Z')",
            [(r[0], r[1], r[2], r[3], r[4], r[4]) for r in revisions],
        )
        platform_id = conn.exec_driver_sql(
            "SELECT id FROM lookup_turbine_platform WHERE code = '3XM'"
        ).scalar()
        conn.exec_driver_sql(
            "INSERT INTO status_code_revision_platform"
            " (status_code_revision_id, turbine_platform_id) VALUES (?, ?)",
            [(r[0], platform_id) for r in revisions],
        )
        db.session.commit()
    return user


def _login(client):
    reset_for_testing()
    response = client.post("/api/v1/auth/login", json={"username": "perf", "password": PASSWORD})
    assert response.status_code == 200


def _timed(call, repeat: int) -> list[float]:
    samples = []
    for _ in range(repeat):
        start = time.perf_counter()
        response = call()
        samples.append(time.perf_counter() - start)
        assert response.status_code == 200
    return samples


def test_search_and_read_latency_at_20000_revisions(file_app, record_property, speed_factor):
    """TC-024."""
    _seed(file_app, TOTAL_REVISIONS)
    client = file_app.test_client()
    _login(client)

    with file_app.app_context():
        total = db.session.execute(db.text("SELECT COUNT(*) FROM status_code_revision")).scalar()
        group_ids = [g.id for g in db.session.query(LookupFunctionalSystemGroup).all()]
    assert total == TOTAL_REVISIONS
    assert len(group_ids) >= 9

    searches = []
    for n in range(40):
        searches.append(
            lambda n=n: client.get(
                "/api/v1/status-codes",
                query_string={
                    "q": ["converter", f"code {n * 37}", "StCd-0", "load testing"][n % 4],
                    "functional_system_group": group_ids[n % len(group_ids)] if n % 2 else None,
                    "sort": "title",
                    "page_size": 50,
                },
            )
        )
    list_samples = [s for call in searches for s in _timed(call, 1)]
    assert p95(list_samples) <= 0.5 * speed_factor, f"search p95 {p95(list_samples):.3f}s"

    read_samples = _timed(lambda: client.get("/api/v1/status-codes/12345"), 60)
    assert p95(read_samples) <= 0.2 * speed_factor, f"read p95 {p95(read_samples):.3f}s"
    record_property("search_p95_ms", round(p95(list_samples) * 1000, 1))
    record_property("search_median_ms", round(statistics.median(list_samples) * 1000, 1))
    record_property("read_p95_ms", round(p95(read_samples) * 1000, 1))
    record_property("revisions", TOTAL_REVISIONS)
    record_property("speed_factor", speed_factor)
    print(
        f"\nsearch p95={p95(list_samples) * 1000:.0f}ms median="
        f"{statistics.median(list_samples) * 1000:.0f}ms; read p95={p95(read_samples) * 1000:.0f}ms"
    )


@pytest.mark.parametrize("fmt,limit_seconds", [("csv", 5), ("json", 5), ("xlsx", 15), ("pdf", 15)])
def test_export_of_5000_records_within_target(
    file_app, fmt, limit_seconds, record_property, speed_factor
):
    """NFR-001: CSV/JSON <= 5 s, PDF <= 15 s for 5,000 records (XLSX held to the PDF limit)."""
    _seed(file_app, EXPORT_RECORDS)
    client = file_app.test_client()
    _login(client)

    start = time.perf_counter()
    response = client.get(f"/api/v1/exports/released?format={fmt}")
    elapsed = time.perf_counter() - start
    assert response.status_code == 200
    assert elapsed <= limit_seconds * speed_factor, f"{fmt} export took {elapsed:.1f}s"
    record_property("export_seconds", round(elapsed, 2))
    record_property("records", EXPORT_RECORDS)
    record_property("limit_seconds", limit_seconds)
    record_property("speed_factor", speed_factor)
    print(f"\n{fmt} export of {EXPORT_RECORDS}: {elapsed:.2f}s")


def test_concurrent_identifier_allocation_in_one_group(file_app, record_property, speed_factor):
    """TC-025: parallel submissions in one popular group yield unique, gap-free
    identifiers (BEGIN IMMEDIATE serialises allocation) within a latency budget."""
    with file_app.app_context():
        group = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(LookupFunctionalSystemGroup.code == "WCNV")
            .one()
        )
        subgroup = (
            db.session.query(LookupFunctionalSubgroup)
            .filter(
                LookupFunctionalSubgroup.functional_system_group_id == group.id,
                LookupFunctionalSubgroup.code == "010xx",
            )
            .one()
        )
        group_id, subgroup_id = group.id, subgroup.id
        owner_id = UserService.create_user(
            username="alloc",
            email="alloc@example.com",
            full_name="Alloc",
            role_code="ENGINEER",
            password=PASSWORD,
            actor=None,
        ).id

    workers, per_worker = 8, 8
    identifiers: list[str] = []
    latencies: list[float] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker(worker_no: int):
        try:
            for _ in range(per_worker):
                with file_app.app_context():
                    start = time.perf_counter()
                    # Mirrors ChangeRequestService.submit: allocate + persist in ONE transaction.
                    identifier = NumberingService.allocate_next_identifier(group_id, subgroup_id)
                    db.session.execute(
                        db.text(
                            "INSERT INTO status_code (status_code_identifier,"
                            " functional_system_group_id, functional_subgroup_id, is_sandbox,"
                            " owner_id, created_at) VALUES (:i, :g, :s, 0, :o,"
                            " '2026-01-01T00:00:00.000Z')"
                        ),
                        {"i": identifier, "g": group_id, "s": subgroup_id, "o": owner_id},
                    )
                    db.session.commit()
                    elapsed = time.perf_counter() - start
                with lock:
                    identifiers.append(identifier)
                    latencies.append(elapsed)
        except BaseException as exc:  # noqa: BLE001 - surfaced by the assertion below
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker, args=(w,)) for w in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    expected = [f"StCd-{1000 + n:05d}" for n in range(workers * per_worker)]
    assert sorted(identifiers) == expected  # unique and gap-free
    assert p95(latencies) <= 2.0 * speed_factor, f"allocation p95 {p95(latencies):.3f}s"
    record_property("allocation_p95_ms", round(p95(latencies) * 1000, 1))
    record_property("submissions", len(latencies))
    record_property("speed_factor", speed_factor)
    print(f"\nallocation p95={p95(latencies) * 1000:.0f}ms over {len(latencies)} submissions")


def test_fifty_concurrent_users_are_served_without_errors(file_app, record_property, speed_factor):
    """NFR-004: 50 concurrent named users (each searching every ~8 s —
    about 6 requests/s in total — staggered) at 20,000 revisions keep the NFR-001
    search target and see no errors — in particular no "database is locked",
    which reads used to hit when every transaction took the SQLite write lock."""
    _seed(file_app, TOTAL_REVISIONS)

    # A slower host gets proportionally longer think time so utilisation, and hence the
    # queueing the test measures, stays the same as on the reference machine.
    users, think_time, actions = 50, 8.0 * speed_factor, 2
    clients = []
    for _ in range(users):  # sign in serially: the per-IP login limit is not under test
        client = file_app.test_client()
        _login(client)
        clients.append(client)

    latencies: list[float] = []
    failures: list[str] = []
    lock = threading.Lock()

    def user_session(n: int):
        try:
            time.sleep(think_time * n / users)  # stagger arrivals
            for q in ("converter", f"code {n}", "StCd-0")[:actions]:
                start = time.perf_counter()
                response = clients[n].get(
                    "/api/v1/status-codes", query_string={"q": q, "page_size": 50, "sort": "title"}
                )
                elapsed = time.perf_counter() - start
                if response.status_code != 200:
                    raise AssertionError(f"search {response.status_code}")
                with lock:
                    latencies.append(elapsed)
                time.sleep(think_time)
        except BaseException as exc:  # noqa: BLE001 - surfaced by the assertion below
            with lock:
                failures.append(f"user {n}: {exc!r}")

    threads = [threading.Thread(target=user_session, args=(n,)) for n in range(users)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert failures == []
    assert len(latencies) == users * actions
    assert p95(latencies) <= 0.5 * speed_factor, f"p95 with 50 users {p95(latencies):.2f}s"
    record_property("p95_ms_50_users", round(p95(latencies) * 1000, 1))
    record_property("speed_factor", speed_factor)
    print(f"\n50 concurrent users: p95={p95(latencies) * 1000:.0f}ms")


def test_reads_are_not_blocked_by_an_open_write_transaction(file_app):
    """WAL read concurrency: a reader proceeds while another connection holds
    the write lock (a long-running submit), instead of timing out."""
    _seed(file_app, 200)
    client = file_app.test_client()
    _login(client)

    import sqlite3

    db_path = file_app.config["SQLALCHEMY_DATABASE_URI"].removeprefix("sqlite:///")
    writer = sqlite3.connect(db_path, isolation_level=None)
    writer.execute("BEGIN IMMEDIATE")  # holds the write lock
    writer.execute("INSERT INTO role (code, label) VALUES ('X_TEST', 'x')")
    try:
        start = time.perf_counter()
        response = client.get("/api/v1/status-codes")
        elapsed = time.perf_counter() - start
    finally:
        writer.execute("ROLLBACK")
        writer.close()
    assert response.status_code == 200
    assert elapsed < 1.0, f"read blocked for {elapsed:.2f}s behind a writer"


def test_export_issues_a_constant_number_of_queries(file_app, record_property):
    """Regression guard for the N+1 problem: exporting 500 revisions must not cost
    ~13 queries per row (it did, and a 5,000-row export took ~4 s instead of <1 s)."""
    from sqlalchemy import event

    _seed(file_app, 500)
    client = file_app.test_client()
    _login(client)

    statements: list[str] = []

    def count(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    with file_app.app_context():
        event.listen(db.engine, "before_cursor_execute", count)
    try:
        response = client.get("/api/v1/exports/released?format=csv")
        working = client.get("/api/v1/exports/working-set?format=csv")
    finally:
        with file_app.app_context():
            event.remove(db.engine, "before_cursor_execute", count)

    assert response.status_code == 200 and working.status_code == 200
    # Authentication, the export query with its eager loads, export job + audit rows, x2.
    record_property("statements_for_two_500_row_exports", len(statements))
    assert len(statements) < 80, f"{len(statements)} SQL statements for two 500-row exports"

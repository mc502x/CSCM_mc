"""I-33 / I-34: the packaging, installer, scheduler units and CI definitions are consistent with
the application they deploy - every command they call exists, every setting they write is read,
the scripts parse, and the production entry point really starts (or refuses to).

Not provable on a developer machine, and said so in docs/14 §4: a real install on a clean
Windows Server / Linux host, systemd's own `verify`, and the PostgreSQL port itself.

TC-051. Requirements: NFR-013, NFR-014.
"""

import configparser
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
import yaml

from tests.system.test_multiprocess import _free_port

APP_DIR = Path(__file__).resolve().parents[2]
REPO = APP_DIR.parent
DEPLOY = APP_DIR / "deploy"
LINUX = DEPLOY / "linux"
WINDOWS = DEPLOY / "windows"
JOB_COMMANDS = {"backup-db", "send-reminders", "audit-verify"}


def _units():
    return sorted([*LINUX.glob("*.service"), *LINUX.glob("*.timer")])


def _unit(path: Path) -> configparser.ConfigParser:
    parser = configparser.ConfigParser(strict=False, interpolation=None)
    parser.optionxform = str  # type: ignore[assignment,method-assign]
    parser.read(path, encoding="utf-8")
    return parser


def test_every_expected_artifact_is_shipped():
    expected = {
        LINUX / name
        for name in (
            "install.sh",
            "cscm.service",
            "cscm-backup.service",
            "cscm-backup.timer",
            "cscm-reminders.service",
            "cscm-reminders.timer",
            "cscm-audit-verify.service",
            "cscm-audit-verify.timer",
            "nginx-cscm.conf",
        )
    } | {
        WINDOWS / name for name in ("install.ps1", "run-server.ps1", "run-job.ps1", "uninstall.ps1")
    }
    assert {p for p in expected if not p.is_file()} == set()


# ------------------------------------------------------------------ systemd units
def test_units_parse_and_have_the_required_sections():
    for path in _units():
        unit = _unit(path)
        assert "Unit" in unit and "Description" in unit["Unit"], path.name
        if path.suffix == ".service":
            assert "Service" in unit and unit["Service"]["ExecStart"], path.name
        else:
            assert unit["Timer"]["OnCalendar"] and unit["Install"]["WantedBy"] == "timers.target"


def test_each_timer_has_a_matching_oneshot_service():
    for timer in LINUX.glob("*.timer"):
        service = timer.with_suffix(".service")
        assert service.is_file(), timer.name
        assert _unit(service)["Service"]["Type"] == "oneshot"


def test_services_call_only_commands_that_exist(app):
    registered = set(app.cli.commands)
    called = set()
    for path in [*LINUX.glob("*.service"), *WINDOWS.glob("install.ps1")]:
        text = path.read_text(encoding="utf-8")
        called |= set(re.findall(r"flask(?:\.exe)?\s+(?:--env-file\s+\S+\s+)?([a-z][a-z-]+)", text))
        called |= set(re.findall(r"-InstallDir `\"\$InstallDir`\" ([a-z][a-z-]+)", text))
    called -= {"db"}  # Flask-Migrate's group, registered by the extension
    assert JOB_COMMANDS <= called
    assert called - set(app.cli.commands) - {"db"} == set(), called - registered


def test_web_service_runs_the_production_entry_point_as_an_unprivileged_user():
    service = _unit(LINUX / "cscm.service")["Service"]
    assert service["User"] == "cscm" and "scripts/serve.py" in service["ExecStart"]
    assert (APP_DIR / "scripts" / "serve.py").is_file()
    assert service["NoNewPrivileges"] == "true" and service["ProtectSystem"] == "strict"


def test_write_paths_of_the_units_cover_what_the_jobs_write():
    env = (LINUX / "install.sh").read_text(encoding="utf-8")
    for needed in ("/var/lib/cscm", "/var/backups/cscm", "/var/log/cscm"):
        assert needed in env
    backup = _unit(LINUX / "cscm-backup.service")["Service"]["ReadWritePaths"]
    assert "/var/backups/cscm" in backup and "/var/lib/cscm" in backup


def test_backup_runs_every_night_and_reminders_on_weekdays():
    assert "*-*-*" in _unit(LINUX / "cscm-backup.timer")["Timer"]["OnCalendar"]
    assert "Mon..Fri" in _unit(LINUX / "cscm-reminders.timer")["Timer"]["OnCalendar"]


# ------------------------------------------------------------------ settings written by the installers
def _config_names() -> set[str]:
    text = "\n".join(
        p.read_text(encoding="utf-8")
        for p in [
            APP_DIR / "app" / "config.py",
            APP_DIR / "scripts" / "serve.py",
            APP_DIR / "app" / "__init__.py",
        ]
    )
    return set(re.findall(r"\b([A-Z][A-Z0-9_]{3,})\b", text))


def test_every_setting_an_installer_writes_is_read_by_the_application():
    known = _config_names() | {"FLASK_APP", "FLASK_ENV", "DATABASE_URL"}
    for path, pattern in (
        (LINUX / "install.sh", r'echo "([A-Z][A-Z0-9_]+)='),
        (WINDOWS / "install.ps1", r'^\s*"([A-Z][A-Z0-9_]+)='),
    ):
        written = set(re.findall(pattern, path.read_text(encoding="utf-8"), re.M))
        assert {
            "SECRET_KEY",
            "AUDIT_HMAC_KEY",
            "MANIFEST_SIGNING_KEY",
            "BACKUP_DIR",
        } <= written, path.name
        assert written - known == set(), (path.name, written - known)


def test_every_setting_in_the_example_file_is_read_by_the_application():
    text = (APP_DIR / ".env.example").read_text(encoding="utf-8")
    names = set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", text, re.M))
    known = _config_names() | {"FLASK_APP", "FLASK_ENV", "DATABASE_URL"}
    assert names - known == set()
    assert {"SECRET_KEY", "CSCM_INSTANCE_PATH", "CSCM_TRUSTED_PROXY", "BACKUP_DIR"} <= names


# ------------------------------------------------------------------ the scripts
def _bash() -> str | None:
    """A working bash: on Windows a bare "bash" can be the WSL stub, so use the one found on PATH
    explicitly and check that it runs."""
    found = shutil.which("bash")
    if found is None:
        return None
    probe = subprocess.run(
        [found, "-c", "echo ok"], capture_output=True, text=True, check=False
    )  # noqa: S603
    return found if probe.stdout.strip() == "ok" else None


@pytest.mark.skipif(_bash() is None, reason="a working bash is not available")
def test_linux_installer_parses_and_its_dry_run_changes_nothing(tmp_path):
    bash = _bash()
    script = LINUX / "install.sh"
    posix = script.as_posix()  # bash does not take backslash paths
    assert subprocess.run([bash, "-n", posix], check=False).returncode == 0  # noqa: S603
    result = subprocess.run(  # noqa: S603
        [bash, posix, "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHON": sys.executable.replace("\\", "/")},
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    for step in (
        "Service account",
        "Virtual environment",
        "Database migrations",
        "First Administrator",
        "systemd units",
    ):
        assert step in out
    assert all(f"{u.name}" in out for u in _units())
    assert "[dry-run]" in out and "WARNING" not in result.stderr
    assert (
        subprocess.run([bash, posix, "--bogus"], capture_output=True, check=False).returncode == 2
    )  # noqa: S603


@pytest.mark.skipif(
    shutil.which("powershell.exe") is None, reason="Windows PowerShell not available"
)
def test_windows_scripts_parse():
    for script in WINDOWS.glob("*.ps1"):
        command = (
            "$e = $null; [void][System.Management.Automation.Language.Parser]::ParseFile("
            f"'{script}', [ref]$null, [ref]$e); if ($e.Count) {{ $e | % {{ $_.Message }}; exit 1 }}"
        )
        result = subprocess.run(  # noqa: S603,S607
            ["powershell.exe", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{script.name}: {result.stdout}"


@pytest.mark.skipif(
    shutil.which("powershell.exe") is None, reason="Windows PowerShell not available"
)
def test_windows_installer_dry_run_lists_every_step_and_creates_nothing(tmp_path):
    target = tmp_path / "CSCM"
    result = subprocess.run(  # noqa: S603,S607
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WINDOWS / "install.ps1"),
            "-DryRun",
            "-InstallDir",
            str(target),
            "-Python",
            sys.executable,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for step in (
        "Directories",
        "Virtual environment",
        "Database migrations",
        "First Administrator",
        "Scheduled tasks",
    ):
        assert step in result.stdout
    for name in ("web server", "nightly backup", "reminders", "audit chain check"):
        assert f"CSCM Tool - {name}" in result.stdout
    assert not target.exists()


# ------------------------------------------------------------------ production entry point
def test_serve_options_follow_the_environment():
    sys.path.insert(0, str(APP_DIR / "scripts"))
    try:
        import serve
    finally:
        sys.path.pop(0)
    default = serve.build_options({})
    assert (
        default["host"] == "127.0.0.1"
        and default["port"] == 8000
        and "trusted_proxy" not in default
    )
    proxied = serve.build_options(
        {"CSCM_PORT": "9001", "CSCM_THREADS": "3", "CSCM_TRUSTED_PROXY": "10.1.2.3"}
    )
    assert proxied["port"] == 9001 and proxied["threads"] == 3
    assert (
        proxied["trusted_proxy"] == "10.1.2.3" and proxied["clear_untrusted_proxy_headers"] is True
    )


def _serve_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    return {
        **os.environ,
        "FLASK_ENV": "production",
        "SECRET_KEY": "s" * 48,
        "DATABASE_URL": f"sqlite:///{(tmp_path / 'prod.db').as_posix()}",
        "CSCM_INSTANCE_PATH": str(tmp_path / "instance"),
        "CSCM_HOST": "127.0.0.1",
        "CSCM_ENV_FILE": str(tmp_path / "absent.env"),
        **extra,
    }


def test_the_production_entry_point_serves_and_reports_its_state(tmp_path):
    from alembic import command
    from alembic.config import Config

    from app import create_app
    from tests.conftest import MIGRATIONS_DIR

    env = _serve_env(tmp_path, BACKUP_DIR=str(tmp_path / "bk"))
    application = create_app("testing", {"SQLALCHEMY_DATABASE_URI": env["DATABASE_URL"]})
    application.instance_path = str(tmp_path / "instance")
    with application.app_context():
        config = Config(str(MIGRATIONS_DIR / "alembic.ini"))
        config.set_main_option("script_location", str(MIGRATIONS_DIR))
        command.upgrade(config, "head")
        from app.extensions import db

        db.session.remove()
        db.engine.dispose()

    port = _free_port()
    process = subprocess.Popen(  # noqa: S603
        [sys.executable, "scripts/serve.py"],
        cwd=APP_DIR,
        env={**env, "CSCM_PORT": str(port)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 40
        body = None
        while time.time() < deadline and body is None:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/v1/health/ready", timeout=3
                ) as response:  # noqa: S310  # nosec B310
                    body = json.loads(response.read())
                    headers = dict(response.headers)
            except OSError:
                time.sleep(0.3)
        assert body is not None, "the server did not come up"
        assert body["status"] == "degraded" and body["checks"]["backup"]["state"] == "missing"
        assert body["checks"]["schema"]["state"] == "ok"
        assert headers.get("Content-Security-Policy")  # the hardening headers are on in production
    finally:
        process.terminate()
        process.wait(timeout=10)


def test_production_refuses_to_start_with_a_weak_key(tmp_path):
    result = subprocess.run(  # noqa: S603
        [sys.executable, "scripts/serve.py"],
        cwd=APP_DIR,
        env=_serve_env(tmp_path, SECRET_KEY="short"),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode != 0 and "SECRET_KEY" in result.stderr


def test_create_admin_can_take_its_answers_from_the_environment(app):
    runner = app.test_cli_runner()
    result = runner.invoke(
        args=["create-admin"],
        env={
            "CSCM_ADMIN_USERNAME": "installer",
            "CSCM_ADMIN_EMAIL": "installer@example.com",
            "CSCM_ADMIN_FULL_NAME": "Installer",
            "CSCM_ADMIN_PASSWORD": "a genuinely long passphrase",
        },
        input="a genuinely long passphrase\n",  # the confirmation prompt, if Click asks for it
    )
    assert result.exit_code == 0, result.output
    assert "Created Administrator 'installer'" in result.output


# ------------------------------------------------------------------ CI definitions
def test_ci_files_parse_and_run_the_ci_script():
    gitea = yaml.safe_load((REPO / ".gitea" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    gitlab = yaml.safe_load((REPO / ".gitlab-ci.yml").read_text(encoding="utf-8"))
    steps = " ".join(str(s.get("run", "")) for s in gitea["jobs"]["verify"]["steps"])
    assert (
        "scripts/ci.py" in steps
        and gitea["jobs"]["verify"]["defaults"]["run"]["working-directory"] == "cscm_tool"
    )
    assert "scripts/ci.py" in " ".join(gitlab["verify"]["script"])
    assert (APP_DIR / "scripts" / "ci.py").is_file()
    assert "docs/24-test-report.md" in gitlab["verify"]["artifacts"]["paths"]


def test_the_ci_script_documents_itself():
    result = subprocess.run(  # noqa: S603
        [sys.executable, "scripts/ci.py", "--help"],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0 and "--fast" in result.stdout


# ------------------------------------------------------------------ PostgreSQL readiness ratchet (I-34)
def test_the_postgres_ratchet_holds():
    sys.path.insert(0, str(APP_DIR / "scripts"))
    try:
        import pg_readiness
    finally:
        sys.path.pop(0)
    assert pg_readiness.check(pg_readiness.scan()) == []


def test_the_ratchet_notices_new_sqlite_specific_code(monkeypatch):
    sys.path.insert(0, str(APP_DIR / "scripts"))
    try:
        import pg_readiness
    finally:
        sys.path.pop(0)
    result = pg_readiness.scan()
    result["counts"]["begin-immediate"] += 1
    result["counts"]["glob"] -= 1
    problems = pg_readiness.check(result)
    assert any(p.startswith("begin-immediate") and "Port note" in p for p in problems)
    assert any(p.startswith("glob") and "progress" in p for p in problems)


def test_every_pattern_in_the_scan_is_classified():
    sys.path.insert(0, str(APP_DIR / "scripts"))
    try:
        import pg_readiness
    finally:
        sys.path.pop(0)
    for pattern in pg_readiness.PATTERNS:
        assert (
            pattern.severity in {"BLOCKER", "PORT", "NOTE"}
            and pattern.port
            and pattern.where in {"schema", "migrations", "app"}
        )
    assert len({p.key for p in pg_readiness.PATTERNS}) == len(pg_readiness.PATTERNS)


def test_non_sqlite_connections_are_left_alone(app):
    """The engine listeners must not touch another driver's connection (docs/07 section 12)."""
    from app import _begin_transaction, _configure_sqlite_connection

    class Foreign:
        executed: list[str] = []

        def cursor(self):  # pragma: no cover - would be a bug if called
            raise AssertionError("PRAGMA issued on a non-SQLite connection")

    _configure_sqlite_connection(Foreign(), None)

    class Conn:
        class dialect:  # noqa: N801
            name = "postgresql"

        def exec_driver_sql(self, sql):  # pragma: no cover
            raise AssertionError("BEGIN IMMEDIATE issued on PostgreSQL")

    _begin_transaction(Conn())

"""The first start on a new machine is one command that works from any folder
(scripts/first_start.py; DEPLOYMENT-QUICKSTART.md). A real run builds a virtual environment and
installs the packages (about a minute), so the test proves the steps with --dry-run.

TC-071. Requirements: NFR-013.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "first_start.py"
STEPS = (
    "1. Python",
    "2. Virtual environment",
    "3. Packages",
    "4. Settings",
    "5. Database",
    "6. First Administrator",
)


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603  (our own script with fixed arguments)
        [sys.executable, str(SCRIPT), "--dry-run", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_every_step_is_listed_from_any_folder_and_nothing_is_changed(tmp_path):
    app_dir = SCRIPT.parents[1]
    before = [(app_dir / name).exists() for name in (".venv", ".env", "instance/cscm.db")]
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    for step in STEPS:
        assert step in result.stdout
    assert "dev_server.py 5001" in result.stdout and "http://localhost:5001" in result.stdout
    assert [(app_dir / name).exists() for name in (".venv", ".env", "instance/cscm.db")] == before
    assert list(tmp_path.iterdir()) == []


def test_the_port_and_the_skipped_administrator_are_honoured(tmp_path):
    result = _run(tmp_path, "--port", "5077", "--no-admin")
    assert result.returncode == 0
    assert "dev_server.py 5077" in result.stdout and "skipped (--no-admin)" in result.stdout


def test_the_script_names_the_application_folder_it_works_in(tmp_path):
    result = _run(tmp_path)
    assert str(SCRIPT.parents[1]) in result.stdout

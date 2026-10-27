"""First start on a new machine: one command, the same in every shell (PowerShell, cmd, Git Bash).

    python scripts/first_start.py            (from cscm_tool/)
    python cscm_tool/scripts/first_start.py  (from the repository root)

It works from whatever folder it is started in and does, in order: check Python, create the
virtual environment `.venv` (never recreates or touches an existing one, so it does not matter
whether it is active), install requirements.txt, create `.env` from `.env.example` (once), create
the database (`flask db upgrade`), create the first Administrator when there is none, and print
the command that starts the application. Running it again is safe: finished steps are skipped.

    --port N       the port printed in the start command (default 5001)
    --no-admin     do not ask for the first Administrator
    --dry-run      print every step, change nothing
"""

import argparse
import os
import subprocess  # nosec B404 - runs the project's own interpreter with fixed arguments
import sys
import venv
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
MINIMUM = (3, 12)


def venv_python(directory: Path) -> Path:
    return directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run(command: list[str], dry_run: bool, env: dict[str, str] | None = None) -> int:
    print("  $", " ".join(str(c) for c in command))
    if dry_run:
        return 0
    return subprocess.call(command, cwd=APP_DIR, env=env)  # nosec B603


def has_users(python: Path) -> bool:
    """True when the database already holds a user (so no first Administrator is needed)."""
    code = (
        "from app import create_app\n"
        "from app.extensions import db\n"
        "app = create_app()\n"
        "with app.app_context():\n"
        "    print(db.session.execute(db.text('SELECT COUNT(*) FROM user')).scalar())\n"
    )
    result = subprocess.run(  # nosec B603
        [str(python), "-c", code], cwd=APP_DIR, capture_output=True, text=True, check=False
    )
    return result.returncode == 0 and result.stdout.strip().splitlines()[-1:] not in ([], ["0"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="First start of the CSCM Tool on this machine.")
    parser.add_argument("--port", type=int, default=5001)
    parser.add_argument("--no-admin", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    dry = args.dry_run

    print(f"CSCM Tool - first start{' (dry run, nothing is changed)' if dry else ''}")
    print(f"Application folder: {APP_DIR}")

    print("1. Python")
    if sys.version_info < MINIMUM:
        print(
            f"   Python {MINIMUM[0]}.{MINIMUM[1]} or newer is needed; "
            f"this is {sys.version.split()[0]}."
        )
        return 1
    print(f"   Python {sys.version.split()[0]}")

    print("2. Virtual environment (.venv)")
    env_dir = APP_DIR / ".venv"
    python = venv_python(env_dir)
    if python.is_file():
        print("   exists, kept as it is")
    else:
        print("   creating")
        if not dry:
            venv.EnvBuilder(with_pip=True).create(env_dir)

    print("3. Packages (requirements.txt)")
    if run([str(python), "-m", "pip", "install", "-q", "-r", "requirements.txt"], dry):
        print(
            "   The packages could not be installed (no network? set PIP_INDEX_URL to your mirror)."
        )
        return 1

    print("4. Settings (.env)")
    env_file, example = APP_DIR / ".env", APP_DIR / ".env.example"
    if env_file.exists():
        print("   exists, kept as it is")
    else:
        print("   created from .env.example")
        if not dry:
            env_file.write_bytes(example.read_bytes())

    print("5. Database (flask db upgrade)")
    if run([str(python), "-m", "flask", "db", "upgrade"], dry):
        print("   The database could not be created; the message above says why.")
        return 1
    print("   loading the initial mapping (only into an empty one)")
    if run([str(python), "-m", "flask", "mapping-seed"], dry):
        print("   The mapping was not loaded; an Administrator can load it from the Mapping page.")

    print("6. First Administrator")
    if args.no_admin:
        print("   skipped (--no-admin)")
    elif not dry and has_users(python):
        print("   the database already has users")
    else:
        print("   answer the questions (name, e-mail, password)")
        if run([str(python), "-m", "flask", "create-admin"], dry):
            print("   The Administrator was not created; run the step again.")
            return 1

    shown = python.relative_to(APP_DIR)
    print("\nDone. Start the application with:")
    print(f"    cd {APP_DIR}")
    print(f"    {shown} dev_server.py {args.port}")
    print(f"then open http://localhost:{args.port}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

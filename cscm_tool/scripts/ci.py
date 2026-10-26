"""One command for the CI server (and for a developer before pushing).

    python scripts/ci.py                 # the full pipeline
    python scripts/ci.py --fast          # tests only, stop at the first failure
    python scripts/ci.py --offline       # as the full pipeline; pip-audit reports "not run"
    python scripts/ci.py --order shuffle:3
    python scripts/ci.py --pdf           # as the full pipeline, then the four release PDFs (FR-185)
    python scripts/ci.py --showcase      # ... and the two design showcase decks (FR-186; needs Edge or Chrome)

The full pipeline is `scripts/generate_test_report.py` (pytest with coverage, then black, ruff,
mypy, bandit, pip-audit; it rewrites docs/24-test-report.md and the run history) followed by
`scripts/pg_readiness.py --check` (the PostgreSQL-readiness ratchet, I-34). The exit status is
non-zero when any test fails, any gate fails or the ratchet is exceeded. A gate that could not run
(pip-audit without network access) is reported as "not run" and does not fail the build; the CI
job summary shows it, so it cannot be mistaken for a pass.

Docs: docs/14-deployment-architecture.md §4, docs/15-development-standards.md §7."""

import argparse
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]


def run(*args: str) -> int:
    print("+", " ".join(args), flush=True)
    return subprocess.run(args, cwd=APP_DIR, check=False).returncode  # noqa: S603  # nosec B603


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--fast", action="store_true", help="tests only, stop at first failure")
    parser.add_argument(
        "--offline", action="store_true", help="same as the full run (pip-audit degrades itself)"
    )
    parser.add_argument("--order", default="file", help="file | reverse | shuffle[:SEED]")
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="after a green pipeline build the four documents as PDF into releases/v<version>/",
    )
    parser.add_argument(
        "--showcase",
        action="store_true",
        help="after a green pipeline build the two design showcase decks into releases/v<version>/",
    )
    args = parser.parse_args(argv)
    py = sys.executable

    if args.fast:
        return run(
            py, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "-m", "not performance"
        )

    status = run(py, "scripts/generate_test_report.py", "--order", args.order)
    ratchet = run(py, "scripts/pg_readiness.py", "--check")
    if status or ratchet:
        return 1
    code = run(py, "scripts/build_docs_pdf.py") if args.pdf else 0
    if code == 0 and args.showcase:
        code = run(py, "scripts/build_showcase.py", "--pdf")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

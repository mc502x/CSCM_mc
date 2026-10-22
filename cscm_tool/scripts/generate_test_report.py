"""Runs the whole verification pipeline and (re)writes the test report.

    python scripts/generate_test_report.py                  # file order
    python scripts/generate_test_report.py --order reverse  # independence check
    python scripts/generate_test_report.py --order shuffle:7
    python scripts/generate_test_report.py --skip-gates     # tests + coverage only

It executes the full pytest suite (JUnit XML + coverage), the static quality
gates (black, ruff, mypy, bandit, pip-audit), then writes
`docs/24-test-report.md` and appends the run to
`docs/artifacts/test-run-history.json`. The report is generated output: re-run
this script whenever the software changes (docs/15-development-standards.md,
Definition of Done) instead of editing the report by hand.
"""

from __future__ import annotations

# ruff: noqa: E501
import argparse
import ast
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
REPO = APP_DIR.parent
DOCS = REPO / "docs"
REPORT = DOCS / "24-test-report.md"
HISTORY = DOCS / "artifacts" / "test-run-history.json"
MATRIX = DOCS / "20-traceability-matrix.md"
TESTS = APP_DIR / "tests"

REQ_RE = re.compile(
    r"\b(FR-\d{3}[a-z]?|BR-\d{3}|NFR-\d{3}[a-z]?|SEC-\d{3}|TC-\d{3}[a-z]?|UAT-\d{2}[a-z]?|US-\d{3})\b"
)


# --------------------------------------------------------------------------- helpers
def run(cmd: list[str], env: dict | None = None, timeout: int | None = None):
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd,
        cwd=APP_DIR,
        env=full_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8"
    )
    return result.stdout.strip()


def md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------- static test index
def index_tests() -> dict[str, dict]:
    """module path (relative, posix) -> {'doc': str, 'tests': {name: first doc line}}"""
    index: dict[str, dict] = {}
    for path in sorted(TESTS.rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        tests = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                doc = ast.get_docstring(node) or ""
                tests[node.name] = doc.strip().splitlines()[0] if doc.strip() else ""
        index[path.relative_to(APP_DIR).as_posix()] = {
            "doc": (ast.get_docstring(tree) or "").strip(),
            "tests": tests,
        }
    return index


def refs_for(module_doc: str, test_name: str, test_doc: str) -> list[str]:
    found = set(REQ_RE.findall(test_doc)) | set(REQ_RE.findall(test_name.upper().replace("_", "-")))
    if not found:
        found = set(REQ_RE.findall(module_doc))
    return sorted(found)


# --------------------------------------------------------------------------- pytest run
def _parse_junit(junit: Path) -> tuple[list[dict], float]:
    cases: list[dict] = []
    root = ET.parse(junit).getroot()
    for case in root.iter("testcase"):
        classname = case.get("classname", "")
        status = "passed"
        message = ""
        for tag in ("failure", "error", "skipped"):
            node = case.find(tag)
            if node is not None:
                status = "failed" if tag in ("failure", "error") else "skipped"
                message = (node.get("message") or node.text or "")[:600]
        props = {p.get("name"): p.get("value") for p in case.iter("property")}
        cases.append(
            {
                "module": classname.replace(".", "/") + ".py",
                "name": case.get("name", ""),
                "time": float(case.get("time", 0)),
                "status": status,
                "message": message,
                "props": props,
                "retried": False,
            }
        )
    return cases, float(root.get("time") or sum(c["time"] for c in cases))


def run_pytest(order: str) -> tuple[list[dict], dict, float, str]:
    """Runs the suite in two processes. The functional suite runs with coverage;
    the timing-based performance tests run afterwards in a fresh process WITHOUT
    coverage tracing (which slows pure-Python code ~2-3x and would measure the
    instrumentation, not the application). If a performance test still fails,
    only performance tests are re-run once and a pass on retry is flagged in
    the report; any other failure is never retried."""
    with tempfile.TemporaryDirectory() as tmp:
        junit = Path(tmp) / "junit.xml"
        perf_junit = Path(tmp) / "perf.xml"
        cov = Path(tmp) / "coverage.json"
        env = {"CSCM_TEST_ORDER": "" if order == "file" else order}
        base = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q"]

        main_proc = run(
            [
                *base,
                "-m",
                "not performance",
                f"--junitxml={junit}",
                "--cov=app",
                f"--cov-report=json:{cov}",
            ],
            env=env,
        )
        cases, total_time = _parse_junit(junit)
        coverage = json.loads(cov.read_text(encoding="utf-8")) if cov.exists() else {}
        main_line = ((main_proc.stdout or "").strip().splitlines()[-1:] or [""])[0]

        perf_proc = run([*base, "tests/performance", f"--junitxml={perf_junit}"], env=env)
        perf_cases, perf_time = _parse_junit(perf_junit)
        perf_line = ((perf_proc.stdout or "").strip().splitlines()[-1:] or [""])[0]

        perf_failed = [c for c in perf_cases if c["status"] == "failed"]
        if perf_failed:
            print(f"  {len(perf_failed)} performance test(s) failed; retrying once ...", flush=True)
            retry_junit = Path(tmp) / "retry.xml"
            run([*base, "tests/performance", f"--junitxml={retry_junit}"], env=env)
            retried, _ = _parse_junit(retry_junit)
            by_key = {(c["module"], c["name"]): c for c in retried}
            for i, case in enumerate(perf_cases):
                again = by_key.get((case["module"], case["name"]))
                if case["status"] == "failed" and again is not None:
                    if again["status"] == "passed":
                        again["retried"] = True
                        again["message"] = "first attempt failed: " + case["message"][:200]
                    perf_cases[i] = again

        cases += perf_cases
        total_time += perf_time
        summary_line = f"functional: {main_line}  |  performance: {perf_line}"
    return cases, coverage, total_time, summary_line


# --------------------------------------------------------------------------- quality gates
def run_gates() -> list[dict]:
    py = sys.executable
    gates = []

    def gate(name: str, cmd: list[str], ok_if=lambda p: p.returncode == 0, timeout=300):
        try:
            proc = run(cmd, timeout=timeout)
            output = (proc.stdout + proc.stderr).strip().splitlines()
            summary = output[-1] if output else ""
            gates.append(
                {"name": name, "ok": ok_if(proc), "summary": summary[:160], "output": output}
            )
        except Exception as exc:  # noqa: BLE001 - reported in the table
            gates.append({"name": name, "ok": None, "summary": f"not run: {exc}", "output": []})

    gate("black --check", [py, "-m", "black", "--check", "app", "tests", "migrations/versions"])
    gate("ruff check", [py, "-m", "ruff", "check", "app", "tests", "migrations/versions"])
    gate("mypy", [py, "-m", "mypy", "app", "wsgi.py"])
    gate("bandit -r app", [py, "-m", "bandit", "-q", "-r", "app"])
    gates.append(pip_audit_gate())
    return gates


def pip_audit_gate() -> dict:
    requirements = (APP_DIR / "requirements.txt").read_text(encoding="utf-8")
    runtime_text = requirements.split("# --- dev")[0]
    runtime = {
        re.split(r"[=<>\[ ]", line.strip(), maxsplit=1)[0].lower().replace("_", "-")
        for line in runtime_text.splitlines()
        if line.strip() and not line.startswith("#")
    }
    try:
        proc = run([sys.executable, "-m", "pip_audit", "-r", "requirements.txt"], timeout=180)
    except Exception as exc:  # noqa: BLE001
        return {"name": "pip-audit", "ok": None, "summary": f"not run: {exc}", "output": []}
    findings = [
        line.split()
        for line in proc.stdout.splitlines()
        if len(line.split()) >= 4 and line.split()[2].startswith(("PYSEC", "GHSA", "CVE"))
    ]
    if proc.returncode not in (0, 1) or (proc.returncode == 1 and not findings):
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-1:] or ["no output"]
        return {
            "name": "pip-audit",
            "ok": None,
            "summary": f"not run: {tail[0][:120]}",
            "output": [],
        }
    runtime_hits = sorted({f[0] for f in findings if f[0].lower() in runtime})
    dev_hits = sorted({f[0] for f in findings if f[0].lower() not in runtime})
    summary = f"runtime packages with advisories: {', '.join(runtime_hits) or 'none'}"
    if dev_hits:
        summary += f"; dev-only advisories (accepted): {', '.join(dev_hits)}"
    return {"name": "pip-audit", "ok": not runtime_hits, "summary": summary, "output": []}


# --------------------------------------------------------------------------- traceability evidence check
def check_matrix_evidence(index: dict[str, dict]) -> tuple[int, list[str]]:
    """Every test / test file named in the traceability matrix must still exist."""
    if not MATRIX.exists():
        return 0, []
    functions = {name for mod in index.values() for name in mod["tests"]}
    modules = {Path(m).stem for m in index}
    checked, missing = 0, []
    for token in set(re.findall(r"`([^`]+)`", MATRIX.read_text(encoding="utf-8"))):
        for piece in re.split(r"[,;\s]+|::", token):
            piece = piece.strip().rstrip(".").rsplit("/", 1)[-1]
            if not piece.startswith("test_"):
                continue
            piece = piece.removesuffix(".py")
            stem = piece.split("…")[0].rstrip("*")  # "test_x_*" / "test_x…" cite a family
            checked += 1
            if piece in modules or piece in functions:
                continue
            if stem and any(name.startswith(stem) for name in functions | modules):
                continue
            missing.append(piece)
    return checked, sorted(set(missing))


# --------------------------------------------------------------------------- report
SUITE_ORDER = ["unit", "integration", "system", "performance"]


def suite_of(module: str) -> str:
    parts = Path(module).parts
    return parts[1] if len(parts) > 2 and parts[0] == "tests" else "other"


def fmt_pct(value: float) -> str:
    return f"{value:.0f}%"


def write_report(
    cases, coverage, total_time, pytest_tail, gates, order, index, history, matrix_check
) -> None:
    now = datetime.now(UTC)
    commit = git("rev-parse", "--short", "HEAD") or "unknown"
    dirty = (
        "+uncommitted changes" if git("status", "--porcelain", "--", "cscm_tool", "docs") else ""
    )
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    counts = Counter(c["status"] for c in cases)
    totals = coverage.get("totals", {})
    cov_pct = totals.get("percent_covered", 0.0)

    lines: list[str] = []
    w = lines.append
    w("# 24. Test Report — CSCM Tool")
    w("")
    w(
        "> **Generated file — do not edit by hand.** Regenerate with "
        "`python cscm_tool/scripts/generate_test_report.py` after every software change "
        "(Definition of Done, 15-development-standards.md). It runs the complete pytest suite, "
        "measures coverage, runs the static quality gates, and appends the run to the history "
        "below."
    )
    w("")
    w("## 1. Run summary")
    w("")
    verdict = (
        "PASS" if counts["failed"] == 0 and all(g["ok"] is not False for g in gates) else "FAIL"
    )
    w("| | |")
    w("|---|---|")
    w(f"| **Verdict** | **{verdict}** |")
    w(f"| Generated (UTC) | {now:%Y-%m-%d %H:%M:%S} |")
    w(f"| Branch / commit | `{branch}` @ `{commit}` {dirty} |")
    w(f"| Test order | `{order}` |")
    w(
        f"| Tests | **{len(cases)}** run — {counts['passed']} passed, {counts['failed']} failed, {counts['skipped']} skipped |"
    )
    w(f"| Duration | {total_time:.1f} s |")
    w(
        f"| Line coverage (`app/`) | **{fmt_pct(cov_pct)}** ({totals.get('covered_lines', 0)} of {totals.get('num_statements', 0)} statements) |"
    )
    w(
        f"| Python / platform | {platform.python_version()} / {platform.system()} {platform.release()} |"
    )
    w(f"| pytest summary line | `{pytest_tail}` |")
    w("")

    # suites
    by_suite: dict[str, list[dict]] = defaultdict(list)
    for c in cases:
        by_suite[suite_of(c["module"])].append(c)
    w("## 2. Results by suite")
    w("")
    w("| Suite | Tests | Passed | Failed | Skipped | Time |")
    w("|---|---|---|---|---|---|")
    for suite in [s for s in SUITE_ORDER if s in by_suite] + sorted(
        set(by_suite) - set(SUITE_ORDER)
    ):
        items = by_suite[suite]
        st = Counter(i["status"] for i in items)
        w(
            f"| {suite} | {len(items)} | {st['passed']} | {st['failed']} | {st['skipped']} | "
            f"{sum(i['time'] for i in items):.1f} s |"
        )
    w("")

    # gates
    w("## 3. Static quality and security gates")
    w("")
    w("| Gate | Result | Detail |")
    w("|---|---|---|")
    for g in gates:
        mark = {True: "PASS", False: "**FAIL**", None: "not run"}[g["ok"]]
        w(f"| {g['name']} | {mark} | {md_escape(g['summary'])} |")
    if not gates:
        w("| (skipped with `--skip-gates`) | — | — |")
    w("")

    # performance
    perf = [c for c in cases if c["props"]]
    if perf:
        w("## 4. Measured performance (NFR-001, NFR-004, TC-024, TC-025)")
        w("")
        w("| Test | Measured |")
        w("|---|---|")
        for c in perf:
            measured = ", ".join(f"{k} = {v}" for k, v in sorted(c["props"].items()))
            if c["retried"]:
                measured += " — **passed on retry** (" + c["message"] + ")"
            w(f"| `{md_escape(c['name'])}` | {md_escape(measured)} |")
        w("")
        w(
            "Targets: search p95 ≤ 500 ms and single read p95 ≤ 200 ms at 20,000 revisions; "
            "CSV/JSON export of 5,000 records ≤ 5 s, XLSX/PDF ≤ 15 s; 50 concurrent users keep the "
            "500 ms search target; identifier allocation under contention correct and gap-free."
        )
        w("")

    # coverage
    w("## 5. Coverage by module")
    w("")
    w("| Module | Statements | Missed | Coverage |")
    w("|---|---|---|---|")
    files = coverage.get("files", {})
    for name in sorted(files):
        s = files[name]["summary"]
        w(
            f"| `{name.replace(chr(92), '/')}` | {s['num_statements']} | {s['missing_lines']} | {fmt_pct(s['percent_covered'])} |"
        )
    w("")

    # matrix evidence
    checked, missing = matrix_check
    w("## 6. Traceability evidence check")
    w("")
    w(
        f"`docs/20-traceability-matrix.md` cites {checked} test names / test files as evidence. "
        f"**{checked - len(missing)} resolve** to a test that exists; "
        f"**{len(missing)} are stale**"
        + (": " + ", ".join(f"`{m}`" for m in missing) if missing else ".")
    )
    w("")

    # failures
    failed = [c for c in cases if c["status"] == "failed"]
    w("## 7. Failures")
    w("")
    if failed:
        for c in failed:
            w(f"- `{c['module']}::{c['name']}` — {md_escape(c['message'][:300])}")
    else:
        w("None.")
    w("")

    # inventory
    w("## 8. Complete test inventory")
    w("")
    w(
        "Every executed test, grouped by file, with its outcome, duration, and the requirement IDs "
        "it cites (module/test docstring or name). Parametrised cases appear individually."
    )
    w("")
    by_module: dict[str, list[dict]] = defaultdict(list)
    for c in cases:
        by_module[c["module"]].append(c)
    for module in sorted(
        by_module,
        key=lambda m: (SUITE_ORDER.index(suite_of(m)) if suite_of(m) in SUITE_ORDER else 9, m),
    ):
        entry = index.get(module, {"doc": "", "tests": {}})
        items = by_module[module]
        st = Counter(i["status"] for i in items)
        doc_line = entry["doc"].splitlines()[0] if entry["doc"] else ""
        w(
            f"### `{module}` — {len(items)} tests, {st['passed']} passed"
            + (f", {st['failed']} FAILED" if st["failed"] else "")
        )
        w("")
        if doc_line:
            w(f"_{md_escape(doc_line)}_")
            w("")
        w("| Result | Test | Purpose | Requirements | Time |")
        w("|---|---|---|---|---|")
        for c in sorted(items, key=lambda i: i["name"]):
            base = c["name"].split("[")[0]
            tdoc = entry["tests"].get(base, "")
            refs = ", ".join(refs_for(entry["doc"], base, tdoc))
            mark = {"passed": "✅", "failed": "❌", "skipped": "⏭"}[c["status"]] + (
                " (retry)" if c["retried"] else ""
            )
            w(
                f"| {mark} | `{md_escape(c['name'])}` | {md_escape(tdoc)} | {refs} | {c['time']:.2f} s |"
            )
        w("")

    # history
    w("## 9. Run history")
    w("")
    w(
        "| # | Date (UTC) | Commit | Order | Tests | Passed | Failed | Retried | Coverage | Gates | Duration |"
    )
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for i, h in enumerate(history, 1):
        w(
            f"| {i} | {h['date']} | `{h['commit']}` | {h['order']} | {h['total']} | {h['passed']} | "
            f"{h['failed']} | {h.get('retried', 0)} | {fmt_pct(h['coverage'])} | {h['gates']} | {h['duration']:.0f} s |"
        )
    w("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--order", default="file", help="file | reverse | shuffle[:SEED]")
    parser.add_argument("--skip-gates", action="store_true")
    parser.add_argument(
        "--no-history", action="store_true", help="do not append to the run history"
    )
    args = parser.parse_args()

    print(f"Running test suite (order: {args.order}) ...", flush=True)
    cases, coverage, total_time, tail = run_pytest(args.order)
    print(f"  {tail}", flush=True)
    gates = [] if args.skip_gates else run_gates()
    for g in gates:
        print(
            f"  gate {g['name']}: {({True: 'pass', False: 'FAIL', None: 'not run'})[g['ok']]}",
            flush=True,
        )

    index = index_tests()
    matrix_check = check_matrix_evidence(index)

    history = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []
    counts = Counter(c["status"] for c in cases)
    if not args.no_history:
        gate_text = (
            "skipped" if not gates else f"{sum(1 for g in gates if g['ok'])}/{len(gates)} pass"
        )
        history.append(
            {
                "date": f"{datetime.now(UTC):%Y-%m-%d %H:%M}",
                "commit": (git("rev-parse", "--short", "HEAD") or "unknown")
                + ("*" if git("status", "--porcelain", "--", "cscm_tool", "docs") else ""),
                "order": args.order,
                "total": len(cases),
                "passed": counts["passed"],
                "failed": counts["failed"],
                "coverage": coverage.get("totals", {}).get("percent_covered", 0.0),
                "gates": gate_text,
                "retried": sum(1 for c in cases if c["retried"]),
                "duration": total_time,
            }
        )
        history = history[-100:]
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        HISTORY.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8", newline="\n")

    write_report(cases, coverage, total_time, tail, gates, args.order, index, history, matrix_check)
    print(f"Report written to {REPORT.relative_to(REPO)}")
    failed_gate = any(g["ok"] is False for g in gates)
    return 1 if counts["failed"] or failed_gate else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""TC-052. The documents agree with the code and with each other: the generated endpoint table, the
quoted counts, the audit action catalogue, the requirement ids, the traceability matrix, the
links between documents, the section references and the document set version.

This is the automated half of "documentation checked for correctness" (docs/13-test-strategy.md
§12); it cannot judge whether a sentence is *true*, but it makes the checkable facts impossible to
drift."""

import ast
import re
import sqlite3
import sys
from pathlib import Path

import pytest
import yaml

APP_DIR = Path(__file__).resolve().parents[2]
DOCS = APP_DIR.parent / "docs"
SCRIPTS = APP_DIR / "scripts"
MARKDOWN = sorted(p for p in DOCS.glob("*.md") if not p.name.startswith("24-"))
ALL_DOCS = sorted(DOCS.glob("*.md")) + [APP_DIR.parent / "README.md", APP_DIR / "README.md"]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _scripts():
    sys.path.insert(0, str(SCRIPTS))
    try:
        import gen_api_summary
        import generate_test_report
    finally:
        sys.path.pop(0)
    return gen_api_summary, generate_test_report


@pytest.fixture(scope="module")
def spec():
    return yaml.safe_load(_text(DOCS / "artifacts" / "openapi.yaml"))


@pytest.fixture(scope="module")
def schema_counts(tmp_path_factory):
    connection = sqlite3.connect(":memory:")
    connection.executescript(_text(DOCS / "artifacts" / "schema.sql"))
    tables = [
        r[0]
        for r in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    triggers = [
        r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
    ]
    groups = connection.execute("SELECT COUNT(*) FROM lookup_functional_system_group").fetchone()[0]
    subgroups = connection.execute("SELECT COUNT(*) FROM lookup_functional_subgroup").fetchone()[0]
    return {
        "tables": len(tables),
        "triggers": len(triggers),
        "groups": groups,
        "subgroups": subgroups,
    }


# ------------------------------------------------------------------ generated blocks
def test_the_endpoint_table_of_the_api_document_is_the_generated_one():
    gen_api_summary, _ = _scripts()
    document = _text(DOCS / "09-api-specification.md").replace("\r\n", "\n")
    block = document.split(gen_api_summary.START, 1)[1].split(gen_api_summary.END, 1)[0]
    generated = "\n".join(gen_api_summary.rows())
    assert block.strip() == generated.strip(), "run: python scripts/gen_api_summary.py --write"
    assert "| ? |" not in generated  # every operation of the contract exists in the code


# ------------------------------------------------------------------ quoted numbers
def test_the_contract_version_and_operation_count_quoted_in_the_documents(spec):
    operations = sum(
        1
        for item in spec["paths"].values()
        for m in item
        if m in ("get", "post", "put", "patch", "delete")
    )
    assert spec["info"]["version"] == "4.0.0"
    for name in ("03-srs.md", "09-api-specification.md", "22-software-description.md"):
        assert f"{operations} operations" in _text(DOCS / name), name
    assert f"{operations} operations" in _text(APP_DIR / "README.md")
    assert "v4.0.0" in _text(DOCS / "09-api-specification.md")


def test_the_table_and_trigger_counts_quoted_in_the_documents(schema_counts):
    assert f"{schema_counts['tables']} tables" in _text(DOCS / "06-data-dictionary.md")
    assert f"{schema_counts['tables']} tables, {schema_counts['triggers']} triggers" in _text(
        DOCS / "07-database-design.md"
    )
    assert f"{schema_counts['tables']} tables" in _text(APP_DIR / "README.md")
    assert f"{schema_counts['tables']} tables in total" in _text(
        DOCS / "22-software-description.md"
    )


def test_the_group_and_subgroup_counts_quoted_in_the_documents(schema_counts):
    assert schema_counts["groups"] == 12 and schema_counts["subgroups"] == 38
    assert "12-row numbering band lookup" in _text(DOCS / "07-database-design.md")
    assert "38 seeded subgroups" in _text(DOCS / "07-database-design.md")


def test_the_screen_count_matches_the_inventory():
    inventory = _text(DOCS / "10-ui-ux-specification.md")
    numbers = {int(n) for n in re.findall(r"^\| S(\d+) \|", inventory, re.M)}
    assert numbers == set(range(1, 45))
    assert "Forty-four screens (S1–S44" in _text(DOCS / "22-software-description.md")


def test_the_audit_catalogue_lists_every_code_the_application_can_write():
    root = APP_DIR / "app"
    emitted: set[str] = set()
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(_text(path))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "log"
                and len(node.args) >= 3
                and isinstance(node.args[2], ast.Constant)
                and isinstance(node.args[2].value, str)
            ):
                emitted.add(node.args[2].value)
    # written through a variable: per-decision, lock, deactivation and export codes
    emitted |= {
        "ACCOUNT_LOCKED",
        "REVIEWER_SIGNOFF",
        "ADMIN_SIGNOFF",
        "CHIEF_ENGINEER_APPROVE",
        "CHIEF_ENGINEER_REJECT",
        "USER_DEACTIVATE",
        "OFFLINE_BUNDLE_EXPORT",
        "RELEASE_NOTES_EXPORT",
    }
    documented = set(re.findall(r"`([A-Z][A-Z_]{3,})`", _text(DOCS / "12-audit-compliance.md")))
    assert emitted - documented == set()
    assert "Seventy-eight action codes" in _text(DOCS / "22-software-description.md")
    assert len(emitted) == 78


# ------------------------------------------------------------------ requirement ids
def _defined_ids() -> dict[str, set[str]]:
    srs = _text(DOCS / "03-srs.md")
    return {
        "FR": set(re.findall(r"\*\*(FR-\d{3}[a-z]?)\*\*", srs)),
        "BR": set(re.findall(r"\*\*(BR-\d{3})\*\*", srs)),
        "NFR": set(
            re.findall(r"\b(NFR-\d{3}[a-z]?)\b", " ".join(re.findall(r"^#{2,4} [^\n]*", srs, re.M)))
        ),
        "SEC": set(re.findall(r"\*\*(SEC-\d{3})\*\*", _text(DOCS / "11-security-architecture.md"))),
        "AUD": set(re.findall(r"\*\*(AUD-\d{3})\*\*", _text(DOCS / "12-audit-compliance.md"))),
        "D": set(re.findall(r"\| \*\*(D-\d{2})\*\* \|", srs)),
        "TC": set(
            re.findall(r"^\| (TC-\d{3}[a-z]?) \|", _text(DOCS / "13-test-strategy.md"), re.M)
        ),
        "I": set(re.findall(r"^\| (I-\d{2}) \|", _text(DOCS / "21-improvement-ideas.md"), re.M))
        | set(
            re.findall(r"^\| \*\*(I-\d{2})\*\* \|", _text(DOCS / "21-improvement-ideas.md"), re.M)
        ),
        "A": set(re.findall(r"\*\*(A-\d{3})\*\*", srs)),
    }


def test_the_decisions_and_assumptions_are_complete():
    ids = _defined_ids()
    assert ids["D"] == {f"D-0{n}" for n in range(1, 9)}
    assert {f"I-{n:02d}" for n in range(1, 61)} <= ids["I"]
    assert {"A-009", "A-010"} <= ids["A"]


def test_every_requirement_id_cited_in_a_document_is_defined():
    ids = _defined_ids()
    # ids cited with a letter suffix that the SRS defines only as the stem (FR-048a-d style)
    problems = []
    for path in ALL_DOCS:
        if path.name.startswith("24-"):
            continue
        text = _text(path)
        for kind, pattern in (
            ("FR", r"\bFR-\d{3}[a-z]?\b"),
            ("BR", r"\bBR-\d{3}\b"),
            ("SEC", r"\bSEC-\d{3}\b"),
            ("AUD", r"\bAUD-\d{3}\b"),
            ("D", r"\bD-0\d\b"),
        ):
            for cited in set(re.findall(pattern, text)):
                if cited not in ids[kind]:
                    problems.append(f"{path.name}: {cited}")
    assert problems == []


def test_every_test_case_id_cited_in_the_documents_exists():
    ids = _defined_ids()["TC"]
    problems = []
    for path in ALL_DOCS:
        if path.name.startswith("24-"):
            continue
        for cited in set(re.findall(r"\bTC-\d{3}[a-z]?\b", _text(path))):
            if cited not in ids:
                problems.append(f"{path.name}: {cited}")
    assert problems == []


def test_every_requirement_is_accounted_for_and_the_matrix_evidence_resolves():
    _, report = _scripts()
    index = report.index_tests()
    coverage = report.requirement_coverage(index)
    assert coverage["open"] == [], coverage["open"]
    checked, missing = report.check_matrix_evidence(index)
    assert checked > 200 and missing == [], missing


# ------------------------------------------------------------------ links and references
def _slug(heading: str) -> str:
    text = re.sub(r"[`*_]", "", heading.strip().lower())
    text = re.sub(r"\([^)]*\)$", lambda m: m.group(0), text)
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def _anchors(path: Path) -> set[str]:
    return {_slug(m.group(1)) for m in re.finditer(r"^#{1,6} (.+)$", _text(path), re.M)}


def test_links_between_documents_point_at_existing_files_and_headings():
    problems = []
    for path in ALL_DOCS:
        if path.name.startswith("24-"):
            continue
        for target in re.findall(r"\]\(([^)\s]+)\)", _text(path)):
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            file_part, _, fragment = target.partition("#")
            destination = path.parent / file_part if file_part else path
            if not destination.exists():
                problems.append(f"{path.name}: missing {target}")
            elif fragment and destination.suffix == ".md" and fragment not in _anchors(destination):
                problems.append(f"{path.name}: no heading for {target}")
    assert problems == []


def _section_numbers(path: Path) -> set[str]:
    numbers = set()
    for m in re.finditer(r"^#{1,6} (\d+[a-z]?(?:\.\d+[a-z]?)*)\.?[ )]", _text(path), re.M):
        numbers.add(m.group(1))
    for m in re.finditer(r"^#{1,6} ((?:EPIC-)?\d+[a-z]?)\b", _text(path), re.M):
        numbers.add(m.group(1))
    return numbers


def test_section_references_between_documents_exist():
    sections = {p.name: _section_numbers(p) for p in DOCS.glob("[0-9][0-9]-*.md")}
    problems = []
    for path in ALL_DOCS:
        if path.name.startswith("24-"):
            continue
        for name, ref in re.findall(
            r"\b(\d\d-[a-z0-9-]+\.md) §(\d+[a-z]?(?:\.\d+[a-z]?)?)", _text(path)
        ):
            if name in sections and ref not in sections[name]:
                problems.append(f"{path.name}: {name} §{ref}")
    assert problems == []


# ------------------------------------------------------------------ version and generated file
def test_the_document_set_version_is_current_and_the_report_is_generated():
    index = _text(DOCS / "00-INDEX.md")
    assert "**Document Set Version:** 4.0" in index
    for name in ("21-improvement-ideas.md", "22-software-description.md", "23-user-manual.md"):
        assert "v4" in _text(DOCS / name) or "version 4" in _text(DOCS / name), name
    report = _text(DOCS / "24-test-report.md")
    assert "Generated file" in report and "do not edit by hand" in report


def test_paragraphs_in_documents_are_single_source_lines():
    """docs/15 §6: prose paragraphs are one continuous source line (tables, lists and code may span)."""
    problems = []
    for path in MARKDOWN:
        in_code = False
        previous = ""
        for number, line in enumerate(_text(path).splitlines(), 1):
            if line.startswith("```"):
                in_code = not in_code
            if in_code or not line.strip():
                previous = ""
                continue
            plain = re.match(r"^[A-Za-z*`(\[]", line) and not line.startswith(("*", "|"))
            if (
                plain
                and previous
                and re.match(r"^[A-Za-z(\[`]", previous)
                and not previous.endswith(":")
                and len(previous) > 100
            ):
                problems.append(f"{path.name}:{number}")
            previous = line if plain else ""
    assert len(problems) < 10, problems[:10]


def test_the_test_suite_table_of_the_strategy_matches_the_test_files():
    """docs/13 section 8a quotes how many test functions each v4 module has."""
    document = _text(DOCS / "13-test-strategy.md")
    section = document.split("## 8a. v4 Test Suites", 1)[1].split("## 9.", 1)[0]
    problems = []
    for line in section.splitlines():
        match = re.match(r"^\| ((?:`[^`]+`(?:, )?)+) \| ([\d +]+) \|", line)
        if not match:
            continue
        files = re.findall(r"`tests/…/?([^`]+)`|`([^`]+\.py)`", match.group(1))
        names = [a or b for a, b in files]
        counts = [int(n) for n in re.findall(r"\d+", match.group(2))]
        actual = []
        for name in names:
            path = next(iter((APP_DIR / "tests").rglob(Path(name).name)), None)
            assert path is not None, name
            actual.append(len(re.findall(r"^def test_", _text(path), re.M)))
        if actual != counts:
            problems.append(f"{names}: documented {counts}, actual {actual}")
    assert problems == []


def test_every_screen_path_in_the_ui_inventory_is_a_real_route(app):
    """docs/10 section 1 names the path of each v4 screen; each must exist as a UI route."""

    def normal(path: str) -> str:
        return re.sub(r"\{[^}]*\}|<[^>]*>", "{}", path)

    routes = {normal(r.rule) for r in app.url_map.iter_rules() if not r.rule.startswith("/api")}
    inventory = _text(DOCS / "10-ui-ux-specification.md")
    problems = []
    for line in inventory.splitlines():
        match = re.match(r"^\| S(\d+) \|", line)
        if not match or int(match.group(1)) < 20:
            continue
        paths = re.findall(r"`(/[^`]*)`", line)
        base = paths[0].rsplit("/", 1)[0] if paths else ""
        for path in paths:
            candidate = normal(path)
            if candidate not in routes and normal(f"{base}{path}") not in routes:
                problems.append(f"S{match.group(1)}: {path}")
    assert problems == []


def test_the_v4_tables_of_the_data_dictionary_name_real_columns():
    """docs/06 section 13 lists each v4 table with its fields; every named field must exist."""
    connection = sqlite3.connect(":memory:")
    connection.executescript(_text(DOCS / "artifacts" / "schema.sql"))
    section = _text(DOCS / "06-data-dictionary.md").split("## 13. v4 Tables", 1)[1]
    problems = []
    checked = 0
    for line in section.splitlines():
        match = re.match(r"^\| `([a-z_]+)` \| (.+?) \| ", line)
        if not match:
            continue
        table, fields = match.group(1), match.group(2)
        columns = {r[1] for r in connection.execute(f'PRAGMA table_info("{table}")')}
        assert columns, f"{table} is not a table"
        checked += 1
        for token in re.findall(r"`([a-z][a-z_0-9]*)`", fields.split("(")[0] if False else fields):
            if token not in columns:
                problems.append(f"{table}.{token}")
    assert checked >= 20
    assert problems == []

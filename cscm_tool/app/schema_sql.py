"""Reads docs/artifacts/schema.sql (the hand-reviewed physical schema) and splits it
into statements. Migrations after the baseline use this to bring an older database
up to date from the same source of truth, instead of keeping a second copy of the
DDL that could drift (docs/15-development-standards.md §5)."""

import re
import sqlite3
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "docs" / "artifacts"
SCHEMA_SQL_PATH = SCHEMA_DIR / "schema.sql"
FTS_SQL_PATH = SCHEMA_DIR / "schema-fts5.sql"

_COMMENT_LINE = re.compile(r"^\s*--.*$", re.MULTILINE)


def split_statements(sql: str) -> list[str]:
    """Statements in file order, comments stripped. sqlite3.complete_statement
    understands trigger bodies, so `CREATE TRIGGER ... BEGIN ...; END;` stays whole."""
    statements: list[str] = []
    buffer = ""
    for line in sql.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            cleaned = _COMMENT_LINE.sub("", buffer).strip()
            if cleaned:
                statements.append(cleaned)
            buffer = ""
    return statements


def schema_statements(path: Path = SCHEMA_SQL_PATH) -> list[str]:
    return split_statements(path.read_text(encoding="utf-8"))


_TABLE_RE = re.compile(r"^CREATE TABLE (\w+)", re.IGNORECASE)
_INDEX_RE = re.compile(r"^CREATE (?:UNIQUE )?INDEX (\w+) ON (\w+)", re.IGNORECASE)
_TRIGGER_RE = re.compile(r"^CREATE TRIGGER (\w+)", re.IGNORECASE)
_INSERT_RE = re.compile(r"^INSERT INTO (\w+)", re.IGNORECASE)


def table_statements(table: str, statements: list[str] | None = None) -> list[str]:
    """CREATE TABLE + its indexes + its seed INSERTs, in file order."""
    found: list[str] = []
    for stmt in statements if statements is not None else schema_statements():
        m = _TABLE_RE.match(stmt)
        if m and m.group(1) == table:
            found.append(stmt)
            continue
        m = _INDEX_RE.match(stmt)
        if m and m.group(2) == table:
            found.append(stmt)
            continue
        m = _INSERT_RE.match(stmt)
        if m and m.group(1) == table:
            found.append(stmt)
    return found


def trigger_statement(name: str, statements: list[str] | None = None) -> str:
    for stmt in statements if statements is not None else schema_statements():
        m = _TRIGGER_RE.match(stmt)
        if m and m.group(1) == name:
            return stmt
    raise KeyError(name)

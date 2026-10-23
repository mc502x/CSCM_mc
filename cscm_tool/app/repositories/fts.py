"""SQLite FTS5 helpers for catalogue search (I-31).

The index (docs/artifacts/schema-fts5.sql) is optional derived data: when the table is
missing, or the SQLite build has no FTS5, every function here reports "not available" and
the repository falls back to substring search. With it, search gains relevance ranking
(bm25: a hit in the title outranks one buried in a description) and typo tolerance
("converte" and "convertor" still find "converter")."""

import re
from difflib import get_close_matches

from sqlalchemy import column, literal_column, select, table, text

from app.extensions import db

_TOKEN_RE = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]+")
_cache: dict[int, bool] = {}


def available() -> bool:
    engine_id = id(db.engine)
    if engine_id not in _cache:
        _cache[engine_id] = bool(
            db.session.execute(
                text("SELECT 1 FROM sqlite_master WHERE name = 'status_code_fts'")
            ).first()
        )
    return _cache[engine_id]


def forget_availability() -> None:
    """Tests that drop or create the index call this."""
    _cache.clear()


def tokens(query: str) -> list[str]:
    return _TOKEN_RE.findall(query)


def match_expression(query: str) -> str | None:
    """Every word must match as a prefix: 'conv grid' finds 'converter ... grid'."""
    words = tokens(query)
    if not words:
        return None
    return " ".join(f'"{w}"*' for w in words)


def fuzzy_expression(query: str) -> str | None:
    """Like match_expression, but each word may also match close spellings from the index."""
    words = tokens(query)
    if not words:
        return None
    parts = []
    for word in words:
        lowered = word.lower()
        rows = db.session.execute(
            text(
                "SELECT term FROM status_code_fts_vocab "
                "WHERE term LIKE :p AND ABS(LENGTH(term) - :n) <= 2 LIMIT 4000"
            ),
            {"p": lowered[0] + "%", "n": len(lowered)},
        )
        close = get_close_matches(lowered, [r[0] for r in rows], n=3, cutoff=0.75)
        alternatives = [f'"{word}"*'] + [f'"{c}"' for c in close if c != lowered]
        parts.append(
            "(" + " OR ".join(alternatives) + ")" if len(alternatives) > 1 else alternatives[0]
        )
    # FTS5 needs an explicit AND once a word is a parenthesised group of alternatives
    return " AND ".join(parts)


def ranked(expression: str):
    """Subquery (rid, score) of revisions matching `expression`, best score first."""
    fts = table("status_code_fts", column("rowid"))
    return (
        select(
            literal_column("rowid").label("rid"),
            literal_column("bm25(status_code_fts)").label("score"),
        )
        .select_from(fts)
        .where(text("status_code_fts MATCH :fts_match").bindparams(fts_match=expression))
        .subquery("fts_hits")
    )

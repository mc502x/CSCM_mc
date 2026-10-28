"""Shared timestamp helpers. Match schema.sql's strftime('%Y-%m-%dT%H:%M:%fZ','now')
format (SQLite %f = SS.SSS, millisecond precision) so Python- and DB-defaulted
timestamps sort and compare consistently as TEXT."""

from datetime import UTC, datetime

_ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def format_iso(dt: datetime) -> str:
    dt = dt.astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def parse_iso(value: str) -> datetime:
    return datetime.strptime(value, _ISO_FORMAT).replace(tzinfo=UTC)


def utcnow_iso() -> str:
    return format_iso(datetime.now(UTC))


def split_multi(value) -> list[str]:
    """The values of a multi-select filter: a list, a repeated query parameter or one comma-joined
    string ("DRAFT,REVIEW", the way saved searches and shared links keep them), without blanks or
    repeats, in the order given."""
    if value is None:
        return []
    parts = [value] if isinstance(value, str) else list(value)
    out: list[str] = []
    for part in parts:
        for item in str(part).split(","):
            item = item.strip()
            if item and item not in out:
                out.append(item)
    return out


def join_multi(values) -> str | None:
    """The comma-joined form of split_multi (None when nothing is chosen)."""
    return ",".join(split_multi(values)) or None

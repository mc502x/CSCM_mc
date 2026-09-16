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

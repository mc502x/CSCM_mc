"""JSON catalogue export."""

import json


def build_json(rows: list[dict]) -> bytes:
    return json.dumps(rows, indent=2, default=str).encode("utf-8")

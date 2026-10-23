"""Hash chain primitives for the tamper-evident audit log (I-18, AUD-074).

Every audit row stores `prev_hash` (the previous row's `entry_hash`, or GENESIS
for the first) and `entry_hash` over its own content plus `prev_hash`. Removing,
reordering or editing any row breaks the chain at that point, which
`AuditChainService.verify()` reports. With `AUDIT_HMAC_KEY` configured the hash
is an HMAC, so someone with the database file but not the key cannot recompute
a consistent chain after tampering.

The canonical form below is frozen: migration f8b2d4e6a012 carries its own copy
to back-fill old rows, and a test proves both produce identical hashes."""

import hashlib
import hmac
import json

GENESIS = "GENESIS"


def canonical_bytes(
    entity_type: str,
    entity_id: int,
    action: str,
    actor_id: int | None,
    occurred_at: str,
    before_value: str | None,
    after_value: str | None,
    ip_address: str | None,
    request_id: str,
    prev_hash: str,
) -> bytes:
    return json.dumps(
        [
            entity_type,
            entity_id,
            action,
            actor_id,
            occurred_at,
            before_value,
            after_value,
            ip_address,
            request_id,
            prev_hash,
        ],
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def compute_hash(payload: bytes, key: bytes | None = None) -> str:
    if key:
        return hmac.new(key, payload, hashlib.sha256).hexdigest()
    return hashlib.sha256(payload).hexdigest()

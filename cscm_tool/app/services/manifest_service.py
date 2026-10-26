"""Release integrity (I-06): a manifest for everything that leaves the system.

An export of a Release is accompanied by a manifest naming the release, the scope, the
row count, the SHA-256 of every file and a content digest of the data rows (independent of
the file format), plus who generated it and when. With `MANIFEST_SIGNING_KEY` configured
the manifest also carries an HMAC-SHA-256 signature, so a downstream consumer holding the
same on-premises key can tell the manifest itself was not edited. Without a key the
manifest is unsigned - integrity of the files is still checkable, authenticity of the
manifest is not (decision D-05).

Verification works without the database (`verify_file`), so Technical Publications can
check a CSV they received from a shared drive with nothing but the manifest."""

import hashlib
import hmac
import json
from typing import Any

from flask import current_app

MANIFEST_VERSION = 1


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode("utf-8")


def content_digest(rows: list[dict]) -> str:
    """Digest of the data itself, the same whether it ships as CSV, JSON, XLSX or PDF."""
    return sha256_hex(canonical_json(rows))


def _key() -> bytes | None:
    raw = current_app.config.get("MANIFEST_SIGNING_KEY")
    return raw.encode("utf-8") if raw else None


def key_id(key: bytes | None = None) -> str | None:
    key = key if key is not None else _key()
    return sha256_hex(key)[:8] if key else None


def sign(manifest: dict, key: bytes | None = None) -> dict:
    """Returns a copy of `manifest` with a `signature` member (None when no key is set)."""
    key = key if key is not None else _key()
    unsigned = {k: v for k, v in manifest.items() if k != "signature"}
    if not key:
        return {**unsigned, "signature": None}
    value = hmac.new(key, canonical_json(unsigned), hashlib.sha256).hexdigest()
    return {
        **unsigned,
        "signature": {"algorithm": "HMAC-SHA256", "key_id": key_id(key), "value": value},
    }


def verify_signature(manifest: dict, key: bytes | None = None) -> str:
    """'valid' | 'invalid' | 'unsigned' | 'no-key' (signed, but this server has no key)."""
    signature = manifest.get("signature")
    if not signature:
        return "unsigned"
    key = key if key is not None else _key()
    if not key:
        return "no-key"
    expected = sign({k: v for k, v in manifest.items() if k != "signature"}, key)["signature"]
    return (
        "valid"
        if hmac.compare_digest(expected["value"], str(signature.get("value")))
        else "invalid"
    )


def build_manifest(
    *,
    generated_at: str,
    generated_by: dict,
    release: dict | None,
    scope: dict,
    export_format: str,
    profile: str | None,
    audience: str | None,
    language: str | None,
    software_version: str | None,
    row_count: int,
    files: list[dict],
    digest: str,
    kind: str = "catalogue",
) -> dict:
    manifest = {
        "manifest_version": MANIFEST_VERSION,
        "kind": kind,
        "generated_at": generated_at,
        "generated_by": generated_by,
        "release": release,
        "scope": scope,
        "format": export_format,
        "profile": profile,
        "audience": audience,
        "language": language,
        "software_version": software_version,
        "row_count": row_count,
        "files": files,
        "content_digest": digest,
        "algorithm": "SHA-256",
    }
    return sign(manifest)


def verify_file(
    content: bytes, manifest: dict, filename: str | None = None, key: bytes | None = None
) -> dict:
    """Checks `content` against `manifest`: is its hash listed (under `filename`, if given),
    and is the manifest's own signature intact?"""
    digest = sha256_hex(content)
    listed = [f for f in manifest.get("files", []) if f.get("sha256") == digest]
    if filename:
        listed = [f for f in listed if f.get("name") == filename] or listed
    signature = verify_signature(manifest, key)
    have_key = (key if key is not None else _key()) is not None
    # With a key configured an unsigned manifest is not good enough: stripping the
    # signature must not make a tampered manifest look fine.
    signature_ok = signature == "valid" or (signature == "unsigned" and not have_key)
    return {
        "file_sha256": digest,
        "file_listed": bool(listed),
        "file_name_matches": bool(listed)
        and (filename is None or listed[0].get("name") == filename),
        "signature": signature,
        "ok": bool(listed) and signature_ok,
    }

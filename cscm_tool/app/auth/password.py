"""Password hashing and policy. SEC-001: Argon2id, plaintext/reversible
storage prohibited absolutely. Policy per docs/11-security-architecture.md §4."""

from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()

MIN_PASSWORD_LENGTH = 12

# Breach-corpus blocklist. A full corpus cannot be fetched at runtime (the
# no-cloud constraint, docs/11-security-architecture.md §12), so the list is
# local data: the built-in entries below plus every line of
# `seed_data/common_passwords.txt`. To use a larger corpus, replace that file
# with one lowercase password per line before go-live — a data change, not a
# code change. Only entries of at least MIN_PASSWORD_LENGTH characters can
# ever match, so shorter ones are ignored.
_BUILTIN_BLOCKLIST = frozenset(
    {
        "password123456",
        "123456789012",
        "qwertyuiop12",
        "administrator",
        "changeme12345",
        "welcome123456",
        "letmein123456",
    }
)


def _load_blocklist() -> frozenset[str]:
    path = Path(__file__).resolve().parents[2] / "seed_data" / "common_passwords.txt"
    extra: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            entry = line.strip().lower()
            if entry and not entry.startswith("#") and len(entry) >= MIN_PASSWORD_LENGTH:
                extra.add(entry)
    return _BUILTIN_BLOCKLIST | extra


_COMMON_PASSWORD_BLOCKLIST = _load_blocklist()


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False


def validate_password_policy(plain_password: str) -> list[str]:
    """Returns a list of human-readable violations; empty list means the
    password is acceptable. FR-013 enforces this on self password change;
    the same check applies to Administrator-created/reset passwords."""
    violations = []
    if len(plain_password) < MIN_PASSWORD_LENGTH:
        violations.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")
    if plain_password.lower() in _COMMON_PASSWORD_BLOCKLIST:
        violations.append("Password is too common; choose a less predictable password.")
    return violations

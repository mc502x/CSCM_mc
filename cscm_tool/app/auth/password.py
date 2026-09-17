"""Password hashing and policy. SEC-001: Argon2id, plaintext/reversible
storage prohibited absolutely. Policy per docs/11-security-architecture.md §4."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()

MIN_PASSWORD_LENGTH = 12

# Placeholder blocklist pending a real breach-corpus source (a full corpus
# cannot be bundled here without an internet fetch, which the no-cloud/
# on-premises constraint prohibits at runtime — see docs/11-security-
# architecture.md §12). Mirrors the Functional Subgroup placeholder pattern
# in docs/06-data-dictionary.md §9a: replace with a real local corpus file
# before go-live; this is a data change, not a code change.
_COMMON_PASSWORD_BLOCKLIST = frozenset(
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

from app.auth.password import hash_password, validate_password_policy, verify_password


def test_hash_and_verify_round_trip():
    hashed = hash_password("a genuinely long passphrase")
    assert hashed != "a genuinely long passphrase"
    assert verify_password("a genuinely long passphrase", hashed)


def test_verify_rejects_wrong_password():
    hashed = hash_password("a genuinely long passphrase")
    assert not verify_password("something else entirely", hashed)


def test_policy_rejects_short_password():
    violations = validate_password_policy("short1")
    assert violations
    assert any("12 characters" in v for v in violations)


def test_policy_rejects_blocklisted_password():
    violations = validate_password_policy("administrator")
    assert any("too common" in v for v in violations)


def test_policy_accepts_reasonable_password():
    assert validate_password_policy("a genuinely long passphrase") == []

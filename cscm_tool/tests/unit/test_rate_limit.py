from app.auth.rate_limit import check_and_record_login_attempt, reset_for_testing


def setup_function():
    reset_for_testing()


def test_allows_attempts_under_the_limit():
    for _ in range(5):
        assert check_and_record_login_attempt("10.0.0.1", "alice") is True


def test_blocks_after_five_username_attempts():
    for _ in range(5):
        assert check_and_record_login_attempt("10.0.0.1", "bob") is True
    assert check_and_record_login_attempt("10.0.0.2", "bob") is False


def test_blocks_after_ten_ip_attempts_across_usernames():
    for i in range(10):
        assert check_and_record_login_attempt("10.0.0.3", f"user{i}") is True
    assert check_and_record_login_attempt("10.0.0.3", "one-more-user") is False


def test_username_limit_is_case_insensitive():
    for _ in range(5):
        assert check_and_record_login_attempt("10.0.0.4", "Carol") is True
    assert check_and_record_login_attempt("10.0.0.5", "carol") is False

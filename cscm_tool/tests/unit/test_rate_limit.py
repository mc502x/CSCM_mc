"""SEC-004 / I-20: the login rate limiter, backed by the database.

TC-050. Requirements: NFR-009, SEC-004.
"""

import pytest

from app.auth.rate_limit import check_and_record_login_attempt
from app.extensions import db
from app.models.operations import LoginAttempt


@pytest.fixture()
def in_app(app):
    with app.app_context():
        yield
        db.session.rollback()


def test_allows_attempts_under_the_limit(in_app):
    for _ in range(5):
        assert check_and_record_login_attempt("10.0.0.1", "alice") is True


def test_blocks_after_five_username_attempts(in_app):
    for _ in range(5):
        assert check_and_record_login_attempt("10.0.0.1", "bob") is True
    assert check_and_record_login_attempt("10.0.0.2", "bob") is False


def test_blocks_after_ten_ip_attempts_across_usernames(in_app):
    for i in range(10):
        assert check_and_record_login_attempt("10.0.0.3", f"user{i}") is True
    assert check_and_record_login_attempt("10.0.0.3", "one-more-user") is False


def test_username_limit_is_case_insensitive(in_app):
    for _ in range(5):
        assert check_and_record_login_attempt("10.0.0.4", "Carol") is True
    assert check_and_record_login_attempt("10.0.0.5", "carol") is False


def test_attempts_age_out_of_the_window(in_app):
    for _ in range(5):
        assert check_and_record_login_attempt("10.0.0.6", "dave", now=1000.0) is True
    assert check_and_record_login_attempt("10.0.0.6", "dave", now=1000.0 + 60) is False
    # 15 minutes later the username window has passed and old rows are pruned
    assert check_and_record_login_attempt("10.0.0.6", "dave", now=1000.0 + 15 * 60 + 1) is True
    assert db.session.query(LoginAttempt).filter(LoginAttempt.scope == "USER").count() == 1


def test_a_refused_attempt_is_not_recorded(in_app):
    for _ in range(5):
        check_and_record_login_attempt("10.0.0.7", "erin")
    before = db.session.query(LoginAttempt).count()
    assert check_and_record_login_attempt("10.0.0.7", "erin") is False
    assert db.session.query(LoginAttempt).count() == before

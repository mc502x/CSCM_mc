"""SEC-002 / deployment hardening: a production instance must not start with a
guessable session-signing key."""

import pytest

from app import create_app
from app.config import CONFIG_BY_NAME, DEFAULT_SECRET_KEY, ProductionConfig


def _production_with_key(monkeypatch, key):
    class Config(ProductionConfig):
        SECRET_KEY = key
        SQLALCHEMY_DATABASE_URI = "sqlite://"

    monkeypatch.setitem(CONFIG_BY_NAME, "production", Config)


@pytest.mark.parametrize(
    "key", [DEFAULT_SECRET_KEY, "", "too-short", "x" * 31, "change-me-in-every-real-environment"]
)
def test_production_refuses_a_weak_secret_key(monkeypatch, key):
    _production_with_key(monkeypatch, key)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app("production")


def test_production_starts_with_a_strong_secret_key(monkeypatch):
    _production_with_key(monkeypatch, "k" * 40)
    app = create_app("production")
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["DEBUG"] is False


def test_development_and_testing_still_start_with_the_default_key():
    assert create_app("development").config["SECRET_KEY"] == DEFAULT_SECRET_KEY
    assert create_app("testing").testing is True

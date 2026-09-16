"""Environment-driven configuration. See docs/11-security-architecture.md
SEC-002/SEC-003 for the session cookie and timeout values fixed here."""

import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "instance", "cscm.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}}

    # SEC-002: session cookie attributes
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "Strict"

    # SEC-003: idle timeout 30 min, absolute session lifetime 12h
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    IDLE_SESSION_TIMEOUT = timedelta(minutes=30)

    # SEC-004: account lockout
    FAILED_LOGIN_LOCKOUT_THRESHOLD = 5
    FAILED_LOGIN_LOCKOUT_MINUTES = 15


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # local HTTP dev server, no TLS


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"  # in-memory, fresh per test run
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}

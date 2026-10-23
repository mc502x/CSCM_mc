"""Environment-driven configuration. See docs/11-security-architecture.md
SEC-002/SEC-003 for the session cookie and timeout values fixed here."""

import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# The development-only fallback: create_app() refuses to start a production instance
# that still uses it (and tests/system/test_production_config.py proves that).
DEFAULT_SECRET_KEY = "dev-secret-key-change-me"  # nosec B105
MIN_PRODUCTION_SECRET_LENGTH = 32


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "instance", "cscm.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}}

    # SEC-024: library import (EPIC-14) uploads are size- and type-limited.
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB

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

    # I-17 / SEC-026: sign-offs, approval, publish and the full-database export need the
    # actor's password again. Turning this off is a deliberate, documented deviation.
    STEP_UP_REQUIRED = True

    # I-06: optional keys. With MANIFEST_SIGNING_KEY every export manifest carries an
    # HMAC-SHA256 signature; with AUDIT_HMAC_KEY the audit hash chain is keyed (I-18).
    MANIFEST_SIGNING_KEY = os.environ.get("MANIFEST_SIGNING_KEY") or None
    AUDIT_HMAC_KEY = os.environ.get("AUDIT_HMAC_KEY") or None

    # I-13: evidence attachments (SEC-024)
    ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024
    ATTACHMENT_MAX_PER_CR = 20

    # I-09 / I-21: where verified backups go and how old the newest may be before
    # /health/ready reports "degraded".
    BACKUP_DIR = os.environ.get("BACKUP_DIR") or None
    BACKUP_MAX_AGE_HOURS = int(os.environ.get("BACKUP_MAX_AGE_HOURS", "36"))

    # I-08: optional mail through the organisation's own SMTP relay (never a cloud service)
    SMTP_HOST = os.environ.get("SMTP_HOST") or None
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "25"))
    SMTP_SENDER = os.environ.get("SMTP_SENDER", "cscm-tool@localhost")
    SMTP_STARTTLS = os.environ.get("SMTP_STARTTLS", "0") == "1"
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME") or None
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD") or None

    # I-21: /metrics is for the internal network only
    METRICS_ALLOWED_CIDRS = tuple(
        c.strip()
        for c in os.environ.get(
            "METRICS_ALLOWED_CIDRS", "127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
        ).split(",")
        if c.strip()
    )
    METRICS_TOKEN = os.environ.get("METRICS_TOKEN") or None
    LOG_FILE = os.environ.get("LOG_FILE") or None

    # I-32: uploads above this many rows are processed by a background worker
    IMPORT_ASYNC_ROW_THRESHOLD = int(os.environ.get("IMPORT_ASYNC_ROW_THRESHOLD", "300"))
    IMPORT_ASYNC_INLINE = False  # tests run the "background" job on the calling thread

    # FR-163 / SEC-033: how people sign in. "password" (the MVP), "windows" (the Windows identity
    # handed over by the organisation's authenticating gateway; passwords are refused) or "both".
    AUTH_MODE = os.environ.get("AUTH_MODE", "password")
    # The header the gateway (IIS with Windows authentication behind ARR, Apache with Kerberos,
    # nginx with spnego) sets to the signed-in user: DOMAIN\name or name@domain. REMOTE_USER of the
    # WSGI server is read too. It is believed only from the addresses listed below.
    WINDOWS_AUTH_HEADER = os.environ.get("WINDOWS_AUTH_HEADER", "X-Remote-User")
    WINDOWS_AUTH_TRUSTED_PROXIES = tuple(
        p.strip()
        for p in os.environ.get("WINDOWS_AUTH_TRUSTED_PROXIES", "").split(",")
        if p.strip()
    )
    # DOMAIN\name is matched with name@<this domain> (a user principal name needs none of it)
    WINDOWS_AUTH_EMAIL_DOMAIN = os.environ.get("WINDOWS_AUTH_EMAIL_DOMAIN") or None
    # A page that lets a developer pretend to be a Windows user. Refused in production.
    WINDOWS_AUTH_SIMULATE = False

    # I-29: webhook targets must resolve to private/loopback addresses (internal network only)
    WEBHOOK_TIMEOUT_SECONDS = 3
    WEBHOOK_ALLOW_PUBLIC_TARGETS = False


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # local HTTP dev server, no TLS
    # The Windows sign-in is simulated on a developer machine: password and Windows side by side
    # (docs/11-security-architecture.md SEC-033). Never honoured in production.
    AUTH_MODE = os.environ.get("AUTH_MODE", "both")
    WINDOWS_AUTH_SIMULATE = os.environ.get("WINDOWS_AUTH_SIMULATE", "1") == "1"


class TestingConfig(Config):
    TESTING = True
    IMPORT_ASYNC_INLINE = True
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

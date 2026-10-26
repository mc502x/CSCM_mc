"""Production entry point: Waitress behind the internal reverse proxy (docs/14 §3).

    python scripts/serve.py

Settings come from the environment, or from the `.env` file next to `wsgi.py` (or the file named
by CSCM_ENV_FILE) - the same file the Flask CLI reads, so the web process and the scheduled jobs
(`flask backup-db`, ...) always agree.

    CSCM_HOST            interface to bind (default 127.0.0.1; the reverse proxy is the public side)
    CSCM_PORT            port (default 8000)
    CSCM_THREADS         worker threads (default 8; SQLite serialises writers anyway)
    CSCM_TRUSTED_PROXY   address of the reverse proxy. When set, its X-Forwarded-For / -Proto /
                         -Host headers are believed (so the login rate limit sees the real client
                         address) and the same headers from anyone else are stripped.

The application itself refuses to start in production with a missing or weak SECRET_KEY."""

import os
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))


def build_options(environ: dict[str, str]) -> dict:
    options: dict = {
        "host": environ.get("CSCM_HOST", "127.0.0.1"),
        "port": int(environ.get("CSCM_PORT", "8000")),
        "threads": int(environ.get("CSCM_THREADS", "8")),
        "ident": "cscm",
        "channel_timeout": 120,
        "max_request_body_size": 25 * 1024 * 1024,
    }
    proxy = environ.get("CSCM_TRUSTED_PROXY")
    if proxy:
        options.update(
            trusted_proxy=proxy,
            trusted_proxy_count=1,
            trusted_proxy_headers={"x-forwarded-for", "x-forwarded-proto", "x-forwarded-host"},
            clear_untrusted_proxy_headers=True,
        )
    return options


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(os.environ.get("CSCM_ENV_FILE") or APP_DIR / ".env")  # before app.config reads it

    from waitress import serve

    from app import create_app

    serve(create_app("production"), **build_options(dict(os.environ)))


if __name__ == "__main__":
    main()

"""Structured JSON application logging (docs/11-security-architecture.md §11).

One JSON object per line on stderr. Logs describe *what happened to a request*
— method, path, status, duration, request id, authenticated user id — and never
contain credentials, session tokens, request bodies or query strings (a query
string can carry a search term or an identifier a user would not expect in a
log). They are operational diagnostics; the business record of truth is the
audit log (12-audit-compliance.md)."""

import json
import logging
import sys
import time
from datetime import UTC, datetime

from flask import Flask, Response, g, request

_LOGGER_NAME = "cscm"
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
            + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k not in _RESERVED})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(app: Flask) -> None:
    logger = logging.getLogger(_LOGGER_NAME)
    if not any(getattr(h, "_cscm", False) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonFormatter())
        handler._cscm = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    log_file = app.config.get("LOG_FILE")
    if log_file and not any(getattr(h, "_cscm_file", False) for h in logger.handlers):
        # I-21: a rotating file a log shipper can tail (the same JSON lines as stderr).
        from logging.handlers import RotatingFileHandler
        from pathlib import Path

        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(JsonFormatter())
        file_handler._cscm_file = True  # type: ignore[attr-defined]
        logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = True  # lets pytest's caplog observe the records

    @app.before_request
    def _start_timer():
        g.request_started = time.perf_counter()

    @app.after_request
    def _log_request(response: Response) -> Response:
        started = g.get("request_started")
        user = g.get("current_user")
        if started:
            from app.observability import observe_request

            observe_request(request.method, response.status_code, time.perf_counter() - started)
        logger.info(
            "request",
            extra={
                "request_id": g.get("request_id"),
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": (
                    round((time.perf_counter() - started) * 1000, 1) if started else None
                ),
                "user_id": getattr(user, "id", None),
                "remote_addr": request.remote_addr,
            },
        )
        return response

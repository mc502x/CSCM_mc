"""Operational telemetry for the internal network (I-21): request counters and latencies,
the time spent waiting for SQLite's write lock, and database gauges, in the Prometheus text
format at `GET /metrics`.

Everything stays on-premises (docs/11-security-architecture.md §12): the endpoint answers
only requests from the configured internal networks (`METRICS_ALLOWED_CIDRS`) or carrying
the `METRICS_TOKEN` bearer token, and nothing is pushed anywhere. Counters are per
process; the supported deployment is one waitress process with several threads."""

import hmac
import ipaddress
import threading
from collections import defaultdict

from flask import Flask, Response, current_app, g, request
from sqlalchemy import func

from app.extensions import db

_LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
_LOCK_BUCKETS = (0.001, 0.005, 0.025, 0.1, 0.5, 2.0, 10.0)


class _Registry:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.requests: dict[tuple[str, str], int] = defaultdict(int)
        self.latency_counts = [0] * (len(_LATENCY_BUCKETS) + 1)
        self.latency_sum = 0.0
        self.lock_counts = [0] * (len(_LOCK_BUCKETS) + 1)
        self.lock_sum = 0.0

    def reset(self) -> None:
        with self.lock:
            self.requests.clear()
            self.latency_counts = [0] * (len(_LATENCY_BUCKETS) + 1)
            self.latency_sum = 0.0
            self.lock_counts = [0] * (len(_LOCK_BUCKETS) + 1)
            self.lock_sum = 0.0


registry = _Registry()


def _bucket(buckets: tuple[float, ...], counts: list[int], value: float) -> None:
    for i, upper in enumerate(buckets):
        if value <= upper:
            counts[i] += 1
            return
    counts[-1] += 1


def observe_request(method: str, status: int, seconds: float) -> None:
    with registry.lock:
        registry.requests[(method, f"{status // 100}xx")] += 1
        registry.latency_sum += seconds
        _bucket(_LATENCY_BUCKETS, registry.latency_counts, seconds)


def observe_lock_wait(seconds: float) -> None:
    """Time spent in BEGIN IMMEDIATE, i.e. waiting for another writer (app/__init__.py)."""
    with registry.lock:
        registry.lock_sum += seconds
        _bucket(_LOCK_BUCKETS, registry.lock_counts, seconds)


def _histogram(name: str, help_text: str, buckets, counts, total_sum) -> list[str]:
    lines = [f"# HELP {name} {help_text}", f"# TYPE {name} histogram"]
    running = 0
    for upper, count in zip(buckets, counts, strict=False):
        running += count
        lines.append(f'{name}_bucket{{le="{upper}"}} {running}')
    running += counts[-1]
    lines.append(f'{name}_bucket{{le="+Inf"}} {running}')
    lines.append(f"{name}_sum {total_sum:.6f}")
    lines.append(f"{name}_count {running}")
    return lines


def _database_gauges() -> list[str]:
    from app.models.change_request import ChangeRequest
    from app.models.status_code import StatusCodeRevision
    from app.services.backup_service import status_summary
    from app.services.sla_service import SlaService

    lines = [
        "# HELP cscm_change_requests Change requests by state",
        "# TYPE cscm_change_requests gauge",
    ]
    for state, count in db.session.query(ChangeRequest.state, func.count()).group_by(
        ChangeRequest.state
    ):
        lines.append(f'cscm_change_requests{{state="{state}"}} {count}')
    lines += [
        "# HELP cscm_revisions Status code revisions by lifecycle",
        "# TYPE cscm_revisions gauge",
    ]
    for status, count in db.session.query(
        StatusCodeRevision.lifecycle_status, func.count()
    ).group_by(StatusCodeRevision.lifecycle_status):
        lines.append(f'cscm_revisions{{lifecycle="{status}"}} {count}')
    waiting: dict[tuple[str, str], int] = defaultdict(int)
    for _cr, info in SlaService.waiting():
        waiting[(info["stage"], info["level"])] += 1
    lines += [
        "# HELP cscm_cr_waiting Change requests waiting for a decision by stage and SLA level",
        "# TYPE cscm_cr_waiting gauge",
    ]
    for (stage, level), count in sorted(waiting.items()):
        lines.append(f'cscm_cr_waiting{{stage="{stage}",level="{level}"}} {count}')
    backup = status_summary()
    lines += [
        "# HELP cscm_backup_age_hours Hours since the last verified backup",
        "# TYPE cscm_backup_age_hours gauge",
    ]
    if "age_hours" in backup:
        lines.append(f"cscm_backup_age_hours {backup['age_hours']}")
    lines += [
        "# HELP cscm_backup_ok 1 when the last backup is fresh and verified",
        "# TYPE cscm_backup_ok gauge",
    ]
    lines.append(f"cscm_backup_ok {1 if backup['state'] == 'ok' else 0}")
    return lines


def render_metrics() -> str:
    with registry.lock:
        lines = [
            "# HELP cscm_http_requests_total HTTP requests handled by this process",
            "# TYPE cscm_http_requests_total counter",
        ]
        for (method, klass), count in sorted(registry.requests.items()):
            lines.append(f'cscm_http_requests_total{{method="{method}",status="{klass}"}} {count}')
        lines += _histogram(
            "cscm_http_request_duration_seconds",
            "Request latency",
            _LATENCY_BUCKETS,
            registry.latency_counts,
            registry.latency_sum,
        )
        lines += _histogram(
            "cscm_db_lock_wait_seconds",
            "Time waiting for the SQLite write lock (BEGIN IMMEDIATE)",
            _LOCK_BUCKETS,
            registry.lock_counts,
            registry.lock_sum,
        )
    lines += _database_gauges()
    return "\n".join(lines) + "\n"


def _allowed() -> bool:
    cfg = current_app.config
    token = cfg.get("METRICS_TOKEN")
    header = request.headers.get("Authorization", "")
    if token and header.startswith("Bearer ") and hmac.compare_digest(header[7:], token):
        return True
    try:
        client = ipaddress.ip_address(request.remote_addr or "")
    except ValueError:
        return False
    return any(
        client in ipaddress.ip_network(cidr, strict=False) for cidr in cfg["METRICS_ALLOWED_CIDRS"]
    )


def register_metrics(app: Flask) -> None:
    @app.get("/metrics")
    def metrics() -> Response:
        g.writes_on_get = False
        if not _allowed():
            return Response("forbidden\n", status=403, mimetype="text/plain")
        return Response(render_metrics(), mimetype="text/plain; version=0.0.4")

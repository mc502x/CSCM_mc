"""Liveness and readiness (14-deployment-architecture.md §8, I-21).

* GET /health        - the process is up (always cheap, no database).
* GET /health/ready  - the instance can serve: database reachable, schema at the expected
                       Alembic head, newest audit rows chain correctly, and the last verified
                       backup is recent (I-09). 200 when ready (status ok or degraded),
                       503 when not. Unauthenticated by design: it is for the internal
                       load balancer / monitoring and reveals no business data."""

from flask import jsonify

from app.api.v1 import api_v1_bp
from app.audit_chain import AuditChainService
from app.extensions import db
from app.services import backup_service


@api_v1_bp.get("/health")
def health():
    return jsonify(status="ok"), 200


@api_v1_bp.get("/health/ready")
def ready():
    checks: dict[str, dict] = {}
    try:
        db.session.execute(db.text("SELECT 1"))
        checks["database"] = {"state": "ok"}
        migration = backup_service.migration_state()
        checks["schema"] = {"state": "ok" if migration["ok"] else "outdated", **migration}
        checks["audit_chain"] = {"state": "ok"}
        tail = AuditChainService.verify_tail()
        if not tail["ok"]:
            checks["audit_chain"] = {"state": "broken", "first_bad_id": tail.get("first_bad_id")}
    except Exception as exc:  # noqa: BLE001  (any failure means "not ready", never a 500)
        checks.setdefault("database", {"state": "unavailable", "error": type(exc).__name__})
    finally:
        db.session.rollback()

    backup = backup_service.status_summary()
    checks["backup"] = backup

    hard_failure = (
        checks.get("database", {}).get("state") != "ok"
        or checks.get("schema", {}).get("state") != "ok"
        or checks.get("audit_chain", {}).get("state") == "broken"
    )
    degraded = backup["state"] in ("missing", "stale", "last_attempt_failed")
    status = "unavailable" if hard_failure else ("degraded" if degraded else "ok")
    return jsonify(status=status, checks=checks), (503 if hard_failure else 200)

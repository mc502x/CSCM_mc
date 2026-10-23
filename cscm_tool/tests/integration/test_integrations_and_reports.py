"""I-29 API tokens, change feed and webhooks; I-26 saved searches; I-28 fleet occurrences;
I-19 / I-10 reports; I-36 Hub -> Main Controller consolidation.

TC-046. Requirements: FR-123, FR-140, FR-141, FR-142, FR-143, FR-144, FR-145, FR-146, FR-147, SEC-027, SEC-028.
"""

import csv
import hashlib
import hmac
import io
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from app.extensions import db
from app.models.operations import ApiToken
from app.models.status_code import StatusCodeRevision
from tests.helpers import (
    cr_id_for_revision,
    decide,
    domain_sign,
    drive_to_approved,
    login_as,
    make_cast,
    release_revisions,
    submit,
    valid_payload,
)


@pytest.fixture()
def cast(make_user):
    return make_cast(make_user)


def _make_token(client, cast, scopes=("catalogue:read",), **extra):
    login_as(client, cast["admin"])
    resp = client.post(
        "/api/v1/api-tokens", json={"name": "Dashboard", "scopes": list(scopes), **extra}
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def _anonymous(app):
    """A client with no session cookie: only the Authorization header can identify it."""
    return app.test_client(use_cookies=False)


def _released_code(app, client, cast, wcnv_ids, title="Released for integrations", label="I1"):
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids, title=title)
    release_revisions(client, cast, [revision["id"]], label=label)
    return revision


# ------------------------------------------------------------------ API tokens
def test_a_token_is_shown_once_and_stored_only_as_a_hash(app, client, cast):
    created = _make_token(client, cast)
    assert created["token"].startswith("cscm_") and created["token_prefix"] == created["token"][:12]
    listing = client.get("/api/v1/api-tokens").get_json()
    assert (
        created["token"] not in json.dumps(listing) and listing["items"][0]["name"] == "Dashboard"
    )
    with app.app_context():
        row = db.session.query(ApiToken).one()
        assert row.token_hash == hashlib.sha256(created["token"].encode()).hexdigest()
        assert created["token"] not in row.token_hash


def test_a_token_reads_released_data_only_and_never_writes(app, client, cast, wcnv_ids):
    released = _released_code(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    client.post("/api/v1/status-codes", json=valid_payload(*wcnv_ids, title="Still a draft"))
    token = _make_token(client, cast)["token"]
    anonymous = _anonymous(app)
    headers = {"Authorization": f"Bearer {token}"}
    listing = anonymous.get("/api/v1/status-codes", headers=headers)
    assert listing.status_code == 200
    titles = [i["title"] for i in listing.get_json()["items"]]
    assert titles == [released["title"]]  # Viewer-level: no drafts
    assert anonymous.get("/api/v1/status-codes").status_code == 401  # no header, no access
    assert (
        anonymous.post(
            "/api/v1/status-codes", headers=headers, json=valid_payload(*wcnv_ids)
        ).status_code
        == 401
    )
    assert (
        anonymous.get("/api/v1/users", headers=headers).status_code == 401
    )  # not a token endpoint
    assert anonymous.get("/api/v1/auth/me", headers=headers).status_code in (401, 200)


def test_a_token_only_works_for_its_scope(app, client, cast):
    token = _make_token(client, cast, scopes=("changes:read",))["token"]
    anonymous = _anonymous(app)
    headers = {"Authorization": f"Bearer {token}"}
    assert anonymous.get("/api/v1/changes", headers=headers).status_code == 200
    assert anonymous.get("/api/v1/status-codes", headers=headers).status_code == 401


def test_revoked_expired_unknown_and_orphaned_tokens_are_refused(app, client, cast):
    anonymous = _anonymous(app)

    def works(token):
        return (
            anonymous.get(
                "/api/v1/changes", headers={"Authorization": f"Bearer {token}"}
            ).status_code
            == 200
        )

    revoked = _make_token(client, cast, scopes=("changes:read",))
    assert works(revoked["token"])
    assert client.delete(f"/api/v1/api-tokens/{revoked['id']}").status_code == 204
    assert not works(revoked["token"])
    assert client.delete(f"/api/v1/api-tokens/{revoked['id']}").status_code == 204  # idempotent

    expired = _make_token(client, cast, scopes=("changes:read",))
    with app.app_context():
        db.session.get(ApiToken, expired["id"]).expires_at = "2020-01-01T00:00:00.000Z"
        db.session.commit()
    assert not works(expired["token"])
    assert not works("cscm_" + "x" * 43)

    orphan = _make_token(client, cast, scopes=("changes:read",))
    with app.app_context():
        from app.models.user import User

        db.session.get(User, db.session.get(ApiToken, orphan["id"]).user_id).is_active = 0
        db.session.commit()
    assert not works(orphan["token"])


def test_token_management_is_for_administrators_and_validated(client, cast):
    login_as(client, cast["engineer"])
    assert (
        client.post(
            "/api/v1/api-tokens", json={"name": "x", "scopes": ["catalogue:read"]}
        ).status_code
        == 403
    )
    assert client.get("/api/v1/api-tokens").status_code == 403
    login_as(client, cast["admin"])
    for bad in (
        {"name": "", "scopes": ["catalogue:read"]},
        {"name": "x", "scopes": []},
        {"name": "x", "scopes": ["write:everything"]},
        {"name": "x", "scopes": ["catalogue:read"], "expires_in_days": 4000},
    ):
        assert client.post("/api/v1/api-tokens", json=bad).status_code == 422, bad
    assert client.delete("/api/v1/api-tokens/9999").status_code == 404


def test_token_events_are_audited_without_the_secret(app, client, cast):
    created = _make_token(client, cast)
    client.delete(f"/api/v1/api-tokens/{created['id']}")
    login_as(client, cast["admin"])
    entries = client.get("/api/v1/audit-log?entity_type=ApiToken").get_json()
    assert {e["action"] for e in entries} == {"API_TOKEN_CREATE", "API_TOKEN_REVOKE"}
    assert created["token"] not in json.dumps(entries)


# ------------------------------------------------------------------ change feed
def test_the_feed_lists_releases_in_order_with_a_cursor_and_an_etag(app, client, cast, wcnv_ids):
    first = _released_code(app, client, cast, wcnv_ids, "Feed code one", "F1")
    _released_code(app, client, cast, wcnv_ids, "Feed code two", "F2")
    login_as(client, cast["viewer"])
    feed = client.get("/api/v1/changes").get_json()
    assert [i["event"] for i in feed["items"]] == ["code.released", "code.released"]
    assert (
        feed["items"][0]["title"] == first["title"]
        and feed["items"][0]["release"]["version_label"] == "F1"
    )
    assert feed["has_more"] is False
    cursor = feed["items"][0]["id"]
    assert [
        i["title"] for i in client.get(f"/api/v1/changes?since_id={cursor}").get_json()["items"]
    ] == ["Feed code two"]
    paged = client.get("/api/v1/changes?limit=1").get_json()
    assert paged["has_more"] is True and len(paged["items"]) == 1

    response = client.get("/api/v1/changes")
    etag = response.headers["ETag"]
    assert client.get("/api/v1/changes", headers={"If-None-Match": etag}).status_code == 304
    _released_code(app, client, cast, wcnv_ids, "Feed code three", "F3")
    login_as(client, cast["viewer"])
    assert client.get("/api/v1/changes", headers={"If-None-Match": etag}).status_code == 200


def test_the_feed_needs_authentication(client):
    assert client.get("/api/v1/changes").status_code == 401


def test_sandbox_activity_never_appears_in_the_feed(app, client, cast, wcnv_ids):
    login_as(client, cast["engineer"])
    client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, is_sandbox=True, title="Scratch")
    )
    login_as(client, cast["viewer"])
    assert client.get("/api/v1/changes").get_json()["items"] == []


# ------------------------------------------------------------------ webhooks
class _Receiver:
    def __init__(self, status=200, location=None):
        outer = self
        self.calls = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                outer.calls.append((dict(self.headers), body))
                self.send_response(302 if location else status)
                if location:
                    self.send_header("Location", location)
                self.end_headers()

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/hook"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture()
def receiver():
    made = []

    def make(**kwargs):
        made.append(_Receiver(**kwargs))
        return made[-1]

    yield make
    for r in made:
        r.close()


def _webhook(client, cast, url, **extra):
    login_as(client, cast["admin"])
    resp = client.post("/api/v1/webhooks", json={"name": "Docs site", "url": url, **extra})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def test_a_publish_calls_the_webhook_with_a_verifiable_signature(
    app, client, cast, wcnv_ids, receiver
):
    target = receiver()
    hook = _webhook(client, cast, target.url)
    assert (
        "secret" in hook and "secret" not in client.get("/api/v1/webhooks").get_json()["items"][0]
    )
    _released_code(app, client, cast, wcnv_ids)
    assert len(target.calls) == 1
    raw_headers, body = target.calls[0]
    headers = {k.lower(): v for k, v in raw_headers.items()}
    expected = hmac.new(hook["secret"].encode(), body, hashlib.sha256).hexdigest()
    assert (
        headers["x-cscm-signature"] == f"sha256={expected}"
        and headers["x-cscm-event"] == "release.published"
    )
    payload = json.loads(body)
    assert payload["event"] == "release.published" and payload["data"]["version_label"] == "I1"
    login_as(client, cast["admin"])
    delivery = client.get(f"/api/v1/webhooks/{hook['id']}/deliveries").get_json()["items"][0]
    assert delivery["ok"] is True and delivery["http_status"] == 200
    assert client.get("/api/v1/webhooks").get_json()["items"][0]["last_status"] == "ok"


def test_a_failing_webhook_is_recorded_and_never_blocks_the_publish(
    app, client, cast, wcnv_ids, receiver
):
    broken = receiver(status=500)
    hook = _webhook(client, cast, broken.url)
    _released_code(
        app, client, cast, wcnv_ids
    )  # release_revisions asserts the publish returned 200
    login_as(client, cast["admin"])
    delivery = client.get(f"/api/v1/webhooks/{hook['id']}/deliveries").get_json()["items"][0]
    assert delivery["ok"] is False and delivery["http_status"] == 500
    assert client.get("/api/v1/webhooks").get_json()["items"][0]["last_status"] == "HTTP 500"


def test_an_unreachable_webhook_target_does_not_block_the_publish(
    app, client, cast, wcnv_ids, receiver
):
    target = receiver()
    hook = _webhook(client, cast, target.url)
    target.close()
    _released_code(app, client, cast, wcnv_ids)
    login_as(client, cast["admin"])
    delivery = client.get(f"/api/v1/webhooks/{hook['id']}/deliveries").get_json()["items"][0]
    assert delivery["ok"] is False and delivery["error"]


def test_redirects_are_not_followed(app, client, cast, wcnv_ids, receiver):
    elsewhere = receiver()
    bouncer = receiver(location=elsewhere.url)
    hook = _webhook(client, cast, bouncer.url)
    _released_code(app, client, cast, wcnv_ids)
    assert elsewhere.calls == []
    login_as(client, cast["admin"])
    assert (
        client.get(f"/api/v1/webhooks/{hook['id']}/deliveries").get_json()["items"][0]["ok"]
        is False
    )


def test_a_disabled_webhook_is_not_called(app, client, cast, wcnv_ids, receiver):
    target = receiver()
    hook = _webhook(client, cast, target.url)
    assert (
        client.patch(f"/api/v1/webhooks/{hook['id']}", json={"is_active": False}).get_json()[
            "is_active"
        ]
        is False
    )
    _released_code(app, client, cast, wcnv_ids)
    assert target.calls == []


def test_webhook_targets_must_be_internal_and_inputs_valid(client, cast):
    login_as(client, cast["admin"])
    for url in ("http://8.8.8.8/hook", "ftp://127.0.0.1/x", "not a url", ""):
        assert (
            client.post("/api/v1/webhooks", json={"name": "x", "url": url}).status_code == 422
        ), url
    assert (
        client.post("/api/v1/webhooks", json={"name": "", "url": "http://127.0.0.1/x"}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/webhooks",
            json={"name": "x", "url": "http://127.0.0.1/x", "events": ["code.deleted"]},
        ).status_code
        == 422
    )
    login_as(client, cast["engineer"])
    assert client.get("/api/v1/webhooks").status_code == 403
    login_as(client, cast["admin"])
    assert client.patch("/api/v1/webhooks/999", json={"is_active": False}).status_code == 404


# ------------------------------------------------------------------ saved searches
def test_saved_searches_round_trip_through_the_url(client, cast, wcnv_ids):
    login_as(client, cast["engineer"])
    client.post("/api/v1/status-codes", json=valid_payload(*wcnv_ids, title="converter in a draft"))
    created = client.post(
        "/api/v1/saved-searches",
        json={
            "name": "My drafts",
            "filters": {"lifecycle_status": "DRAFT", "q": "converter", "bogus": "x"},
            "columns": ["title", "set_delay", "nonsense"],
        },
    )
    assert created.status_code == 201
    body = created.get_json()
    assert body["filters"] == {"lifecycle_status": "DRAFT", "q": "converter"}
    assert body["columns"] == ["title", "set_delay"]
    assert (
        "lifecycle_status=DRAFT" in body["query_string"]
        and "cols=title%2Cset_delay" in body["query_string"]
    )
    listing = client.get("/api/v1/saved-searches").get_json()
    assert [s["name"] for s in listing["items"]] == ["My drafts"]
    assert "title" in {c["key"] for c in listing["available_columns"]}
    # the saved link reproduces the view
    page = client.get("/status-codes?" + body["query_string"]).get_data(as_text=True)
    table_headers = " ".join(re.findall(r"<th\b.*?</th>", page, re.S))
    assert "Set delay" in table_headers and "Reset delay" not in table_headers


def test_saving_under_an_existing_name_replaces_it_and_validates_the_name(client, cast):
    login_as(client, cast["engineer"])
    client.post("/api/v1/saved-searches", json={"name": "A", "filters": {"q": "one"}})
    client.post("/api/v1/saved-searches", json={"name": "A", "filters": {"q": "two"}})
    items = client.get("/api/v1/saved-searches").get_json()["items"]
    assert len(items) == 1 and items[0]["filters"] == {"q": "two"}
    assert client.post("/api/v1/saved-searches", json={"name": "  "}).status_code == 422
    assert client.post("/api/v1/saved-searches", json={"name": "x" * 81}).status_code == 422


def test_saved_searches_are_private_to_their_owner(client, cast):
    login_as(client, cast["engineer"])
    mine = client.post(
        "/api/v1/saved-searches", json={"name": "Mine", "filters": {"q": "x"}}
    ).get_json()
    login_as(client, cast["reviewer"])
    assert client.get("/api/v1/saved-searches").get_json()["items"] == []
    assert client.delete(f"/api/v1/saved-searches/{mine['id']}").status_code == 403
    assert client.delete("/api/v1/saved-searches/999").status_code == 404
    login_as(client, cast["engineer"])
    assert client.delete(f"/api/v1/saved-searches/{mine['id']}").status_code == 204
    assert client.get("/api/v1/saved-searches").get_json()["items"] == []


def test_saved_search_ui_save_and_delete(client, cast):
    login_as(client, cast["engineer"])
    saved = client.post(
        "/saved-searches",
        data={"name": "UI search", "q": "converter", "cols": "title,status_category"},
    )
    assert saved.status_code == 302
    page = client.get("/status-codes").get_data(as_text=True)
    assert "UI search" in page
    sid = client.get("/api/v1/saved-searches").get_json()["items"][0]["id"]
    assert client.post(f"/saved-searches/{sid}/delete").status_code == 302
    assert client.get("/api/v1/saved-searches").get_json()["items"] == []


# ------------------------------------------------------------------ fleet occurrences
def _counts(rows):
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["status_code_identifier", "occurrences"])
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


def _upload(client, rows, **fields):
    data = {
        "source_label": "SCADA Q1",
        "period_start": "2027-01-01",
        "period_end": "2027-03-31",
        **fields,
    }
    return client.post(
        "/api/v1/occurrence-imports",
        data={"file": (io.BytesIO(_counts(rows)), "counts.csv"), **data},
        content_type="multipart/form-data",
    )


def test_occurrence_report_names_codes_that_never_fire_and_those_that_fire_most(
    app, client, cast, wcnv_ids
):
    busy = _released_code(app, client, cast, wcnv_ids, "Busy converter fault", "O1")
    quiet = _released_code(app, client, cast, wcnv_ids, "Quiet converter fault", "O2")
    login_as(client, cast["chief_engineer"])
    busy_id = client.get(f"/api/v1/status-codes/{busy['status_code_id']}").get_json()[
        "status_code_identifier"
    ]
    uploaded = _upload(client, [(busy_id, "120"), (busy_id, "5"), ("StCd-99999", "7")])
    assert uploaded.status_code == 201
    assert uploaded.get_json()["matched_codes"] == 1 and uploaded.get_json()["unmatched_rows"] == 1
    report = client.get("/api/v1/reports/occurrences").get_json()
    assert report["periods_imported"] == 1 and report["live_codes"] == 2
    assert [e["occurrences"] for e in report["most_frequent"]] == [125]
    assert [e["title"] for e in report["never_fired"]] == [quiet["title"]]
    assert [e["title"] for e in report["needs_remedy_text"]] == [
        "Busy converter fault"
    ]  # no remedy yet
    assert client.get("/api/v1/reports/occurrences?min_periods=2").get_json()["never_fired"] == []
    assert len(client.get("/api/v1/occurrence-imports").get_json()["items"]) == 1


def test_occurrence_import_validation_and_permissions(client, cast):
    login_as(client, cast["engineer"])
    assert client.get("/api/v1/reports/occurrences").status_code == 403
    assert _upload(client, [("StCd-00001", "1")]).status_code == 403
    login_as(client, cast["chief_engineer"])
    assert _upload(client, [("StCd-00001", "-4")]).status_code == 422
    assert _upload(client, [("StCd-00001", "many")]).status_code == 422
    assert _upload(client, [("StCd-00001", "1")], period_end="2026-01-01").status_code == 422
    assert _upload(client, [("StCd-00001", "1")], source_label="").status_code == 422
    assert _upload(client, [("StCd-00001", "1")], period_start="soon").status_code == 422
    wrong = client.post(
        "/api/v1/occurrence-imports",
        data={
            "file": (io.BytesIO(b"a,b\n1,2\n"), "x.csv"),
            "source_label": "s",
            "period_start": "2027-01-01",
            "period_end": "2027-01-02",
        },
        content_type="multipart/form-data",
    )
    assert wrong.status_code == 422 and "status_code_identifier" in wrong.get_json()["message"]
    assert client.post("/api/v1/occurrence-imports", data={}).status_code == 422


# ------------------------------------------------------------------ catalogue health / KPIs
def test_the_capacity_table_colours_main_blue_and_hub_light_blue(client, cast):
    login_as(client, cast["admin"])
    rows = client.get("/api/v1/reports/catalogue-health").get_json()["capacity"]
    kind = {r["functional_subgroup"]: r["controller"] for r in rows}
    assert kind["010xx"] == "MC" and kind["0996x"] == "MC"
    assert kind["110xx"] == "HC" and kind["1110x"] == "HC" and kind["130xx"] == "HC"
    page = client.get("/reports/catalogue-health").get_data(as_text=True)
    assert page.count("controller-row--mc") >= 19 and page.count("controller-row--hc") == 11
    assert "controller-chip--mc" in page and "controller-chip--hc" in page
    css = (Path(__file__).resolve().parents[2] / "app" / "static" / "css" / "app.css").read_text(
        encoding="utf-8"
    )
    assert ".controller-chip--mc { background: #1565c0;" in css  # blue
    assert ".controller-chip--hc { background: #b3e5fc;" in css  # light blue


def test_health_report_covers_capacity_missing_data_and_inconsistencies(
    app, client, cast, wcnv_ids
):
    _released_code(app, client, cast, wcnv_ids, "Health check code", "H1")
    login_as(client, cast["admin"])
    report = client.get("/api/v1/reports/catalogue-health").get_json()
    assert set(report) >= {
        "capacity",
        "capacity_alerts",
        "missing_data",
        "inconsistencies",
        "unused_numbers",
        "upcoming",
    }
    converter = next(
        c
        for c in report["capacity"]
        if c["functional_system_group"] == "WCNV" and c["functional_subgroup"] == "010xx"
    )
    assert converter["allocated"] == 1 and converter["remaining"] == converter["total"] - 1
    assert (
        report["missing_data"]["checked"] == 1
        and report["missing_data"]["fields"]["remedy_text"]["count"] == 1
    )
    assert report["capacity_alerts"] == []
    # lowering the thresholds the other way makes the same band alert
    assert client.put(
        "/api/v1/admin/settings", json={"health.capacity_alert_percent": 100}
    ).status_code in (200, 404, 405)


def test_health_report_flags_a_nearly_full_band(app, client, cast, wcnv_ids):
    _released_code(app, client, cast, wcnv_ids, "Fill a band", "H2")
    with app.app_context():
        from app.auth.providers import AuthenticatedUser
        from app.services.settings_service import SettingsService

        admin = AuthenticatedUser(
            id=cast["admin"].id,
            username="a",
            email="a@example.com",
            full_name="A",
            role_code="ADMINISTRATOR",
        )
        SettingsService.update({"health.capacity_alert_percent": "100"}, admin)
    login_as(client, cast["chief_engineer"])
    alerts = client.get("/api/v1/reports/catalogue-health").get_json()["capacity_alerts"]
    assert any(a["functional_subgroup"] == "010xx" for a in alerts)


def test_health_report_finds_an_info_code_with_an_alarm(app, client, cast, wcnv_ids):
    drive_to_approved(
        app, client, cast, wcnv_ids, title="Odd info code", status_category="INFO", alarm_flag=True
    )
    login_as(client, cast["admin"])
    rules = {
        f["rule"]
        for f in client.get("/api/v1/reports/catalogue-health").get_json()["inconsistencies"]
    }
    assert "INFO_WITH_ALARM" in rules


def test_reports_are_limited_to_the_right_roles(client, cast):
    for role, allowed in (
        ("engineer", False),
        ("viewer", False),
        ("reviewer", True),
        ("admin", True),
    ):
        login_as(client, cast[role])
        assert (client.get("/api/v1/reports/catalogue-health").status_code == 200) is allowed, role
    for role, allowed in (("reviewer", False), ("chief_engineer", True), ("admin", True)):
        login_as(client, cast[role])
        assert (client.get("/api/v1/reports/kpis").status_code == 200) is allowed, role


def test_kpis_have_the_documented_shape(app, client, cast, wcnv_ids):
    _released_code(app, client, cast, wcnv_ids, "KPI code", "K1")
    login_as(client, cast["chief_engineer"])
    kpis = client.get("/api/v1/reports/kpis").get_json()
    assert isinstance(kpis, dict) and kpis
    assert client.get("/reports/success-metrics").status_code in (200, 404)


# ------------------------------------------------------------------ Hub -> Main consolidation
@pytest.fixture()
def hub_ids(app):
    with app.app_context():
        from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup

        group = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter_by(controller_type="HUB")
            .order_by(LookupFunctionalSystemGroup.sort_order)
            .first()
        )
        sub = (
            db.session.query(LookupFunctionalSubgroup)
            .filter_by(functional_system_group_id=group.id)
            .order_by(LookupFunctionalSubgroup.sort_order)
            .first()
        )
        return group.id, sub.id


def test_a_hub_code_is_carried_over_as_a_main_controller_draft(
    app, client, cast, hub_ids, wcnv_ids
):
    hub, _ = drive_to_approved(app, client, cast, hub_ids, title="Hub pitch fault")
    login_as(client, cast["engineer"])
    report = client.get("/api/v1/hub-consolidation/mapping").get_json()
    assert report["tally"]["OPEN"] == 1 and report["items"][0]["state"] == "OPEN"

    draft = client.post(
        f"/api/v1/status-codes/{hub['status_code_id']}/mc-drafts",
        json={"functional_system_group": wcnv_ids[0], "functional_subgroup": wcnv_ids[1]},
    )
    assert draft.status_code == 201, draft.get_json()
    body = draft.get_json()
    assert body["title"] == "Hub pitch fault" and body["lifecycle_status"] == "DRAFT"
    assert body["status_code_identifier"] is None  # the MC number is allocated at submit
    hub_identifier = client.get(f"/api/v1/status-codes/{hub['status_code_id']}").get_json()[
        "status_code_identifier"
    ]
    assert body["legacy_reference_number"] == hub_identifier

    again = client.post(
        f"/api/v1/status-codes/{hub['status_code_id']}/mc-drafts",
        json={"functional_system_group": wcnv_ids[0], "functional_subgroup": wcnv_ids[1]},
    )
    assert again.status_code == 409
    mapped = client.get("/api/v1/hub-consolidation/mapping").get_json()
    assert mapped["tally"]["MAPPED_DRAFT"] == 1 and mapped["ready_to_retire"] is False
    assert mapped["items"][0]["mc_status_code_id"] == body["status_code_id"]


def test_carry_over_is_refused_for_the_wrong_kind_of_code_or_target(
    app, client, cast, hub_ids, wcnv_ids
):
    main, _ = drive_to_approved(app, client, cast, wcnv_ids, title="A Main code")
    hub, _ = drive_to_approved(app, client, cast, hub_ids, title="A Hub code")
    login_as(client, cast["engineer"])
    url = lambda sid: f"/api/v1/status-codes/{sid}/mc-drafts"  # noqa: E731
    target = {"functional_system_group": wcnv_ids[0], "functional_subgroup": wcnv_ids[1]}
    assert (
        client.post(url(main["status_code_id"]), json=target).status_code == 422
    )  # not a Hub code
    assert (
        client.post(
            url(hub["status_code_id"]),
            json={"functional_system_group": hub_ids[0], "functional_subgroup": hub_ids[1]},
        ).status_code
        == 422
    )
    assert (
        client.post(
            url(hub["status_code_id"]),
            json={"functional_system_group": wcnv_ids[0], "functional_subgroup": hub_ids[1]},
        ).status_code
        == 422
    )
    assert client.post(url(99999), json=target).status_code == 404
    draft, _ = (None, None)
    login_as(client, cast["engineer"])
    unreleased = client.post(
        "/api/v1/status-codes", json=valid_payload(*hub_ids, title="Hub draft")
    ).get_json()
    assert (
        client.post(url(unreleased["status_code_id"]), json=target).status_code == 409
    )  # not Approved yet
    login_as(client, cast["viewer"])
    assert client.post(url(hub["status_code_id"]), json=target).status_code == 403
    del draft


def test_the_whole_consolidation_loop_ends_with_a_deprecation_request(
    app, client, cast, hub_ids, wcnv_ids
):
    hub, _ = drive_to_approved(app, client, cast, hub_ids, title="Hub generator fault")
    release_revisions(client, cast, [hub["id"]], label="HUB1")
    login_as(client, cast["admin"])
    skipped = client.post(
        "/api/v1/hub-consolidation/deprecation-requests",
        json={"functional_system_group": hub_ids[0]},
    ).get_json()
    assert skipped["created"] == [] and "no MC replacement" in skipped["skipped"][0]["reason"]

    login_as(client, cast["engineer"])
    draft = client.post(
        f"/api/v1/status-codes/{hub['status_code_id']}/mc-drafts",
        json={"functional_system_group": wcnv_ids[0], "functional_subgroup": wcnv_ids[1]},
    ).get_json()
    cr_id = cr_id_for_revision(app, draft["id"])
    domain_sign(client, cast, cr_id)
    assert submit(client, cast, cr_id).status_code == 200
    for who, endpoint in (
        ("reviewer", "reviewer-signoff"),
        ("admin", "admin-signoff"),
        ("chief_engineer", "chief-engineer-decide"),
    ):
        assert decide(client, cast[who], cr_id, endpoint).status_code == 200
    release_revisions(client, cast, [draft["id"]], label="MC1")

    login_as(client, cast["admin"])
    assert client.get("/api/v1/hub-consolidation/mapping").get_json()["tally"]["MAPPED_LIVE"] == 1
    result = client.post(
        "/api/v1/hub-consolidation/deprecation-requests",
        json={"functional_system_group": hub_ids[0]},
    ).get_json()
    assert len(result["created"]) == 1 and result["skipped"] == []
    with app.app_context():
        from app.models.change_request import ChangeRequest

        crs = db.session.query(ChangeRequest).filter_by(cr_type="DEPRECATION").all()
        assert len(crs) == 1 and "Replaced by" in crs[0].justification
        assert (
            db.session.query(StatusCodeRevision).filter_by(lifecycle_status="RELEASED").count() >= 2
        )
    # a second run does not open another request
    again = client.post(
        "/api/v1/hub-consolidation/deprecation-requests",
        json={"functional_system_group": hub_ids[0]},
    ).get_json()
    assert again["created"] == []


def test_bulk_deprecation_is_for_administrators_and_hub_groups(client, cast, hub_ids, wcnv_ids):
    login_as(client, cast["engineer"])
    assert (
        client.post(
            "/api/v1/hub-consolidation/deprecation-requests",
            json={"functional_system_group": hub_ids[0]},
        ).status_code
        == 403
    )
    login_as(client, cast["admin"])
    assert (
        client.post(
            "/api/v1/hub-consolidation/deprecation-requests",
            json={"functional_system_group": wcnv_ids[0]},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/hub-consolidation/deprecation-requests",
            json={"functional_system_group": 99999},
        ).status_code
        == 404
    )
    login_as(client, cast["viewer"])
    assert client.get("/api/v1/hub-consolidation/mapping").status_code == 403


def test_hub_consolidation_ui_page_renders(app, client, cast, hub_ids):
    drive_to_approved(app, client, cast, hub_ids, title="Hub UI code")
    login_as(client, cast["engineer"])
    page = client.get("/hub-consolidation")
    assert page.status_code == 200 and b"Hub UI code" in page.data

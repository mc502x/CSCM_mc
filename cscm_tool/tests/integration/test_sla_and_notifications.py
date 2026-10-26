"""I-08 SLA ages, stalled requests, in-app notices and reminders (docs/21-improvement-ideas.md),
and I-10 success metrics computed from the same timestamps.

TC-041. Requirements: FR-120, FR-121, FR-122, FR-123.
"""

from datetime import UTC, date, datetime, timedelta

import pytest

from app.extensions import db
from app.models.change_request import ChangeRequest
from app.models.operations import Notification
from app.services.kpi_service import KpiService
from app.services.mail_service import MailService
from app.services.notification_service import NotificationService
from app.services.sla_service import SlaService, business_days_between
from app.utils import format_iso
from tests.helpers import (
    drive_to_approved,
    drive_to_review,
    login_as,
    make_cast,
)


def _age(app, cr_id, days):
    """Move the CR's stage entry `days` calendar days into the past."""
    with app.app_context():
        cr = db.session.get(ChangeRequest, cr_id)
        stamp = format_iso(datetime.now(UTC) - timedelta(days=days))
        cr.submitted_at = stamp
        db.session.commit()


# ---------------------------------------------------------------- business days
def test_business_days_skip_weekends():
    friday = date(2026, 10, 23)
    assert friday.weekday() == 4
    assert business_days_between(friday, date(2026, 10, 23)) == 0
    assert business_days_between(friday, date(2026, 10, 24)) == 0  # Saturday
    assert business_days_between(friday, date(2026, 10, 26)) == 1  # Monday
    assert business_days_between(friday, date(2026, 10, 30)) == 5
    assert business_days_between(date(2026, 10, 26), date(2026, 10, 23)) == 0


def test_levels_follow_the_thresholds(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    login_as(client, cast["admin"])
    assert client.get(f"/api/v1/change-requests/{cr_id}/sla").get_json()["sla"]["level"] == "ok"
    _age(app, cr_id, 5)  # at least 3 business days (amber threshold)
    amber = client.get(f"/api/v1/change-requests/{cr_id}/sla").get_json()["sla"]
    assert amber["stage"] == "review" and amber["level"] in ("amber", "red")
    _age(app, cr_id, 14)  # >= 5 business days
    assert client.get(f"/api/v1/change-requests/{cr_id}/sla").get_json()["sla"]["level"] == "red"


def test_queues_show_the_waiting_time(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    _age(app, cr_id, 14)
    login_as(client, cast["reviewer"])
    html = client.get("/change-requests/review-queue").get_data(as_text=True)
    assert "sla sla--red" in html and "overdue" in html  # text, not colour alone


def test_thresholds_are_configurable_and_validated(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["admin"])
    assert client.put("/api/v1/settings", json={"sla.review.amber_days": "9"}).status_code == 422
    assert client.put("/api/v1/settings", json={"sla.review.amber_days": "x"}).status_code == 422
    assert client.put("/api/v1/settings", json={"no.such.key": "1"}).status_code == 422
    ok = client.put(
        "/api/v1/settings", json={"sla.review.amber_days": "1", "sla.review.red_days": "2"}
    )
    assert ok.status_code == 200
    values = {s["key"]: s["value"] for s in ok.get_json()["items"]}
    assert values["sla.review.amber_days"] == "1" and values["sla.approval.red_days"] == "3"
    login_as(client, cast["engineer"])
    assert client.get("/api/v1/settings").status_code == 403


def test_stalled_view_and_reassignment(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    _age(app, cr_id, 14)
    login_as(client, cast["admin"])
    stalled = client.get("/api/v1/change-requests/stalled").get_json()
    assert [s["change_request_id"] for s in stalled["items"]] == [cr_id]
    assert stalled["items"][0]["level"] == "red"
    page = client.get("/admin/stalled").get_data(as_text=True)
    assert "Assign" in page and str(cr_id) in page
    login_as(client, cast["engineer"])
    assert client.get("/api/v1/change-requests/stalled").status_code == 403


# ---------------------------------------------------------------- reminders
def test_reminders_go_to_whoever_holds_the_next_decision_once_a_day(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    _age(app, cr_id, 14)
    with app.app_context():
        first = NotificationService.send_reminders()
        again = NotificationService.send_reminders()
        recipients = {n.user_id for n in db.session.query(Notification).all()}
    # Reviewer + Administrator (the author is never reminded about their own request)
    assert recipients == {cast["reviewer"].id, cast["admin"].id}
    assert first["created"] == 2 and again["created"] == 0  # idempotent within a day

    login_as(client, cast["reviewer"])
    notices = client.get("/api/v1/notifications").get_json()
    assert notices["unread"] == 1 and "business days" in notices["items"][0]["message"]
    assert "unread" in client.get("/").get_data(as_text=True).lower()
    note_id = notices["items"][0]["id"]
    assert client.post(f"/api/v1/notifications/{note_id}/read").status_code == 200
    assert client.get("/api/v1/notifications?unread=true").get_json()["items"] == []

    login_as(client, cast["admin"])
    other_id = client.get("/api/v1/notifications").get_json()["items"][0]["id"]
    login_as(client, cast["reviewer"])
    assert client.post(f"/api/v1/notifications/{other_id}/read").status_code == 403


def test_assigned_reviewer_only_and_pending_approval_goes_to_chief_engineers(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    second_reviewer = make_user("REVIEWER")
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    login_as(client, cast["admin"])
    client.put(
        f"/api/v1/change-requests/{cr_id}/reviewer-assignment",
        json={"reviewer_id": cast["reviewer"].id},
    )
    _age(app, cr_id, 14)
    with app.app_context():
        NotificationService.send_reminders()
        recipients = {n.user_id for n in db.session.query(Notification).all()}
    assert second_reviewer.id not in recipients and cast["reviewer"].id in recipients

    login_as(client, cast["reviewer"])
    client.post(f"/api/v1/change-requests/{cr_id}/reviewer-signoff", json={"decision": "APPROVE"})
    login_as(client, cast["admin"])
    client.post(f"/api/v1/change-requests/{cr_id}/admin-signoff", json={"decision": "APPROVE"})
    with app.app_context():  # now waiting for the Chief Engineer
        cr = db.session.get(ChangeRequest, cr_id)
        cr.revision.reviewer_signoff_at = format_iso(datetime.now(UTC) - timedelta(days=14))
        cr.revision.admin_signoff_at = format_iso(datetime.now(UTC) - timedelta(days=14))
        db.session.commit()
        db.session.query(Notification).delete()
        db.session.commit()
        NotificationService.send_reminders()
        recipients = {n.user_id for n in db.session.query(Notification).all()}
    assert recipients == {cast["chief_engineer"].id}


def test_reminders_also_reach_a_covering_delegate_and_can_be_mailed(
    app, client, make_user, wcnv_ids, monkeypatch
):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    _age(app, cr_id, 14)
    cover = make_user("ENGINEER")
    login_as(client, cast["reviewer"])
    client.post(
        "/api/v1/delegations",
        json={
            "delegate_id": cover.id,
            "valid_from": datetime.now(UTC).date().isoformat(),
            "valid_to": (datetime.now(UTC) + timedelta(days=2)).date().isoformat(),
        },
    )
    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            sent.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def send_message(self, message):
            sent.append(("mail", message["To"], message["Subject"]))

    monkeypatch.setattr("app.services.mail_service.smtplib.SMTP", FakeSMTP)
    app.config["SMTP_HOST"] = "mail.internal"
    with app.app_context():
        assert MailService.enabled()
        result = NotificationService.send_reminders()
        recipients = {n.user_id for n in db.session.query(Notification).all()}
    assert cover.id in recipients
    assert result["emailed"] == result["created"] >= 3
    assert any(item[0] == "mail" and "waiting for you" in item[2] for item in sent)


def test_mail_failure_never_breaks_the_reminder_job(app, client, make_user, wcnv_ids, monkeypatch):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    _age(app, cr_id, 14)

    def broken(*args, **kwargs):
        raise OSError("relay down")

    monkeypatch.setattr("app.services.mail_service.smtplib.SMTP", broken)
    app.config["SMTP_HOST"] = "mail.internal"
    with app.app_context():
        result = NotificationService.send_reminders()
    assert result["created"] >= 1 and result["emailed"] == 0  # the in-app notice still exists


def test_send_reminders_cli(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["send-reminders"])
    assert result.exit_code == 0 and '"created": 0' in result.output


def test_withdrawn_cr_notices_are_removed_with_it(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    _age(app, cr_id, 14)
    with app.app_context():
        NotificationService.send_reminders()
        assert db.session.query(Notification).count() == 2
    login_as(client, cast["engineer"])
    assert client.post(f"/api/v1/change-requests/{cr_id}/withdraw").status_code == 200
    with app.app_context():
        assert db.session.query(Notification).count() == 0


def test_mark_all_read(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    _age(app, cr_id, 14)
    with app.app_context():
        NotificationService.send_reminders()
    login_as(client, cast["admin"])
    assert client.post("/api/v1/notifications/read-all").get_json()["updated"] == 1
    assert client.get("/api/v1/notifications").get_json()["unread"] == 0
    assert client.post("/api/v1/notifications/read-all").get_json()["updated"] == 0
    page = client.get("/notifications").get_data(as_text=True)
    assert "SLA_REMINDER" not in page and "business days" in page  # listed, but no longer unread


# ---------------------------------------------------------------- KPIs (I-10)
@pytest.fixture()
def released_flow(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, cr_id = drive_to_approved(app, client, cast, wcnv_ids)
    from tests.helpers import release_revisions

    release_revisions(client, cast, [revision["id"]])
    return cast, revision, cr_id


def test_kpis_are_computed_from_stored_timestamps(app, client, released_flow):
    cast, _revision, cr_id = released_flow
    with app.app_context():
        cr = db.session.get(ChangeRequest, cr_id)
        cr.submitted_at = format_iso(datetime.now(UTC) - timedelta(days=10))
        db.session.commit()
        kpis = KpiService.compute()
    approval = kpis["approval_time"]["all_time"]
    assert approval["sample_size"] == 1 and approval["median_days"] >= 6
    assert approval["target_days"] == 7
    assert kpis["audit_trail"]["percent"] == 100.0
    assert kpis["unknown_owner"]["count"] == 0
    assert kpis["queues"]["waiting_total"] == 0

    login_as(client, cast["chief_engineer"])
    assert client.get("/api/v1/reports/kpis").status_code == 200
    assert "Success metrics" in client.get("/reports/success-metrics").get_data(as_text=True)
    login_as(client, cast["reviewer"])
    assert client.get("/api/v1/reports/kpis").status_code == 403


def test_kpis_flag_an_incomplete_audit_trail_and_an_ownerless_code(
    app, client, released_flow, make_user
):
    cast, revision, _cr = released_flow
    with app.app_context():
        from app.models.audit import AuditLogEntry
        from app.models.status_code import StatusCode
        from app.models.user import User

        db.session.execute(
            db.text("DROP TRIGGER trg_audit_no_delete"),
        )
        db.session.query(AuditLogEntry).filter(
            AuditLogEntry.action == "CHIEF_ENGINEER_APPROVE"
        ).delete()
        code = db.session.get(StatusCode, revision["status_code_id"])
        db.session.get(User, code.owner_id).is_active = 0
        db.session.commit()
        kpis = KpiService.compute()
    assert kpis["audit_trail"]["percent"] == 0.0
    assert kpis["audit_trail"]["incomplete_examples"]
    assert kpis["unknown_owner"]["count"] == 1


def test_kpis_without_data_do_not_divide_by_zero(app):
    with app.app_context():
        kpis = KpiService.compute()
    assert kpis["approval_time"]["all_time"]["median_days"] is None
    assert kpis["audit_trail"]["percent"] is None


def test_the_default_thresholds_are_the_documented_ones(app):
    with app.app_context():
        assert SlaService.thresholds() == {
            "review": {"amber": 3, "red": 5},
            "approval": {"amber": 2, "red": 3},
        }

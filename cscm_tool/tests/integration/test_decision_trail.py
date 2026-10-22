"""Where review comments live: the change-request page, the status-code
"Decisions & Comments" tab, and the audit log (which carries the comment text,
and keeps it even when a change request is withdrawn)."""

import json

from app.extensions import db
from app.models.audit import AuditLogEntry
from tests.helpers import (
    PASSWORD,
    decide,
    drive_to_review,
    login_as,
    make_cast,
)


def _ui_login(client, user):
    from app.auth.rate_limit import reset_for_testing

    reset_for_testing()
    client.post("/logout")
    assert (
        client.post("/login", data={"username": user.username, "password": PASSWORD}).status_code
        == 302
    )


def _audit(app, action):
    with app.app_context():
        rows = db.session.query(AuditLogEntry).filter(AuditLogEntry.action == action).all()
        return [
            (json.loads(r.before_value or "null"), json.loads(r.after_value or "null"))
            for r in rows
        ]


def test_audit_entries_carry_the_comment_text_and_id(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    decide(client, cast["reviewer"], cr_id, "reviewer-signoff", comment="Delay value checked.")
    decide(client, cast["admin"], cr_id, "admin-signoff", comment="Audience access confirmed.")
    decide(
        client,
        cast["chief_engineer"],
        cr_id,
        "chief-engineer-decide",
        comment="Approved for release.",
    )
    login_as(client, cast["admin"])
    client.post(f"/api/v1/change-requests/{cr_id}/comments", json={"comment": "FYI for the record"})

    for action, text in (
        ("REVIEWER_SIGNOFF", "Delay value checked."),
        ("ADMIN_SIGNOFF", "Audience access confirmed."),
        ("CHIEF_ENGINEER_APPROVE", "Approved for release."),
        ("COMMENT", "FYI for the record"),
    ):
        [(_, after)] = _audit(app, action)
        assert after["comment"] == text and isinstance(after["comment_id"], int), action


def test_status_code_page_lists_all_decisions_and_comments(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    decide(client, cast["reviewer"], cr_id, "reviewer-signoff", comment="Looks right to me.")
    login_as(client, cast["admin"])
    client.post(
        f"/api/v1/change-requests/{cr_id}/comments", json={"comment": "Please mind the delays."}
    )

    _ui_login(client, cast["engineer"])
    page = client.get(f"/status-codes/{revision['status_code_id']}?tab=decisions").get_data(
        as_text=True
    )
    assert "Decisions &amp; Comments (2)" in page
    assert "Looks right to me." in page and "Please mind the delays." in page
    assert f"{cast['reviewer'].full_name} (Reviewer)" in page and "Reviewer approved" in page


def test_viewers_cannot_see_the_review_discussion(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    decide(client, cast["reviewer"], cr_id, "reviewer-signoff", comment="internal remark")
    _ui_login(client, cast["viewer"])
    # the code itself is not yet visible to a Viewer; the tab and its content never are
    page = client.get(f"/status-codes/{revision['status_code_id']}?tab=decisions")
    assert b"internal remark" not in page.data and b"Decisions &amp; Comments" not in page.data


def test_withdrawing_keeps_the_discussion_in_the_audit_log(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids, title="Withdrawn soon")
    decide(
        client,
        cast["reviewer"],
        cr_id,
        "reviewer-signoff",
        decision="REJECT",
        comment="Wrong delay.",
    )
    login_as(client, cast["engineer"])
    assert client.post(f"/api/v1/change-requests/{cr_id}/withdraw").status_code == 200

    [(before, _)] = _audit(app, "WITHDRAW")
    assert before["title"] == "Withdrawn soon"
    assert [c["comment"] for c in before["comments"]] == ["Wrong delay."]
    assert before["domain_signoffs"][0]["domain"] == "CONTROLS"
    assert client.get(f"/api/v1/change-requests/{cr_id}").status_code in (403, 404)


def test_audit_log_can_be_filtered_by_action_and_actor(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    decide(client, cast["reviewer"], cr_id, "reviewer-signoff", comment="ok")
    login_as(client, cast["admin"])

    entries = client.get(
        "/api/v1/audit-log", query_string={"action": "REVIEWER_SIGNOFF"}
    ).get_json()
    assert [e["action"] for e in entries] == ["REVIEWER_SIGNOFF"]
    mine = client.get(
        "/api/v1/audit-log",
        query_string={"action": "REVIEWER_SIGNOFF", "actor_id": cast["reviewer"].id},
    ).get_json()
    assert len(mine) == 1
    none = client.get(
        "/api/v1/audit-log",
        query_string={"action": "REVIEWER_SIGNOFF", "actor_id": cast["engineer"].id},
    ).get_json()
    assert none == []

    _ui_login(client, cast["admin"])
    html = client.get("/admin/audit-log?action=REVIEWER_SIGNOFF").get_data(as_text=True)
    assert "REVIEWER_SIGNOFF" in html and "SUBMIT_FOR_REVIEW</td>" not in html

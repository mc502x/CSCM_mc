"""I-23 field comments and review checklists, I-13 evidence attachments, I-11 change sets,
I-30 reviewer balancing (docs/21-improvement-ideas.md).

TC-040. Requirements: FR-124, FR-127, FR-128, FR-129, FR-130, SEC-024.
"""

import io
from datetime import UTC, datetime, timedelta

from app.extensions import db
from app.models.audit import AuditLogEntry
from tests.helpers import (
    PASSWORD,
    create_draft,
    domain_sign,
    drive_to_review,
    login_as,
    make_cast,
    submit,
    valid_payload,
)


def _tomorrow():
    return (datetime.now(UTC) + timedelta(days=1)).date().isoformat()


# ---------------------------------------------------------------- field comments (I-23)
def test_reviewer_comments_on_a_field_and_the_author_sees_and_resolves_it(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    login_as(client, cast["reviewer"])
    created = client.post(
        f"/api/v1/change-requests/{cr_id}/field-comments",
        json={"field": "set_delay", "comment": "10ms is below the control cycle time."},
    )
    assert created.status_code == 201
    comment = created.get_json()
    assert comment["field"] == "set_delay" and comment["resolved_at"] is None

    client.post(
        f"/api/v1/change-requests/{cr_id}/reviewer-signoff",
        json={"decision": "REJECT", "comment": "See the field comment."},
    )
    login_as(client, cast["engineer"])
    page = client.get(f"/status-codes/{revision['status_code_id']}/edit").get_data(as_text=True)
    assert "10ms is below the control cycle time." in page  # shown inline on the Draft
    resolved = client.post(f"/api/v1/field-comments/{comment['id']}/resolve")
    assert resolved.status_code == 200 and resolved.get_json()["resolved_by"] == cast["engineer"].id
    page = client.get(f"/status-codes/{revision['status_code_id']}/edit").get_data(as_text=True)
    assert "10ms is below the control cycle time." not in page


def test_field_comment_rules(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, cr_id = create_draft(app, client, cast, wcnv_ids)
    login_as(client, cast["reviewer"])
    url = f"/api/v1/change-requests/{cr_id}/field-comments"
    # while the CR is still a Draft nobody reviews it yet
    assert client.post(url, json={"field": "title", "comment": "x"}).status_code == 409

    domain_sign(client, cast, cr_id)
    submit(client, cast, cr_id)
    login_as(client, cast["reviewer"])
    assert client.post(url, json={"field": "not_a_field", "comment": "x"}).status_code == 422
    assert client.post(url, json={"field": "title", "comment": " "}).status_code == 422
    assert client.post(url, json={"field": "title", "comment": "ok"}).status_code == 201

    login_as(client, cast["engineer"])
    assert client.post(url, json={"field": "title", "comment": "mine"}).status_code == 403
    listing = client.get(url).get_json()["items"]
    assert [c["comment_text"] for c in listing] == ["ok"]
    login_as(client, cast["viewer"])
    assert client.get(url).status_code == 403

    with app.app_context():
        assert db.session.query(AuditLogEntry).filter_by(action="FIELD_COMMENT").count() == 1


def test_only_the_commenter_author_or_admin_can_resolve(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    login_as(client, cast["reviewer"])
    comment = client.post(
        f"/api/v1/change-requests/{cr_id}/field-comments", json={"field": "title", "comment": "c"}
    ).get_json()
    other = make_user("ENGINEER")
    login_as(client, other)
    assert client.post(f"/api/v1/field-comments/{comment['id']}/resolve").status_code == 403
    login_as(client, cast["admin"])
    assert client.post(f"/api/v1/field-comments/{comment['id']}/resolve").status_code == 200


# ---------------------------------------------------------------- checklist (I-23)
def test_checklist_must_be_confirmed_to_approve_and_is_recorded(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    login_as(client, cast["admin"])
    item = client.post(
        "/api/v1/review-checklist-items", json={"text": "Delay values checked against the logic"}
    )
    assert item.status_code == 201
    item_id = item.get_json()["id"]
    other = client.post(
        "/api/v1/review-checklist-items",
        json={"text": "Description is unambiguous", "functional_system_group": wcnv_ids[0]},
    ).get_json()

    login_as(client, cast["reviewer"])
    needed = client.get(f"/api/v1/change-requests/{cr_id}/review-checklist").get_json()
    assert {i["id"] for i in needed["items"]} == {item_id, other["id"]}

    path = f"/api/v1/change-requests/{cr_id}/reviewer-signoff"
    refused = client.post(path, json={"decision": "APPROVE", "checklist_confirmed": [item_id]})
    assert refused.status_code == 422
    assert "Description is unambiguous" in refused.get_json()["message"]
    # rejecting never needs a checklist
    ok = client.post(
        path,
        json={"decision": "APPROVE", "checklist_confirmed": [item_id, other["id"]]},
    )
    assert ok.status_code == 200

    recorded = client.get(f"/api/v1/change-requests/{cr_id}/review-checklist").get_json()
    assert {c["item_text"] for c in recorded["confirmations"]} == {
        "Delay values checked against the logic",
        "Description is unambiguous",
    }


def test_checklist_is_administrator_managed_and_inactive_items_are_not_required(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    assert (
        client.post("/api/v1/review-checklist-items", json={"text": "nope nope"}).status_code == 403
    )
    login_as(client, cast["admin"])
    item = client.post("/api/v1/review-checklist-items", json={"text": "Temporary item"}).get_json()
    assert (
        client.patch(
            f"/api/v1/review-checklist-items/{item['id']}", json={"is_active": False}
        ).get_json()["is_active"]
        is False
    )
    assert client.get("/api/v1/review-checklist-items").get_json()["items"] == []
    assert (
        len(client.get("/api/v1/review-checklist-items?include_inactive=true").get_json()["items"])
        == 1
    )
    bad = client.post("/api/v1/review-checklist-items", json={"text": "x"})
    assert bad.status_code == 422


def test_rejection_does_not_need_the_checklist(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    login_as(client, cast["admin"])
    client.post("/api/v1/review-checklist-items", json={"text": "Must be confirmed"})
    login_as(client, cast["reviewer"])
    rejected = client.post(
        f"/api/v1/change-requests/{cr_id}/reviewer-signoff",
        json={"decision": "REJECT", "comment": "Not good enough."},
    )
    assert rejected.status_code == 200


# ---------------------------------------------------------------- attachments (I-13)
def _upload(client, cr_id, name, content, description="evidence"):
    return client.post(
        f"/api/v1/change-requests/{cr_id}/attachments",
        data={"file": (io.BytesIO(content), name), "description": description},
        content_type="multipart/form-data",
    )


def test_author_attaches_evidence_and_reviewers_download_it(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    pdf = b"%PDF-1.4\n% test report\n"
    created = _upload(client, cr_id, "../../test report.pdf", pdf)
    assert created.status_code == 201
    meta = created.get_json()
    assert meta["filename"] == "test_report.pdf"  # path parts are stripped
    assert meta["size_bytes"] == len(pdf) and len(meta["sha256"]) == 64

    login_as(client, cast["reviewer"])
    downloaded = client.get(f"/api/v1/attachments/{meta['id']}")
    assert downloaded.status_code == 200
    assert downloaded.data == pdf
    assert downloaded.headers["Content-Disposition"].startswith("attachment;")
    assert downloaded.headers["X-Content-SHA256"] == meta["sha256"]
    assert downloaded.headers["X-Content-Type-Options"] == "nosniff"
    listing = client.get(f"/api/v1/change-requests/{cr_id}/attachments").get_json()["items"]
    assert [a["id"] for a in listing] == [meta["id"]]

    login_as(client, cast["viewer"])
    assert client.get(f"/api/v1/attachments/{meta['id']}").status_code == 403


def test_attachment_type_size_and_content_checks(app, client, make_user, wcnv_ids, monkeypatch):
    cast = make_cast(make_user)
    _, cr_id = create_draft(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    assert _upload(client, cr_id, "run.exe", b"MZ\x00\x00").status_code == 422
    assert _upload(client, cr_id, "fake.pdf", b"this is not a pdf").status_code == 422
    assert _upload(client, cr_id, "fake.png", b"%PDF-1.4").status_code == 422
    assert _upload(client, cr_id, "empty.txt", b"").status_code == 422
    assert _upload(client, cr_id, "binary.txt", b"abc\x00def").status_code == 422
    assert _upload(client, cr_id, "notes.txt", "Prüfbericht ✓".encode()).status_code == 201
    app.config["ATTACHMENT_MAX_BYTES"] = 10
    assert _upload(client, cr_id, "big.txt", b"x" * 11).status_code == 422
    app.config["ATTACHMENT_MAX_BYTES"] = 1024 * 1024
    app.config["ATTACHMENT_MAX_PER_CR"] = 1
    assert _upload(client, cr_id, "second.txt", b"two").status_code == 422


def test_attachment_permissions_and_removal_rules(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = create_draft(app, client, cast, wcnv_ids)
    other = make_user("ENGINEER")
    login_as(client, other)
    assert _upload(client, cr_id, "a.txt", b"hello").status_code == 403
    login_as(client, cast["engineer"])
    meta = _upload(client, cr_id, "a.txt", b"hello").get_json()
    login_as(client, other)
    assert client.delete(f"/api/v1/attachments/{meta['id']}").status_code == 403

    login_as(client, cast["engineer"])
    domain_sign(client, cast, cr_id)
    submit(client, cast, cr_id)
    login_as(client, cast["engineer"])
    # once submitted the evidence is frozen: no removal, no more uploads
    assert client.delete(f"/api/v1/attachments/{meta['id']}").status_code == 409
    login_as(client, cast["engineer"])
    assert _upload(client, cr_id, "b.txt", b"late").status_code == 201  # still open for evidence


def test_removing_a_draft_attachment_deletes_the_file_and_withdrawal_purges_all(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    _, cr_id = create_draft(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    first = _upload(client, cr_id, "a.txt", b"one").get_json()
    second = _upload(client, cr_id, "b.txt", b"two").get_json()
    with app.app_context():
        from app.models.change_request import CrAttachment

        paths = {
            a.id: a.storage_path
            for a in db.session.query(CrAttachment).filter_by(change_request_id=cr_id)
        }
    from pathlib import Path

    assert all(Path(p).is_file() for p in paths.values())
    assert client.delete(f"/api/v1/attachments/{first['id']}").status_code == 204
    assert not Path(paths[first["id"]]).exists()
    assert client.post(f"/api/v1/change-requests/{cr_id}/withdraw").status_code == 200
    assert not Path(paths[second["id"]]).exists()


# ---------------------------------------------------------------- change sets (I-11)
def test_change_set_groups_requests_and_bulk_decisions_stay_individual(
    app, client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    _, cr_a = drive_to_review(app, client, cast, wcnv_ids, title="First of the package")
    _, cr_b = drive_to_review(app, client, cast, wcnv_ids, title="Second of the package")

    login_as(client, cast["engineer"])
    created = client.post(
        "/api/v1/change-sets", json={"name": "Controller 4.2", "description": "Release train"}
    )
    assert created.status_code == 201
    set_id = created.get_json()["id"]
    for cr_id in (cr_a, cr_b):
        assert (
            client.post(
                f"/api/v1/change-sets/{set_id}/change-requests", json={"change_request_id": cr_id}
            ).status_code
            == 200
        )
    overview = client.get(f"/api/v1/change-sets/{set_id}").get_json()
    assert overview["tally"] == {"REVIEW": 2}
    assert {i["change_request_id"] for i in overview["items"]} == {cr_a, cr_b}

    # the Reviewer decides the whole package in one call - one audit entry per CR
    login_as(client, cast["reviewer"])
    result = client.post(
        f"/api/v1/change-sets/{set_id}/decisions",
        json={"step": "reviewer", "decision": "APPROVE", "current_password": PASSWORD},
    ).get_json()["results"]
    assert [r["ok"] for r in result] == [True, True]
    with app.app_context():
        assert db.session.query(AuditLogEntry).filter_by(action="REVIEWER_SIGNOFF").count() == 2

    # the author's own request in the set is skipped for them with the reason, the others go through
    login_as(client, cast["admin"])
    result = client.post(
        f"/api/v1/change-sets/{set_id}/decisions",
        json={"step": "admin", "decision": "APPROVE", "current_password": PASSWORD},
    ).get_json()["results"]
    assert all(r["ok"] for r in result)
    assert client.get(f"/api/v1/change-sets/{set_id}").get_json()["tally"] == {
        "PENDING_APPROVAL": 2
    }


def test_bulk_decision_skips_what_the_actor_may_not_decide(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, mine = drive_to_review(app, client, cast, wcnv_ids, title="Written by the admin")
    # an Administrator-authored CR
    login_as(client, cast["admin"])
    created = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, title="Admin's own change")
    ).get_json()
    from tests.helpers import cr_id_for_revision

    own_cr = cr_id_for_revision(app, created["id"])
    domain_sign(client, cast, own_cr)
    submit(client, cast, own_cr, who="admin")

    login_as(client, cast["engineer"])
    set_id = client.post("/api/v1/change-sets", json={"name": "Mixed"}).get_json()["id"]
    login_as(client, cast["engineer"])
    client.post(f"/api/v1/change-sets/{set_id}/change-requests", json={"change_request_id": mine})
    login_as(client, cast["admin"])
    client.post(f"/api/v1/change-sets/{set_id}/change-requests", json={"change_request_id": own_cr})

    results = client.post(
        f"/api/v1/change-sets/{set_id}/decisions",
        json={"step": "admin", "decision": "APPROVE", "current_password": PASSWORD},
    ).get_json()["results"]
    by_cr = {r["cr_id"]: r for r in results}
    assert by_cr[mine]["ok"] is True
    assert by_cr[own_cr]["ok"] is False and "own change request" in by_cr[own_cr]["message"]


def test_bulk_decision_needs_the_password_once_and_a_wrong_one_counts_once(
    app, client, raw_client, make_user, wcnv_ids
):
    cast = make_cast(make_user)
    _, cr_a = drive_to_review(app, client, cast, wcnv_ids, title="A one")
    _, cr_b = drive_to_review(app, client, cast, wcnv_ids, title="B two")
    login_as(client, cast["engineer"])
    set_id = client.post("/api/v1/change-sets", json={"name": "Pw"}).get_json()["id"]
    for cr_id in (cr_a, cr_b):
        client.post(
            f"/api/v1/change-sets/{set_id}/change-requests", json={"change_request_id": cr_id}
        )
    login_as(raw_client, cast["reviewer"])
    body = {"step": "reviewer", "decision": "APPROVE", "current_password": "wrong password here"}
    refused = raw_client.post(f"/api/v1/change-sets/{set_id}/decisions", json=body)
    assert refused.status_code == 403 and refused.get_json()["error"] == "step_up_failed"
    with app.app_context():
        from app.models.user import User

        assert db.session.get(User, cast["reviewer"].id).failed_login_count == 1  # once, not per CR


def test_change_set_rules(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    set_id = client.post("/api/v1/change-sets", json={"name": "Dup"}).get_json()["id"]
    assert client.post("/api/v1/change-sets", json={"name": "Dup"}).status_code == 422
    assert client.post("/api/v1/change-sets", json={"name": ""}).status_code == 422
    stranger = make_user("ENGINEER")
    login_as(client, stranger)
    assert (
        client.post(
            f"/api/v1/change-sets/{set_id}/change-requests", json={"change_request_id": cr_id}
        ).status_code
        == 403
    )
    login_as(client, cast["engineer"])
    assert (
        client.post(
            f"/api/v1/change-sets/{set_id}/change-requests", json={"change_request_id": cr_id}
        ).status_code
        == 200
    )
    other_id = client.post("/api/v1/change-sets", json={"name": "Other"}).get_json()["id"]
    again = client.post(
        f"/api/v1/change-sets/{other_id}/change-requests", json={"change_request_id": cr_id}
    )
    assert again.status_code == 422  # a CR belongs to one set
    assert client.delete(f"/api/v1/change-sets/{set_id}/change-requests/{cr_id}").status_code == 204
    login_as(client, cast["admin"])
    assert client.post(f"/api/v1/change-sets/{set_id}/close").get_json()["status"] == "CLOSED"
    login_as(client, cast["engineer"])
    closed = client.post(
        f"/api/v1/change-sets/{set_id}/change-requests", json={"change_request_id": cr_id}
    )
    assert closed.status_code == 422
    login_as(client, cast["viewer"])
    assert client.get("/api/v1/change-sets").status_code == 403


# ---------------------------------------------------------------- balancing (I-30)
def test_least_loaded_reviewer_is_suggested_and_assigned(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    busy = cast["reviewer"]
    free = make_user("REVIEWER")
    _, cr_one = drive_to_review(app, client, cast, wcnv_ids, title="Gets the busy reviewer")
    _, cr_two = drive_to_review(app, client, cast, wcnv_ids, title="Gets the free reviewer")
    login_as(client, cast["admin"])
    assert (
        client.put(
            f"/api/v1/change-requests/{cr_one}/reviewer-assignment", json={"reviewer_id": busy.id}
        ).status_code
        == 200
    )
    load = {
        w["user_id"]: w["open_reviews"]
        for w in client.get("/api/v1/reviewers/workload").get_json()["items"]
    }
    assert load == {busy.id: 1, free.id: 0}
    auto = client.post(f"/api/v1/change-requests/{cr_two}/reviewer-assignment/auto")
    assert auto.status_code == 200 and auto.get_json()["assigned_reviewer_id"] == free.id


def test_out_of_office_reviewers_are_not_auto_assigned(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    _, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    cover = make_user("ENGINEER")
    login_as(client, cast["reviewer"])
    client.post(
        "/api/v1/delegations",
        json={
            "delegate_id": cover.id,
            "valid_from": datetime.now(UTC).date().isoformat(),
            "valid_to": _tomorrow(),
        },
    )
    login_as(client, cast["admin"])
    refused = client.post(f"/api/v1/change-requests/{cr_id}/reviewer-assignment/auto")
    assert (
        refused.status_code == 422 and "No Reviewer is available" in refused.get_json()["message"]
    )


def test_auto_assignment_on_submit_is_a_setting(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["admin"])
    saved = client.put("/api/v1/settings", json={"reviewer.auto_assign": "1"})
    assert saved.status_code == 200
    revision, cr_id = create_draft(app, client, cast, wcnv_ids)
    domain_sign(client, cast, cr_id)
    assert submit(client, cast, cr_id).status_code == 200
    login_as(client, cast["admin"])
    assigned = client.get(f"/api/v1/change-requests/{cr_id}").get_json()["assigned_reviewer_id"]
    assert assigned == cast["reviewer"].id
    with app.app_context():
        entry = db.session.query(AuditLogEntry).filter_by(action="REVIEWER_ASSIGN").one()
        assert entry.actor_id is None and '"auto": true' in entry.after_value

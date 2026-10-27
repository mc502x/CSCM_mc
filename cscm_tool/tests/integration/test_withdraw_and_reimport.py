"""Withdrawing change requests (several at once) and what a withdrawal does to a program that was
imported from a StCd file: a withdrawn Draft gives its reserved number back, a withdrawn code that
already has its identifier keeps it and can be restored, and a program that differs from the code
already in the catalogue can update the Draft or open a new revision (docs/03-srs.md FR-159, FR-160,
FR-048x, BR-026).

TC-056. Requirements: FR-159, FR-160, FR-048x, BR-026, BR-001, FR-026.

A withdrawn code that keeps its number can be deleted by an Administrator (BR-026, S48).
"""

import io
import json
from pathlib import Path

import pytest
from sqlalchemy import text

from app.extensions import db
from app.models.audit import AuditLogEntry
from app.models.change_request import ChangeRequest
from app.models.status_code import StatusCode
from tests.helpers import (
    PASSWORD,
    cr_id_for_revision,
    decide,
    domain_sign,
    login_as,
    make_cast,
    submit,
    valid_payload,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "st"


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


def _read(name):
    return (FIXTURES / name).read_bytes()


def _preview(client, files):
    data = {
        "files": [(io.BytesIO(content), name) for name, content in files],
        "default_category": "ERROR",
    }
    response = client.post(
        "/api/v1/imports/st/preview", data=data, content_type="multipart/form-data"
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()


def _item(preview, program=None):
    return next(i for i in preview["items"] if program is None or i["program_number"] == program)


def _import(client, name="StCd_1001.st", content=None):
    preview = _preview(client, [(name, content or _read(name))])
    response = client.post("/api/v1/imports/st", json={"token": preview["token"]})
    assert response.status_code == 202, response.get_json()
    return response.get_json()


def _changed(name, old, new):
    text_ = _read(name).decode("cp1252")
    assert old in text_
    return text_.replace(old, new, 1).encode("cp1252")


def _only_code(app):
    with app.app_context():
        code = db.session.query(StatusCode).one()
        return code.id, code.revisions[0].id if code.revisions else None


def _cr_of(app, revision_id):
    return cr_id_for_revision(app, revision_id)


# ------------------------------------------------------------------------------ bulk withdraw
def _drafts(client, cast, wcnv_ids, n=3):
    login_as(client, cast["engineer"])
    ids = []
    for k in range(n):
        created = client.post(
            "/api/v1/status-codes", json=valid_payload(*wcnv_ids, title=f"Withdraw me {k}")
        )
        assert created.status_code == 201, created.get_json()
        ids.append(created.get_json()["id"])
    return ids


def test_several_change_requests_are_withdrawn_in_one_go_and_each_is_reported(
    app, client, cast, wcnv_ids
):
    revision_ids = _drafts(client, cast, wcnv_ids)
    cr_ids = [_cr_of(app, r) for r in revision_ids]
    response = client.post(
        "/api/v1/change-requests/withdraw", json={"cr_ids": cr_ids[:2] + [99999]}
    )
    body = response.get_json()
    assert response.status_code == 200 and body["withdrawn"] == 2 and body["failed"] == 1
    assert [r["ok"] for r in body["results"]] == [True, True, False]
    with app.app_context():
        assert db.session.query(ChangeRequest).count() == 1  # the third is untouched
        withdrawn = db.session.query(AuditLogEntry).filter_by(action="WITHDRAW").count()
        assert withdrawn == 2  # each one has its own audit entry


def test_a_change_request_of_somebody_else_is_refused_and_the_others_go_on(
    app, client, cast, wcnv_ids
):
    mine = _drafts(client, cast, wcnv_ids, n=1)
    login_as(client, cast["admin"])
    theirs = client.post("/api/v1/status-codes", json=valid_payload(*wcnv_ids, title="Admin draft"))
    admin_cr = _cr_of(app, theirs.get_json()["id"])
    login_as(client, cast["engineer"])
    body = client.post(
        "/api/v1/change-requests/withdraw", json={"cr_ids": [admin_cr, _cr_of(app, mine[0])]}
    ).get_json()
    assert [r["ok"] for r in body["results"]] == [False, True]
    assert "requesting Engineer" in body["results"][0]["message"]


def test_bulk_withdraw_needs_a_list_and_a_role_that_can_withdraw(client, cast):
    login_as(client, cast["engineer"])
    for body in ({}, {"cr_ids": []}, {"cr_ids": ["x"]}):
        assert client.post("/api/v1/change-requests/withdraw", json=body).status_code == 422
    for who in ("reviewer", "viewer", "stcd_owner"):
        login_as(client, cast[who])
        assert (
            client.post("/api/v1/change-requests/withdraw", json={"cr_ids": [1]}).status_code == 403
        )


def test_the_list_has_tick_boxes_and_a_withdraw_selected_button(app, client, cast, wcnv_ids):
    revision_ids = _drafts(client, cast, wcnv_ids)
    page = client.get("/change-requests/mine").get_data(as_text=True)
    assert page.count('class="cr-row-check"') == 3 and "Withdraw selected" in page
    assert 'data-check-all="cr-row-check"' in page
    ids = [_cr_of(app, r) for r in revision_ids]
    done = client.post(
        "/change-requests/withdraw-selected", data={"cr_id": ids[:2]}, follow_redirects=True
    )
    assert "2 change request(s) withdrawn." in done.get_data(as_text=True)
    none = client.post("/change-requests/withdraw-selected", data={}, follow_redirects=True)
    assert "Tick at least one" in none.get_data(as_text=True)
    login_as(client, cast["reviewer"])
    assert "Withdraw selected" not in client.get("/change-requests/mine").get_data(as_text=True)


# ------------------------------------------------------------------------------ withdrawn imports
def test_a_withdrawn_import_draft_gives_its_number_and_legacy_number_back(app, client, cast):
    login_as(client, cast["engineer"])
    _import(client)
    code_id, revision_id = _only_code(app)
    assert (
        client.post(
            "/api/v1/change-requests/withdraw", json={"cr_ids": [_cr_of(app, revision_id)]}
        ).status_code
        == 200
    )
    with app.app_context():
        code = db.session.get(StatusCode, code_id)
        assert code.reserved_identifier is None and code.legacy_reference_number is None
        assert (
            db.session.execute(
                text("SELECT prg_idx FROM status_code WHERE id = :i"), {"i": code_id}
            ).scalar()
            is None
        )
        entry = db.session.query(AuditLogEntry).filter_by(action="WITHDRAW").one()
        released = json.loads(entry.before_value)["released_to_the_catalogue"]
        assert released["reserved_identifier"] == "StCd-01001"
        assert released["legacy_reference_number"] == "3005"  # kept in the audit entry

    # the same program imports again as a new code, not as "already there"
    preview = _preview(client, [("StCd_1001.st", _read("StCd_1001.st"))])
    assert _item(preview)["state"] == "ready" and preview["summary"]["ready"] == 1
    assert client.post("/api/v1/imports/st", json={"token": preview["token"]}).status_code == 202


def test_a_withdrawn_code_that_has_its_identifier_keeps_it_and_can_be_restored(app, client, cast):
    login_as(client, cast["engineer"])
    _import(client)
    code_id, revision_id = _only_code(app)
    cr_id = _cr_of(app, revision_id)
    domain_sign(client, cast, cr_id)
    assert submit(client, cast, cr_id).status_code == 200  # StCd-01001 is issued now
    assert (
        client.post("/api/v1/change-requests/withdraw", json={"cr_ids": [cr_id]}).status_code == 200
    )
    with app.app_context():
        code = db.session.get(StatusCode, code_id)
        assert code.status_code_identifier == "StCd-01001" and not code.revisions  # number kept
        assert code.legacy_reference_number == "3005"

    preview = _preview(client, [("StCd_1001.st", _read("StCd_1001.st"))])
    item = _item(preview)
    assert item["state"] == "restorable" and item["action"] == "restore"
    assert item["existing"]["lifecycle_state"] == "WITHDRAWN"
    # not ticked by default: only an explicit choice restores
    assert client.post("/api/v1/imports/st", json={"token": preview["token"]}).status_code == 422
    preview = _preview(client, [("StCd_1001.st", _read("StCd_1001.st"))])
    response = client.post(
        "/api/v1/imports/st", json={"token": preview["token"], "selected": [item["key"]]}
    )
    assert response.status_code == 202 and response.get_json()["created_count"] == 1
    with app.app_context():
        code = db.session.get(StatusCode, code_id)
        assert db.session.query(StatusCode).count() == 1  # the same code, not a second one
        revision = code.revisions[0]
        assert revision.revision_number == 1 and revision.lifecycle_status == "DRAFT"
        assert code.status_code_identifier == "StCd-01001"
        cr = db.session.query(ChangeRequest).one()
        assert cr.import_job_id and cr.change_set_id


def _withdrawn_issued_code(app, client, cast):
    login_as(client, cast["engineer"])
    _import(client)
    code_id, revision_id = _only_code(app)
    cr_id = _cr_of(app, revision_id)
    domain_sign(client, cast, cr_id)
    assert submit(client, cast, cr_id).status_code == 200
    assert (
        client.post("/api/v1/change-requests/withdraw", json={"cr_ids": [cr_id]}).status_code == 200
    )
    return code_id


def test_a_withdrawn_code_is_listed_and_an_administrator_deletes_it_and_imports_again(
    app, client, cast
):
    from app.audit_chain import AuditChainService

    code_id = _withdrawn_issued_code(app, client, cast)
    login_as(client, cast["admin"])
    page = client.get("/admin/withdrawn-codes").get_data(as_text=True)
    assert "StCd-01001" in page and "3005" in page and "Delete selected" in page

    wrong = client.post(
        "/admin/withdrawn-codes/delete",
        data={"ids": [code_id], "current_password": "not the password"},
        follow_redirects=True,
    )
    assert "withdrawn code(s) deleted" not in wrong.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(StatusCode, code_id) is not None  # a wrong password deletes nothing

    done = client.post(
        "/admin/withdrawn-codes/delete",
        data={"ids": [code_id], "current_password": PASSWORD},
        follow_redirects=True,
    )
    assert "1 withdrawn code(s) deleted." in done.get_data(as_text=True)
    with app.app_context():
        shell = db.session.get(StatusCode, code_id)
        # erased in place: the row (and so its id) stays, the number and the references go
        assert shell is not None and shell.deleted_at is not None
        assert shell.status_code_identifier is None and shell.legacy_reference_number is None
        entry = db.session.query(AuditLogEntry).filter_by(action="WITHDRAWN_CODE_DELETE").one()
        before = json.loads(entry.before_value)
        assert before["status_code_identifier"] == "StCd-01001"
        assert before["legacy_reference_number"] == "3005"
        assert AuditChainService.verify(update_anchor=False)["ok"] is True

    # the program imports again as a new code: nothing blocks it any more
    login_as(client, cast["engineer"])
    preview = _preview(client, [("StCd_1001.st", _read("StCd_1001.st"))])
    assert _item(preview)["state"] == "ready"
    assert client.post("/api/v1/imports/st", json={"token": preview["token"]}).status_code == 202
    with app.app_context():
        new_code = db.session.query(StatusCode).filter(StatusCode.deleted_at.is_(None)).one()
        assert new_code.id != code_id  # an id is never handed out twice
        assert new_code.reserved_identifier == "StCd-01001"
    # the deleted code is gone from the list
    login_as(client, cast["admin"])
    assert "No withdrawn codes." in client.get("/admin/withdrawn-codes").get_data(as_text=True)


def test_a_restored_code_is_no_shell_and_the_database_refuses_a_delete_around_the_service(
    app, client, cast
):
    from sqlalchemy.exc import IntegrityError

    code_id = _withdrawn_issued_code(app, client, cast)
    assert client.get("/admin/withdrawn-codes").status_code in (302, 403)  # not for an engineer

    preview = _preview(client, [("StCd_1001.st", _read("StCd_1001.st"))])
    item = _item(preview)
    client.post("/api/v1/imports/st", json={"token": preview["token"], "selected": [item["key"]]})

    login_as(client, cast["admin"])
    assert "No withdrawn codes." in client.get("/admin/withdrawn-codes").get_data(as_text=True)
    done = client.post(
        "/admin/withdrawn-codes/delete",
        data={"ids": [code_id], "current_password": PASSWORD},
        follow_redirects=True,
    )
    assert "Not deleted" in done.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(StatusCode, code_id) is not None
        with pytest.raises(IntegrityError):  # trg_prevent_nonsandbox_delete
            db.session.execute(text("DELETE FROM status_code WHERE id = :i"), {"i": code_id})
            db.session.commit()
        db.session.rollback()


# ------------------------------------------------------------------------------ update / revise
def test_a_changed_program_updates_the_open_draft_when_it_is_ticked(app, client, cast):
    login_as(client, cast["engineer"])
    _import(client)
    code_id, revision_id = _only_code(app)
    edited = _changed("StCd_1001.st", "T#5000ms", "T#20ms")
    preview = _preview(client, [("StCd_1001.st", edited)])
    item = _item(preview)
    assert item["state"] == "changed" and item["action"] == "update"
    assert "set_delay" in item["changes"] and item["existing"]["lifecycle_state"] == "DRAFT"
    assert preview["summary"]["changed"] == 1 and preview["summary"]["ready"] == 0
    # the default confirmation takes only new programs: nothing is changed by accident
    assert client.post("/api/v1/imports/st", json={"token": preview["token"]}).status_code == 422
    preview = _preview(client, [("StCd_1001.st", edited)])
    assert (
        client.post(
            "/api/v1/imports/st", json={"token": preview["token"], "selected": [item["key"]]}
        ).status_code
        == 202
    )
    with app.app_context():
        code = db.session.get(StatusCode, code_id)
        assert len(code.revisions) == 1  # updated in place, no new revision
        assert code.revisions[0].set_delay == "20ms" and code.revisions[0].id == revision_id
    again = _preview(client, [("StCd_1001.st", edited)])
    assert _item(again)["state"] == "exists"  # and now it is the same


def test_a_changed_program_opens_a_new_revision_of_an_approved_code(app, client, cast):
    login_as(client, cast["engineer"])
    _import(client)
    code_id, revision_id = _only_code(app)
    cr_id = _cr_of(app, revision_id)
    domain_sign(client, cast, cr_id)
    assert submit(client, cast, cr_id).status_code == 200
    edited = _changed("StCd_1001.st", "T#5000ms", "T#20ms")

    # in review: a new revision is not possible, and the screen says so
    login_as(client, cast["engineer"])
    blocked = _item(_preview(client, [("StCd_1001.st", edited)]))
    assert blocked["state"] == "blocked" and "in review" in blocked["issues"][0]["message"]

    assert decide(client, cast["reviewer"], cr_id, "reviewer-signoff").status_code == 200
    assert decide(client, cast["admin"], cr_id, "admin-signoff").status_code == 200
    final = decide(client, cast["chief_engineer"], cr_id, "chief-engineer-decide")
    assert final.get_json()["state"] == "APPROVED"

    login_as(client, cast["engineer"])
    preview = _preview(client, [("StCd_1001.st", edited)])
    item = _item(preview)
    assert item["state"] == "changed" and item["action"] == "revise"
    assert item["existing"]["lifecycle_state"] == "APPROVED"
    response = client.post(
        "/api/v1/imports/st", json={"token": preview["token"], "selected": [item["key"]]}
    )
    assert response.status_code == 202 and response.get_json()["created_count"] == 1
    with app.app_context():
        code = db.session.get(StatusCode, code_id)
        states = {r.revision_number: r.lifecycle_status for r in code.revisions}
        assert states == {1: "APPROVED", 2: "DRAFT"}  # the approved one stays as it was
        new = next(r for r in code.revisions if r.revision_number == 2)
        assert new.set_delay == "20ms"
        cr = db.session.query(ChangeRequest).filter_by(status_code_revision_id=new.id).one()
        assert cr.cr_type == "REVISION" and cr.import_job_id and cr.change_set_id


def test_the_preview_screen_lists_the_choices_and_leaves_changed_programs_unticked(
    app, client, cast
):
    login_as(client, cast["engineer"])
    _import(client)
    edited = _changed("StCd_1001.st", "T#5000ms", "T#20ms")
    page = client.post(
        "/imports/st",
        data={"files": [(io.BytesIO(edited), "StCd_1001.st")]},
        content_type="multipart/form-data",
    ).get_data(as_text=True)
    assert "updates the open Draft" in page and "differs in" in page and "set_delay" in page
    assert "tick the ones you want to update" in page
    row = page.split('name="selected"', 1)[1].split(">", 1)[0]
    assert "checked" not in row and "disabled" not in row  # selectable, not ticked

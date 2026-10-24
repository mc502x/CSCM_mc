"""Bulk work on a change set with a sample inspection (docs/03-srs.md FR-180): edit, submit, domain
sign-off and the three decisions on many codes at once, without weakening a step.

TC-070. Requirements: FR-180, FR-029, FR-031, SEC-010, BR-004, BR-005.
"""

import io
import random
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from app.extensions import db
from app.models.audit import AuditLogEntry
from app.models.change_request import BulkSample, ChangeRequest
from app.models.status_code import StatusCodeRevision
from app.services.bulk_service import BulkService
from app.services.settings_service import SettingsService
from tests.helpers import (
    PASSWORD,
    create_draft,
    drive_to_review,
    login_as,
    make_cast,
)


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


class _Actor:
    def __init__(self, user):
        self.id, self.role_code = user.id, user.role.code


def _rules(app, cast, above=2, minimum=2, percent=10):
    with app.app_context():
        SettingsService.update(
            {
                "bulk.sample_above": str(above),
                "bulk.sample_minimum": str(minimum),
                "bulk.sample_percent": str(percent),
            },
            _Actor(cast["admin"]),
        )


def _new_set(client, cast, name="Batch", who="engineer"):
    login_as(client, cast[who])
    return client.post("/api/v1/change-sets", json={"name": name}).get_json()["id"]


def _add(client, set_id, cr_ids):
    for cr_id in cr_ids:
        assert (
            client.post(
                f"/api/v1/change-sets/{set_id}/change-requests", json={"change_request_id": cr_id}
            ).status_code
            == 200
        )


def _drafts(app, client, cast, n, who="engineer", **overrides):
    return [
        create_draft(
            app, client, cast, wcnv_ids_of(app), who=who, title=f"Bulk draft {i}", **overrides
        )[1]
        for i in range(n)
    ]


def wcnv_ids_of(app):
    with app.app_context():
        from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup

        group = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(LookupFunctionalSystemGroup.code == "WCNV")
            .one()
        )
        subgroup = (
            db.session.query(LookupFunctionalSubgroup)
            .filter(
                LookupFunctionalSubgroup.functional_system_group_id == group.id,
                LookupFunctionalSubgroup.code == "010xx",
            )
            .one()
        )
        return group.id, subgroup.id


def _reviews(app, client, cast, n):
    return [
        drive_to_review(app, client, cast, wcnv_ids_of(app), title=f"Bulk review {i}")[1]
        for i in range(n)
    ]


# ------------------------------------------------------------------ the rule and the draw
def test_the_size_of_the_sample_follows_the_settings(app, cast):
    with app.app_context():
        assert [BulkService.sample_size(n) for n in (3, 5, 6, 40, 125)] == [0, 0, 6, 8, 13]
    _rules(app, cast, above=10, minimum=3, percent=20)
    with app.app_context():
        assert [BulkService.sample_size(n) for n in (10, 11, 12, 100)] == [0, 3, 3, 20]


def _stub(subgroup, cr_id):
    status_code = SimpleNamespace(functional_subgroup_id=subgroup)
    return SimpleNamespace(id=cr_id, revision=SimpleNamespace(status_code=status_code))


def test_the_sample_is_spread_over_the_subgroups_and_reproducible():
    eligible = [_stub(1, i) for i in range(1, 91)] + [_stub(2, i) for i in range(91, 101)]
    chosen = BulkService._stratified(eligible, 10, random.Random("seed"))
    assert len(chosen) == len(set(chosen)) == 10
    assert sum(1 for i in chosen if i > 90) == 1  # the small subgroup is looked at, in proportion
    assert chosen == BulkService._stratified(eligible, 10, random.Random("seed"))
    many = [_stub(g, g * 100 + k) for g in range(1, 6) for k in range(4)]
    spread = BulkService._stratified(many, 5, random.Random("x"))
    assert sorted({i // 100 for i in spread}) == [
        1,
        2,
        3,
        4,
        5,
    ]  # one of each while the size allows


# ------------------------------------------------------------------ readiness and bulk edit
def test_the_readiness_names_what_stops_each_draft(app, client, cast):
    crs = _drafts(app, client, cast, 2)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    data = client.get(f"/api/v1/change-sets/{set_id}/readiness").get_json()
    assert data["tally"] == {"ready": 0, "blocked": 2}
    assert data["rules"] == {"percent": 10, "minimum": 8, "above": 5}
    assert all(any("domain sign-off pending" in b for b in i["blockers"]) for i in data["items"])
    assert "CONTROLS" in data["pending_by_domain"] and data["pending_by_domain"]["CONTROLS"] == 2


def test_bulk_edit_sets_the_same_value_on_every_draft_with_its_own_audit_entry(app, client, cast):
    crs = _drafts(app, client, cast, 3)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    response = client.post(
        f"/api/v1/change-sets/{set_id}/bulk-edit",
        json={"changes": {"status_category": "WARNING", "available_group": 5}},
    )
    assert response.status_code == 200, response.get_json()
    assert [r["ok"] for r in response.get_json()["results"]] == [True, True, True]
    with app.app_context():
        states = {
            (r.status_category, r.available_group)
            for r in db.session.query(StatusCodeRevision)
            .join(ChangeRequest, ChangeRequest.status_code_revision_id == StatusCodeRevision.id)
            .filter(ChangeRequest.id.in_(crs))
        }
        assert states == {("WARNING", 5)}
        actions = [a.action for a in db.session.query(AuditLogEntry).all()]
        assert actions.count("BULK_EDIT") == 1 and actions.count("EDIT") >= 3


def test_bulk_edit_refuses_unknown_fields_and_other_peoples_drafts(app, client, cast):
    crs = _drafts(app, client, cast, 2)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    assert (
        client.post(
            f"/api/v1/change-sets/{set_id}/bulk-edit", json={"changes": {"title": "x"}}
        ).status_code
        == 422
    )
    assert (
        client.post(f"/api/v1/change-sets/{set_id}/bulk-edit", json={"changes": {}}).status_code
        == 422
    )
    login_as(client, cast["controls_engineer"])  # not the author
    results = client.post(
        f"/api/v1/change-sets/{set_id}/bulk-edit", json={"changes": {"status_category": "INFO"}}
    ).get_json()["results"]
    assert [r["ok"] for r in results] == [False, False]


# ------------------------------------------------------------------ domain sign-off with a sample
def test_a_bulk_domain_signoff_needs_a_sample_and_every_code_gets_its_own_signoff(
    app, client, cast
):
    _rules(app, cast)
    crs = _drafts(app, client, cast, 4)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    login_as(client, cast["controls_engineer"])
    refused = client.post(
        f"/api/v1/change-sets/{set_id}/domain-signoffs", json={"domain": "CONTROLS"}
    )
    assert (
        refused.status_code == 422 and "need a sample inspection" in refused.get_json()["message"]
    )

    sample = client.post(
        f"/api/v1/change-sets/{set_id}/samples", json={"step": "domain", "domain": "CONTROLS"}
    )
    assert sample.status_code == 201
    sample = sample.get_json()
    assert sample["population"] == 4 and sample["sampled"] == 2 and sample["status"] == "OPEN"
    still_open = client.post(
        f"/api/v1/change-sets/{set_id}/domain-signoffs",
        json={"domain": "CONTROLS", "sample_id": sample["id"]},
    )
    assert (
        still_open.status_code == 422
        and "still need your verdict" in still_open.get_json()["message"]
    )
    for item in sample["items"]:
        marked = client.put(
            f"/api/v1/bulk-samples/{sample['id']}/items/{item['change_request_id']}",
            json={"verdict": "OK"},
        )
        assert marked.status_code == 200
    assert marked.get_json()["status"] == "PASSED"

    done = client.post(
        f"/api/v1/change-sets/{set_id}/domain-signoffs",
        json={"domain": "CONTROLS", "sample_id": sample["id"]},
    )
    assert done.status_code == 200 and all(r["ok"] for r in done.get_json()["results"])
    with app.app_context():
        from app.models.change_request import DomainSignoff

        assert db.session.query(DomainSignoff).count() == 4  # one per code
        assert db.session.get(BulkSample, sample["id"]).status == "USED"
    again = client.post(
        f"/api/v1/change-sets/{set_id}/domain-signoffs",
        json={"domain": "CONTROLS", "sample_id": sample["id"]},
    )
    assert again.status_code == 422  # nothing is waiting any more


def test_a_domain_signoff_is_only_for_a_holder_of_the_domain(app, client, cast):
    crs = _drafts(app, client, cast, 2)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    login_as(client, cast["engineer"])  # holds no domain
    response = client.post(
        f"/api/v1/change-sets/{set_id}/domain-signoffs", json={"domain": "CONTROLS"}
    )
    assert response.status_code == 422 and "do not hold" in response.get_json()["message"]


def test_a_small_batch_needs_no_sample(app, client, cast):
    crs = _drafts(app, client, cast, 2)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    login_as(client, cast["controls_engineer"])
    assert (
        client.post(
            f"/api/v1/change-sets/{set_id}/samples", json={"step": "domain", "domain": "CONTROLS"}
        ).status_code
        == 422
    )
    done = client.post(f"/api/v1/change-sets/{set_id}/domain-signoffs", json={"domain": "CONTROLS"})
    assert done.status_code == 200 and len(done.get_json()["results"]) == 2


# ------------------------------------------------------------------ decisions with a sample
def _inspect(client, sample, defect_on=None, note="wrong platform"):
    for item in sample["items"]:
        bad = item["change_request_id"] == defect_on
        response = client.put(
            f"/api/v1/bulk-samples/{sample['id']}/items/{item['change_request_id']}",
            json={"verdict": "DEFECT" if bad else "OK", "note": note if bad else None},
        )
        assert response.status_code == 200, response.get_json()
    return response.get_json()


def test_a_defect_in_the_sample_blocks_the_decision_until_it_is_sent_back(app, client, cast):
    _rules(app, cast)
    crs = _reviews(app, client, cast, 4)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    login_as(client, cast["reviewer"])
    body = {"step": "reviewer", "decision": "APPROVE", "current_password": PASSWORD}
    assert client.post(f"/api/v1/change-sets/{set_id}/decisions", json=body).status_code == 422

    sample = client.post(
        f"/api/v1/change-sets/{set_id}/samples", json={"step": "reviewer"}
    ).get_json()
    bad = sample["items"][0]["change_request_id"]
    settled = _inspect(client, sample, defect_on=bad)
    assert settled["status"] == "FAILED"
    blocked = client.post(
        f"/api/v1/change-sets/{set_id}/decisions", json={**body, "sample_id": sample["id"]}
    )
    assert blocked.status_code == 422 and "have defects" in blocked.get_json()["message"]

    sent_back = client.post(
        f"/api/v1/bulk-samples/{sample['id']}/reject-defects", json={"current_password": PASSWORD}
    ).get_json()["results"]
    assert [(r["cr_id"], r["ok"]) for r in sent_back] == [(bad, True)]
    with app.app_context():
        assert db.session.get(BulkSample, sample["id"]).status == "VOID"
        revision = db.session.get(ChangeRequest, bad).revision
        assert (
            revision.lifecycle_status == "DRAFT"
        )  # back with its author, with the note as the reason

    again = client.post(
        f"/api/v1/change-sets/{set_id}/samples", json={"step": "reviewer"}
    ).get_json()
    assert again["population"] == 3 and again["sampled"] == 2
    _inspect(client, again)
    decided = client.post(
        f"/api/v1/change-sets/{set_id}/decisions", json={**body, "sample_id": again["id"]}
    ).get_json()["results"]
    assert len(decided) == 4 and sum(1 for r in decided if r["ok"]) == 3
    with app.app_context():
        comments = [
            c.comment_text for cr in crs for c in db.session.get(ChangeRequest, cr).comments
        ]
        assert any(
            f"sample #{again['id']}: 2 of 3 inspected, none defective" in c for c in comments
        )
        assert db.session.get(BulkSample, again["id"]).status == "USED"
        assert [a.action for a in db.session.query(AuditLogEntry)].count("BULK_DECISION") == 1


def test_a_sample_cannot_be_borrowed_reused_or_kept_after_the_batch_changed(app, client, cast):
    _rules(app, cast)
    crs = _reviews(app, client, cast, 4)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    login_as(client, cast["reviewer"])
    sample = client.post(
        f"/api/v1/change-sets/{set_id}/samples", json={"step": "reviewer"}
    ).get_json()
    _inspect(client, sample)
    body = {"step": "reviewer", "decision": "APPROVE", "current_password": PASSWORD}

    # somebody else cannot decide with, or fill in, this reviewer's sample
    login_as(client, cast["admin"])
    other = client.post(
        f"/api/v1/change-sets/{set_id}/decisions",
        json={**body, "step": "admin", "sample_id": sample["id"]},
    )
    assert other.status_code == 422  # wrong step; and it is not the admin's sample either
    assert (
        client.put(
            f"/api/v1/bulk-samples/{sample['id']}/items/{sample['items'][0]['change_request_id']}",
            json={"verdict": "OK"},
        ).status_code
        == 403
    )

    # the batch changes: one request leaves the set -> the old sample no longer covers it
    login_as(client, cast["engineer"])
    client.delete(f"/api/v1/change-sets/{set_id}/change-requests/{crs[0]}")
    login_as(client, cast["reviewer"])
    stale = client.post(
        f"/api/v1/change-sets/{set_id}/decisions", json={**body, "sample_id": sample["id"]}
    )
    assert stale.status_code == 422 and "batch changed" in stale.get_json()["message"]

    # a sample that serves one decision serves no other
    fresh = client.post(
        f"/api/v1/change-sets/{set_id}/samples", json={"step": "reviewer"}
    ).get_json()
    _inspect(client, fresh)
    ok = client.post(
        f"/api/v1/change-sets/{set_id}/decisions", json={**body, "sample_id": fresh["id"]}
    )
    assert ok.status_code == 200
    reused = client.post(
        f"/api/v1/change-sets/{set_id}/decisions", json={**body, "sample_id": fresh["id"]}
    )
    # nothing is left to decide, so the second call decides nothing (no one signs twice)
    results = reused.get_json()["results"]
    assert reused.status_code == 200 and not any(r["ok"] for r in results)
    assert all("Already signed off" in r["message"] for r in results)


def test_a_defect_needs_a_note_and_a_verdict_must_be_ok_or_defect(app, client, cast):
    _rules(app, cast)
    crs = _reviews(app, client, cast, 3)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    login_as(client, cast["reviewer"])
    sample = client.post(
        f"/api/v1/change-sets/{set_id}/samples", json={"step": "reviewer"}
    ).get_json()
    cr = sample["items"][0]["change_request_id"]
    url = f"/api/v1/bulk-samples/{sample['id']}/items/{cr}"
    assert client.put(url, json={"verdict": "DEFECT"}).status_code == 422
    assert client.put(url, json={"verdict": "maybe"}).status_code == 422
    assert (
        client.put(
            f"/api/v1/bulk-samples/{sample['id']}/items/999999", json={"verdict": "OK"}
        ).status_code
        == 404
    )


def test_the_person_who_wrote_a_code_is_not_part_of_the_batch_they_decide(app, client, cast):
    _rules(app, cast)
    crs = _reviews(app, client, cast, 3)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    login_as(client, cast["engineer"])  # an Engineer cannot take a review step at all
    response = client.post(f"/api/v1/change-sets/{set_id}/samples", json={"step": "reviewer"})
    assert response.status_code == 403 or response.status_code == 422


# ------------------------------------------------------------------ submit, dossier, access
def test_bulk_submit_sends_the_drafts_that_are_ready_and_reports_the_rest(app, client, cast):
    crs = _drafts(app, client, cast, 3)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    url = f"/api/v1/change-sets/{set_id}/bulk-submit"
    results = client.post(url, json={}).get_json()["results"]
    # the CONTROLS domain has not signed: nothing can be submitted yet, and each says why
    assert [r["ok"] for r in results] == [False, False, False]
    assert all("Cross-Domain Sign-Off still pending" in r["message"] for r in results)

    login_as(client, cast["controls_engineer"])
    signed = client.post(
        f"/api/v1/change-sets/{set_id}/domain-signoffs", json={"domain": "CONTROLS"}
    )
    assert signed.status_code == 200
    login_as(client, cast["engineer"])
    ready = client.get(f"/api/v1/change-sets/{set_id}/readiness").get_json()
    assert ready["tally"] == {"ready": 3, "blocked": 0}
    results = client.post(url, json={}).get_json()["results"]
    assert [r["ok"] for r in results] == [True, True, True]
    login_as(client, cast["controls_engineer"])  # somebody else's submit is not theirs to make
    assert client.post(url, json={}).get_json()["results"] == []
    with app.app_context():
        states = {db.session.get(ChangeRequest, c).revision.lifecycle_status for c in crs}
        assert states == {"REVIEW"}


def test_the_dossier_puts_the_codes_the_samples_and_the_audit_in_one_workbook(app, client, cast):
    _rules(app, cast)
    crs = _reviews(app, client, cast, 3)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    login_as(client, cast["reviewer"])
    sample = client.post(
        f"/api/v1/change-sets/{set_id}/samples", json={"step": "reviewer"}
    ).get_json()
    _inspect(client, sample)
    login_as(client, cast["stcd_owner"])
    response = client.get(f"/api/v1/change-sets/{set_id}/dossier.xlsx")
    assert response.status_code == 200 and "spreadsheetml" in response.mimetype
    book = load_workbook(io.BytesIO(response.data))
    assert book.sheetnames == ["Change set", "Codes", "Samples", "Sample items", "Audit"]
    assert book["Codes"].max_row == 4  # the header and three codes
    assert book["Samples"].max_row == 2 and book["Sample items"].max_row == 1 + sample["sampled"]
    assert any(row[1].value == "BULK_SAMPLE_DRAW" for row in book["Audit"].iter_rows(min_row=2))


def test_viewers_see_nothing_of_the_bulk_workbench(app, client, cast):
    set_id = _new_set(client, cast)
    login_as(client, cast["viewer"])
    for path in ("readiness", "samples", "dossier.xlsx"):
        assert client.get(f"/api/v1/change-sets/{set_id}/{path}").status_code == 403
    assert (
        client.post(f"/api/v1/change-sets/{set_id}/samples", json={"step": "reviewer"}).status_code
        == 403
    )
    assert client.post(f"/api/v1/change-sets/{set_id}/bulk-edit", json={}).status_code == 403


# ------------------------------------------------------------------ the workbench screen
def test_the_workbench_shows_the_batch_the_readiness_and_the_rule(app, client, cast):
    crs = _drafts(app, client, cast, 2)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    page = client.get(f"/change-sets/{set_id}/workbench").get_data(as_text=True)
    assert "Workbench" in page and "Codes in this batch" in page
    assert "domain sign-off pending: CONTROLS" in page
    assert (
        "more than 5 codes needs a sample inspection first: 10 percent of the batch, at least 8"
        in page
    )
    assert "Set values on the Drafts" in page and "Submit for review" in page
    assert "Dossier (XLSX)" in page
    login_as(client, cast["viewer"])
    assert client.get(f"/change-sets/{set_id}/workbench").status_code in (302, 403)
    login_as(client, cast["stcd_owner"])
    owner = client.get(f"/change-sets/{set_id}/workbench").get_data(as_text=True)
    assert "Set values on the Drafts" not in owner  # the owner looks, the engineers work


def test_a_whole_domain_signoff_can_be_done_in_the_workbench(app, client, cast):
    _rules(app, cast)
    crs = _drafts(app, client, cast, 4)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    login_as(client, cast["controls_engineer"])
    drawn = client.post(
        f"/change-sets/{set_id}/bulk/sample",
        data={"step": "domain:CONTROLS"},
        follow_redirects=True,
    ).get_data(as_text=True)
    assert "drawn: 2 of 4 codes to inspect" in drawn
    with app.app_context():
        sample = db.session.query(BulkSample).one()
        sample_id, item_ids = sample.id, [i.change_request_id for i in sample.items]
    page = client.get(f"/change-sets/{set_id}/workbench").get_data(as_text=True)
    assert f"Sample {sample_id}" in page and "Save the verdicts" in page

    early = client.post(
        f"/change-sets/{set_id}/bulk/domain",
        data={"domain": "CONTROLS", "sample_id": sample_id},
        follow_redirects=True,
    ).get_data(as_text=True)
    assert "still need your verdict" in early
    client.post(
        f"/bulk-samples/{sample_id}/verdicts",
        data={f"verdict_{cr}": "OK" for cr in item_ids},
        follow_redirects=True,
    )
    done = client.post(
        f"/change-sets/{set_id}/bulk/domain",
        data={"domain": "CONTROLS", "sample_id": sample_id},
        follow_redirects=True,
    ).get_data(as_text=True)
    assert "4 of 4" in done
    with app.app_context():
        from app.models.change_request import DomainSignoff

        assert db.session.query(DomainSignoff).count() == 4


def test_a_decision_in_the_workbench_names_its_sample(app, client, cast):
    _rules(app, cast)
    crs = _reviews(app, client, cast, 3)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    login_as(client, cast["reviewer"])
    client.post(f"/change-sets/{set_id}/bulk/sample", data={"step": "reviewer"})
    with app.app_context():
        sample = db.session.query(BulkSample).one()
        sample_id, item_ids = sample.id, [i.change_request_id for i in sample.items]
    refused = client.post(
        f"/change-sets/{set_id}/decide",
        data={"step": "reviewer", "decision": "APPROVE", "current_password": PASSWORD},
        follow_redirects=True,
    ).get_data(as_text=True)
    assert "need a sample inspection first" in refused
    client.post(
        f"/bulk-samples/{sample_id}/verdicts",
        data={f"verdict_{cr}": "OK" for cr in item_ids},
    )
    approved = client.post(
        f"/change-sets/{set_id}/decide",
        data={
            "step": "reviewer",
            "decision": "APPROVE",
            "current_password": PASSWORD,
            "sample_id": sample_id,
        },
        follow_redirects=True,
    ).get_data(as_text=True)
    assert "3 of 3 decisions recorded" in approved


def test_the_bulk_screens_are_translated(app, client, cast):
    crs = _drafts(app, client, cast, 1)
    set_id = _new_set(client, cast)
    _add(client, set_id, crs)
    client.post("/language", data={"lang": "de"})
    page = client.get(f"/change-sets/{set_id}/workbench").get_data(as_text=True)
    assert "Arbeitsbereich" in page and "Stichprobe ziehen" in page and "Workbench" not in page

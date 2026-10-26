"""Remaining spec checks: SEC-010 service-layer authorization, FR-010/011/011a/014
user administration audit, FR-005 auth-provider seam, FR-048d legacy reference,
FR-021 non-binding preview, NFR-008 egress-blocked operation, FR-038."""

import csv
import io
import socket

import pytest

from app.auth.providers import AuthenticatedUser, SessionPasswordAuthProvider
from app.domain.errors import ForbiddenError
from app.extensions import db
from app.models.audit import AuditLogEntry
from app.services.change_request_service import ChangeRequestService
from app.services.export_service import ExportService
from app.services.lookup_admin_service import LookupAdminService
from app.services.release_service import ReleaseService
from app.services.status_code_service import StatusCodeService
from app.services.user_service import UserService
from tests.helpers import (
    PASSWORD,
    decide,
    drive_to_approved,
    drive_to_review,
    login_as,
    make_cast,
    release_revisions,
)


def _actor(role_code: str) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=999,
        username="x",
        email="x@example.com",
        full_name="X",
        role_code=role_code,
    )


# ---- SEC-010 ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "call,wrong_role",
    [
        (lambda a: ChangeRequestService.reviewer_signoff(1, a, "APPROVE", None), "ENGINEER"),
        (lambda a: ChangeRequestService.admin_signoff(1, a, "APPROVE", None), "REVIEWER"),
        (
            lambda a: ChangeRequestService.chief_engineer_decide(1, a, "APPROVE", None),
            "ADMINISTRATOR",
        ),
        (lambda a: ChangeRequestService.assign_reviewer(1, None, a), "REVIEWER"),
        (lambda a: ChangeRequestService.add_comment(1, a, "hello"), "ENGINEER"),
        (lambda a: ReleaseService.create({"name": "n", "version_label": "v"}, a), "ENGINEER"),
        (lambda a: ReleaseService.publish(1, a), "CHIEF_ENGINEER"),
        (lambda a: ReleaseService.delete(1, a), "REVIEWER"),
        (lambda a: StatusCodeService.archive(1, a), "ENGINEER"),
        (lambda a: StatusCodeService.reinstate(1, "reason here", a), "ENGINEER"),
        (lambda a: StatusCodeService.delete_sandbox(1, a), "ENGINEER"),
        (lambda a: StatusCodeService.create_draft({}, a), "VIEWER"),
        (lambda a: ExportService.export_full_database(a), "CHIEF_ENGINEER"),
        (lambda a: ExportService.working_set_revisions(a), "VIEWER"),
        (lambda a: LookupAdminService.create_value("turbine-platforms", {}, a), "ENGINEER"),
        (lambda a: UserService.force_reset_password(1, "irrelevant", a), "ENGINEER"),
    ],
)
def test_services_enforce_roles_independently_of_route_decorators(app, call, wrong_role):
    with app.app_context():
        with pytest.raises(ForbiddenError):
            call(_actor(wrong_role))


# ---- FR-010 / FR-011 / FR-011a / FR-014 ----------------------------------------------------------


def _audit_actions(app):
    with app.app_context():
        return [a for (a,) in db.session.query(AuditLogEntry.action).order_by(AuditLogEntry.id)]


def test_user_administration_events_are_audited(app, client, make_user):
    admin = make_user("ADMINISTRATOR")
    make_user("ADMINISTRATOR")  # so the first can be deactivated later if needed
    target = make_user("ENGINEER")
    login_as(client, admin)

    url = f"/api/v1/users/{target.id}"
    assert client.patch(url, json={"role": "REVIEWER"}).get_json()["role"] == "REVIEWER"
    assert client.patch(url, json={"engineering_domains": ["CONTROLS"]}).status_code == 200
    assert client.patch(url, json={"is_active": False}).status_code == 200
    assert client.patch(url, json={"is_active": True}).status_code == 200
    assert client.patch(url, json={"full_name": "Renamed Person"}).status_code == 200
    assert client.patch(url, json={"role": "NOT_A_ROLE"}).status_code == 422
    reset = client.post(
        f"/api/v1/users/{target.id}/force-reset-password",
        json={"new_password": "another genuinely long one"},
    )
    assert reset.status_code in (200, 204)

    actions = _audit_actions(app)
    for expected in (
        "ROLE_CHANGE",
        "DOMAIN_TAG_CHANGE",
        "USER_DEACTIVATE",
        "USER_UPDATE",
        "PASSWORD_RESET",
    ):
        assert expected in actions, expected


def test_a_user_holds_exactly_one_role(app, client, make_user):
    admin = make_user("ADMINISTRATOR")
    target = make_user("ENGINEER")
    login_as(client, admin)
    body = client.patch(f"/api/v1/users/{target.id}", json={"role": ["ENGINEER", "REVIEWER"]})
    assert body.status_code in (422, 400)
    assert client.get(f"/api/v1/users/{target.id}").get_json()["role"] == "ENGINEER"


def test_account_lock_and_password_events_are_audited(app, client, make_user):
    user = make_user("ENGINEER")
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"username": user.username, "password": "wrong"})
    assert "ACCOUNT_LOCKED" in _audit_actions(app)

    admin = make_user("ADMINISTRATOR")
    login_as(client, admin)
    changed = client.post(
        "/api/v1/users/me/change-password",
        json={"current_password": PASSWORD, "new_password": "a brand new long passphrase"},
    )
    assert changed.status_code in (200, 204)
    assert "PASSWORD_CHANGE" in _audit_actions(app)


# ---- FR-005 -----------------------------------------------------------------------------------


def test_auth_provider_seam_is_substitutable(app, make_user):
    """Callers depend on AuthenticatedUser only: a different provider returning
    the same shape needs no change downstream (FR-005)."""

    class FakeDirectoryProvider:
        def authenticate(self, credentials):
            return AuthenticatedUser(
                id=1, username="ad.user", email="a@corp", full_name="AD User", role_code="VIEWER"
            )

        def get_login_url(self):
            return "https://adfs.corp.example/login"

    user = make_user("ENGINEER")
    with app.app_context():
        from app.models.user import User

        model = db.session.get(User, user.id)
        local = SessionPasswordAuthProvider().authenticate({"user": model, "password": PASSWORD})
        assert local is not None and local.role_code == "ENGINEER"
        assert (
            SessionPasswordAuthProvider().authenticate({"user": model, "password": "nope"}) is None
        )
        assert SessionPasswordAuthProvider().get_login_url() is None
    directory = FakeDirectoryProvider().authenticate({})
    assert isinstance(directory, AuthenticatedUser) and directory.role_code == "VIEWER"


# ---- FR-048d / FR-021 / FR-038 ---------------------------------------------------------------


def test_import_preserves_legacy_reference_number(app, client, make_user):
    cast = make_cast(make_user)
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=[
            "functional_system_group",
            "functional_subgroup",
            "turbine_platforms",
            "title",
            "description",
            "status_category",
            "available_group",
            "set_delay",
            "reset_delay",
            "legacy_reference_number",
        ],
    )
    writer.writeheader()
    writer.writerow(
        {
            "functional_system_group": "WCNV",
            "functional_subgroup": "010xx",
            "turbine_platforms": "3XM",
            "title": "Legacy converter code",
            "description": "Imported with a legacy reference number.",
            "status_category": "ERROR",
            "available_group": "27",
            "set_delay": "10ms",
            "reset_delay": "2min",
            "legacy_reference_number": "L-4711",
        }
    )
    login_as(client, cast["engineer"])
    client.post(
        "/api/v1/imports",
        data={"file": (io.BytesIO(buffer.getvalue().encode()), "lib.csv")},
        content_type="multipart/form-data",
    )
    item = client.get("/api/v1/status-codes").get_json()["items"][0]
    assert item["legacy_reference_number"] == "L-4711"
    assert item["status_code_identifier"] is None  # never confused with the governed identifier


def test_next_available_preview_does_not_reserve_a_number(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    login_as(client, cast["engineer"])
    url = "/api/v1/status-codes/next-available"
    query = {"functional_system_group": wcnv_ids[0], "functional_subgroup": wcnv_ids[1]}
    first = client.get(url, query_string=query).get_json()["preview_identifier"]
    second = client.get(url, query_string=query).get_json()["preview_identifier"]
    assert first == second == "StCd-01000"
    assert client.get(url).status_code == 422

    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    assert client.get(url, query_string=query).get_json()["preview_identifier"] == "StCd-01001"


def test_comment_leaves_state_and_signoffs_untouched(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, cr_id = drive_to_review(app, client, cast, wcnv_ids)
    decide(client, cast["reviewer"], cr_id, "reviewer-signoff")
    login_as(client, cast["chief_engineer"])
    client.post(f"/api/v1/change-requests/{cr_id}/comments", json={"comment": "FYI only."})
    cr = client.get(f"/api/v1/change-requests/{cr_id}").get_json()
    assert cr["state"] == "REVIEW"
    assert [c["decision"] for c in cr["comments"]] == ["REVIEWER_APPROVE", None]


# ---- NFR-008 egress-blocked operation ---------------------------------------------------------


def test_whole_lifecycle_works_with_all_outbound_network_blocked(
    app, client, make_user, wcnv_ids, monkeypatch
):
    """The application must keep operating when it can reach nothing beyond
    itself (docs/14-deployment-architecture.md §1)."""

    def blocked(*args, **kwargs):
        raise OSError("outbound network access is blocked in this test")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)

    cast = make_cast(make_user)
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids)
    release_revisions(client, cast, [revision["id"]])
    login_as(client, cast["viewer"])
    for fmt in ("csv", "json", "xlsx", "pdf"):
        assert client.get(f"/api/v1/exports/released?format={fmt}").status_code == 200
    login_as(client, cast["admin"])
    assert client.post("/api/v1/exports/full-database").status_code == 200
    assert client.get("/exports").status_code in (200, 302)

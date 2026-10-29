"""What the API fuzz found (v4.18.1): an identifier wider than the database's integers is a missing
resource and not a server error, a text with control characters is refused before it is stored, and
a control character that is stored anyway cannot break a workbook.

TC-081. Requirements: FR-200, SEC-020, NFR-006.
"""

import pytest

from app.extensions import db
from app.models.lookup import LookupEngineeringDomain
from app.utils import xlsx_text
from tests.helpers import login_as, make_cast, valid_payload


@pytest.fixture()
def cast(client, make_user):
    return make_cast(make_user)


HUGE = 2**70


@pytest.mark.parametrize(
    "path",
    [
        f"/api/v1/status-codes/{HUGE}",
        f"/api/v1/change-requests/{HUGE}",
        f"/api/v1/users/{HUGE}",
        f"/api/v1/releases/{HUGE}",
        f"/api/v1/mapping/{HUGE}",
        f"/api/v1/mapping-changes/{HUGE}",
        f"/api/v1/packages/{HUGE}",
        f"/status-codes/{HUGE}",
        f"/mapping/{HUGE}",
    ],
)
def test_an_identifier_wider_than_the_database_is_not_found(client, cast, path):
    login_as(client, cast["admin"])
    assert client.get(path).status_code == 404


def test_a_huge_identifier_in_a_body_is_not_a_server_error(client, cast):
    login_as(client, cast["admin"])
    response = client.post("/api/v1/change-requests/withdraw", json={"cr_ids": [HUGE]})
    assert response.status_code < 500


def test_a_text_with_control_characters_is_refused_everywhere(client, cast, wcnv_ids):
    login_as(client, cast["engineer"])
    bad = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, title="Converter\x08 trip")
    )
    assert bad.status_code == 422 and "control characters" in bad.get_json()["message"]
    nested = client.post(
        "/api/v1/mapping-changes",
        json={"title": "t", "reason": "r\x00", "items": [{"action": "ADD", "fields": {}}]},
    )
    assert nested.status_code == 422
    form = client.post("/saved-searches", data={"name": "a\x1fb", "q": "x"})
    assert form.status_code == 422
    ok = client.post(
        "/api/v1/status-codes",
        json=valid_payload(*wcnv_ids, description="Line one.\nLine two.\tTabbed text is fine."),
    )
    assert ok.status_code == 201, ok.get_json()


def test_a_password_may_hold_anything(client, make_user):
    user = make_user("ENGINEER")
    response = client.post(
        "/api/v1/auth/login", json={"username": user.username, "password": "wrong\x01pass"}
    )
    assert response.status_code == 401  # refused as a wrong password, not as bad text


def test_a_worksheet_never_gets_a_character_it_cannot_hold(app, client, cast):
    assert xlsx_text("a\x08b\x00c\td\ne") == "abc\td\ne" and xlsx_text(5) == 5
    with app.app_context():  # stored before the check existed, or by a script
        db.session.add(
            LookupEngineeringDomain(code="BAD\x08CODE", label="Bad\x01 label", is_active=1)
        )
        db.session.commit()
    login_as(client, cast["admin"])
    assert client.get("/api/v1/imports/template?format=xlsx").status_code == 200

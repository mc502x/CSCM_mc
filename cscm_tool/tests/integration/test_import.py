"""FR-048a-d, EPIC-14: CSV/XLSX library import, still fully governed
(docs/05-governance-handbook.md §6b)."""

import io

from app.extensions import db
from app.models.change_request import ChangeRequest


def _login_as(client, user, password="a genuinely long passphrase"):
    resp = client.post("/api/v1/auth/login", json={"username": user.username, "password": password})
    assert resp.status_code == 200
    return resp


def _csv_bytes(rows: list[dict]) -> bytes:
    import csv

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def _valid_row(group_code="WCNV", subgroup_code="010xx", **overrides):
    row = {
        "functional_system_group": group_code,
        "functional_subgroup": subgroup_code,
        "turbine_platforms": "3XM;4XM",
        "title": "Imported Converter Fault",
        "description": "Imported via CSV library import smoke test.",
        "status_category": "ERROR",
        "available_group": "27",
        "set_delay": "10ms",
        "reset_delay": "2min",
        "legacy_reference_number": "3000",
    }
    row.update(overrides)
    return row


def test_non_admin_engineer_can_upload_import(client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    csv_bytes = _csv_bytes([_valid_row()])
    response = client.post(
        "/api/v1/imports",
        data={"file": (io.BytesIO(csv_bytes), "library.csv")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 202
    body = response.get_json()
    assert body["row_count"] == 1
    assert body["created_count"] == 1
    assert body["error_count"] == 0
    assert body["status"] == "COMPLETE"


def test_viewer_cannot_upload_import(client, make_user):
    viewer = make_user("VIEWER")
    _login_as(client, viewer)

    csv_bytes = _csv_bytes([_valid_row()])
    response = client.post(
        "/api/v1/imports",
        data={"file": (io.BytesIO(csv_bytes), "library.csv")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 403


def test_imported_row_becomes_import_type_draft_change_request(app, client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    csv_bytes = _csv_bytes([_valid_row()])
    body = client.post(
        "/api/v1/imports",
        data={"file": (io.BytesIO(csv_bytes), "library.csv")},
        content_type="multipart/form-data",
    ).get_json()

    with app.app_context():
        cr = db.session.query(ChangeRequest).filter(ChangeRequest.import_job_id == body["id"]).one()
        assert cr.cr_type == "IMPORT"
        assert cr.revision.lifecycle_status == "DRAFT"
        assert cr.revision.status_code.legacy_reference_number == "3000"


def test_invalid_row_is_reported_and_creates_nothing(client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    rows = [_valid_row(title="Row One"), _valid_row(title="Row Two", set_delay="not-a-delay")]
    csv_bytes = _csv_bytes(rows)
    response = client.post(
        "/api/v1/imports",
        data={"file": (io.BytesIO(csv_bytes), "library.csv")},
        content_type="multipart/form-data",
    )
    body = response.get_json()
    assert body["row_count"] == 2
    assert body["created_count"] == 1
    assert body["error_count"] == 1
    assert body["error_report_reference"]

    errors_resp = client.get(f"/api/v1/imports/{body['id']}/errors")
    assert errors_resp.status_code == 200
    assert b"set_delay" in errors_resp.data


def test_unknown_functional_system_group_code_reported_as_error(client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    csv_bytes = _csv_bytes([_valid_row(group_code="NOPE")])
    response = client.post(
        "/api/v1/imports",
        data={"file": (io.BytesIO(csv_bytes), "library.csv")},
        content_type="multipart/form-data",
    )
    body = response.get_json()
    assert body["created_count"] == 0
    assert body["error_count"] == 1


def test_ambiguous_group_code_requires_range_hint(client, make_user):
    """WTUR is reused for a second, numerically distinct Hub Controller
    group — importing it bare must fail with a helpful message, and
    succeed once the disambiguating range hint is supplied."""
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    ambiguous = _valid_row(group_code="WTUR", subgroup_code="090xx")
    csv_bytes = _csv_bytes([ambiguous])
    response = client.post(
        "/api/v1/imports",
        data={"file": (io.BytesIO(csv_bytes), "library.csv")},
        content_type="multipart/form-data",
    )
    body = response.get_json()
    assert body["created_count"] == 0
    assert body["error_count"] == 1

    disambiguated = _valid_row(group_code="WTUR", subgroup_code="090xx")
    disambiguated["functional_system_group_range_start"] = "9000"
    csv_bytes = _csv_bytes([disambiguated])
    response = client.post(
        "/api/v1/imports",
        data={"file": (io.BytesIO(csv_bytes), "library.csv")},
        content_type="multipart/form-data",
    )
    body = response.get_json()
    assert body["created_count"] == 1
    assert body["error_count"] == 0


def test_unsupported_file_extension_rejected(client, make_user):
    engineer = make_user("ENGINEER")
    _login_as(client, engineer)

    response = client.post(
        "/api/v1/imports",
        data={"file": (io.BytesIO(b"not a real file"), "library.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 422

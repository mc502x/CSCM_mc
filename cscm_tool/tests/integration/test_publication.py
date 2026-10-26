"""Publishing the catalogue (docs/21-improvement-ideas.md): I-02 profiles and wrapped PDF, I-03
audiences, I-06 manifests / bundles / verification / release notes, I-07 software versions,
I-15 translations, I-24 offline bundle.

TC-042. Requirements: FR-100, FR-101, FR-102, FR-103, FR-104, FR-105, FR-106, FR-107, FR-108, FR-110, FR-111, BR-016, BR-018, BR-021.
"""

import io
import json
import re
import zipfile

import pytest

from app.export import pdf_exporter
from app.extensions import db
from app.services import manifest_service
from tests.helpers import (
    PASSWORD,
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


def _lookup_id(client, vocabulary, code):
    return next(
        v["id"] for v in client.get(f"/api/v1/lookups/{vocabulary}").get_json() if v["code"] == code
    )


def _release_with(app, client, cast, wcnv_ids, specs, label="R1"):
    """Drive one code per spec (payload overrides) to Approved, publish them in one Release."""
    revision_ids = [
        drive_to_approved(app, client, cast, wcnv_ids, **spec)[0]["id"] for spec in specs
    ]
    return release_revisions(client, cast, revision_ids, label=label)


def _csv_rows(response):
    import csv

    return list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))


# ---------------------------------------------------------------- profiles (I-02)
def test_three_profiles_are_seeded_and_shape_the_columns(app, client, cast, wcnv_ids):
    release_id = _release_with(
        app, client, cast, wcnv_ids, [{"title": "Grid trip", "remedy_text": "Reset the converter."}]
    )
    login_as(client, cast["viewer"])
    codes = [p["code"] for p in client.get("/api/v1/export-profiles").get_json()["items"]]
    assert codes == ["SERVICE_MANUAL", "SCADA_TAGS", "CUSTOMER_LIST"]

    response = client.get(f"/api/v1/releases/{release_id}/export?format=csv&profile=SERVICE_MANUAL")
    rows = _csv_rows(response)
    assert list(rows[0]) == [
        "Status code",
        "Title",
        "Description",
        "Category",
        "Set delay",
        "Reset delay",
        "Remedy",
    ]
    assert rows[0]["Remedy"] == "Reset the converter."
    as_json = client.get(
        f"/api/v1/releases/{release_id}/export?format=json&profile=SCADA_TAGS"
    ).get_json()
    assert set(as_json[0]) == {
        "status_code_identifier",
        "logical_node",
        "node_value",
        "title",
        "status_category",
        "alarm_flag",
    }  # machine consumers keep the stable field names
    assert (
        client.get(f"/api/v1/releases/{release_id}/export?format=csv&profile=NOPE").status_code
        == 404
    )


def test_administrator_manages_profiles_as_data(app, client, cast):
    login_as(client, cast["admin"])
    created = client.post(
        "/api/v1/export-profiles",
        json={
            "code": "short_list",
            "name": "Short list",
            "columns": [
                {"field": "status_code_identifier", "label": "No."},
                {"field": "title", "label": "Text"},
            ],
            "pdf_orientation": "P",
        },
    )
    assert created.status_code == 201 and created.get_json()["code"] == "SHORT_LIST"
    bad_field = client.post(
        "/api/v1/export-profiles",
        json={"code": "BAD", "name": "x", "columns": [{"field": "password_hash", "label": "x"}]},
    )
    assert bad_field.status_code == 422
    assert (
        client.post(
            "/api/v1/export-profiles",
            json={
                "code": "SHORT_LIST",
                "name": "again",
                "columns": [{"field": "title", "label": "t"}],
            },
        ).status_code
        == 422
    )
    updated = client.patch(
        f"/api/v1/export-profiles/{created.get_json()['id']}", json={"is_active": False}
    )
    assert updated.status_code == 200
    assert "SHORT_LIST" not in [
        p["code"] for p in client.get("/api/v1/export-profiles").get_json()["items"]
    ]
    assert "SHORT_LIST" in [
        p["code"]
        for p in client.get("/api/v1/export-profiles?include_inactive=true").get_json()["items"]
    ]
    login_as(client, cast["engineer"])
    assert client.post("/api/v1/export-profiles", json={}).status_code == 403


def test_export_profile_fields_match_the_export_row(app, client, cast, wcnv_ids):
    from app.services.export_profile_service import EXPORT_FIELDS
    from app.services.export_service import flatten_revision

    revision, _ = drive_to_approved(app, client, cast, wcnv_ids)
    with app.app_context():
        from app.models.status_code import StatusCodeRevision

        row = flatten_revision(db.session.get(StatusCodeRevision, revision["id"]))
    assert set(row) | {"content_language", "access_level", "audience"} == set(EXPORT_FIELDS)


# ---------------------------------------------------------------- wrapped PDF (I-02)
def _drawn_text(monkeypatch) -> list[str]:
    """The strings the PDF exporter draws (the page content holds glyph ids, not text)."""
    drawn: list[str] = []
    original = pdf_exporter._CataloguePdf.cell

    def spy(self, *args, **kwargs):
        text = args[2] if len(args) > 2 else kwargs.get("text", "")
        drawn.append(text)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(pdf_exporter._CataloguePdf, "cell", spy)
    return drawn


def test_pdf_cells_are_wrapped_not_truncated(app, client, cast, wcnv_ids, monkeypatch):
    drawn = _drawn_text(monkeypatch)
    tail = "ENDMARKER-the-very-last-words-of-the-description"
    long_description = ("The converter DC-link voltage has stayed below the limit. " * 12) + tail
    release_id = _release_with(
        app, client, cast, wcnv_ids, [{"title": "Long text", "description": long_description}]
    )
    login_as(client, cast["viewer"])
    pdf = client.get(f"/api/v1/releases/{release_id}/export?format=pdf").data
    assert pdf.startswith(b"%PDF")
    text = "".join(drawn)
    # (hyphens are break opportunities, so the tail may be split across two lines)
    assert "ENDMARKER" in text and "the-description" in text
    assert "Page 1 of" in text or "Page 1" in text
    assert "Content digest" in text  # title page of a release export


def test_pdf_survives_characters_no_font_has(app):
    rows = [
        {
            "status_code_identifier": "StCd-00001",
            "title": "Ω-Wert → ≥ 3 µs „ok“ 😀",
            "description": "d" * 20,
        }
    ]
    pdf = pdf_exporter.build_pdf(
        rows, columns=[("status_code_identifier", "ID"), ("title", "Title")]
    )
    assert pdf.startswith(b"%PDF")
    # a character no bundled font draws becomes a stand-in instead of an empty gap
    assert pdf_exporter.clean("a → b ≥ 😀") == "a -> b >= ?"
    assert pdf_exporter.clean(None) == "" and pdf_exporter.clean(True) == "Yes"


def test_pdf_column_widths_fit_the_page(app):
    rows = [{"a": "x" * 80, "b": "y", "c": "zz"}] * 3
    widths = pdf_exporter.column_widths([("a", "A"), ("b", "B"), ("c", "C")], rows, 277.0)
    assert abs(sum(widths) - 277.0) < 0.01 and widths[0] > widths[1]
    many = pdf_exporter.column_widths([(str(i), str(i)) for i in range(40)], [{}], 277.0)
    assert abs(sum(many) - 277.0) < 0.01  # more columns than fit: equal share, never overflow


# ---------------------------------------------------------------- audiences (I-03)
def test_audience_export_only_contains_codes_the_audience_may_see(app, client, cast, wcnv_ids):
    login_as(client, cast["engineer"])
    standard = _lookup_id(client, "customer-access", "STANDARD")
    covert = _lookup_id(client, "customer-access", "COVERT")
    release_id = _release_with(
        app,
        client,
        cast,
        wcnv_ids,
        [
            {"title": "Visible to customers", "customer_access": standard},
            {"title": "Covert for customers", "customer_access": covert},
            {"title": "No customer value at all"},
        ],
    )
    login_as(client, cast["viewer"])
    rows = _csv_rows(
        client.get(f"/api/v1/releases/{release_id}/export?format=csv&audience=customer")
    )
    assert [r["title"] for r in rows] == ["Visible to customers"]
    assert rows[0]["audience"] == "customer" and rows[0]["access_level"] == "STANDARD"
    for column in (
        "development_access",
        "sales_access",
        "customer_access",
        "legacy_reference_number",
        "yaw_program",
    ):
        assert column not in rows[0]  # other audiences' and internal columns are dropped
    everyone = _csv_rows(client.get(f"/api/v1/releases/{release_id}/export?format=csv"))
    assert len(everyone) == 3
    assert (
        client.get(f"/api/v1/releases/{release_id}/export?format=csv&audience=martians").status_code
        == 422
    )


def test_covert_visibility_is_data_an_administrator_can_flip(app, client, cast, wcnv_ids):
    login_as(client, cast["engineer"])
    covert = _lookup_id(client, "customer-access", "COVERT")
    release_id = _release_with(
        app, client, cast, wcnv_ids, [{"title": "Covert one", "customer_access": covert}]
    )
    login_as(client, cast["viewer"])
    url = f"/api/v1/releases/{release_id}/export?format=csv&audience=customer"
    assert _csv_rows(client.get(url)) == []
    with app.app_context():
        from app.models.lookup import LookupCustomerAccess

        db.session.query(LookupCustomerAccess).filter_by(code="COVERT").update(
            {"audience_visible": 1}
        )
        db.session.commit()
    assert [r["title"] for r in _csv_rows(client.get(url))] == ["Covert one"]


def test_customer_profile_applies_its_default_audience_and_working_set_refuses_audiences(
    app, client, cast, wcnv_ids
):
    login_as(client, cast["engineer"])
    standard = _lookup_id(client, "customer-access", "STANDARD")
    release_id = _release_with(
        app,
        client,
        cast,
        wcnv_ids,
        [{"title": "For customers", "customer_access": standard}, {"title": "Internal only"}],
    )
    login_as(client, cast["viewer"])
    rows = _csv_rows(
        client.get(f"/api/v1/releases/{release_id}/export?format=csv&profile=CUSTOMER_LIST")
    )
    assert [r["Title"] for r in rows] == ["For customers"]
    login_as(client, cast["admin"])
    refused = client.get("/api/v1/exports/working-set?format=csv&audience=customer")
    assert refused.status_code == 422
    assert len(client.get("/api/v1/audiences").get_json()["items"]) == 8


# ---------------------------------------------------------------- manifest, bundle, verify (I-06)
def test_bundle_contains_the_file_and_a_manifest_that_matches(app, client, cast, wcnv_ids):
    release_id = _release_with(app, client, cast, wcnv_ids, [{"title": "Manifest me"}])
    login_as(client, cast["viewer"])
    response = client.get(f"/api/v1/releases/{release_id}/export?format=csv&bundle=true")
    assert response.mimetype == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(response.data))
    names = archive.namelist()
    assert "MANIFEST.json" in names and len(names) == 2
    manifest = json.loads(archive.read("MANIFEST.json"))
    data_name = next(n for n in names if n != "MANIFEST.json")
    assert manifest["files"][0]["name"] == data_name
    assert manifest["files"][0]["sha256"] == manifest_service.sha256_hex(archive.read(data_name))
    assert manifest["row_count"] == 1 and manifest["release"]["version_label"] == "R1"
    assert manifest["signature"] is None  # no signing key configured
    assert response.headers["X-Content-SHA256"] == manifest["files"][0]["sha256"]
    assert manifest["content_digest"] == manifest_service.content_digest(
        [{**r} for r in manifest_service.json.loads(json.dumps(_flat_rows_of(app, release_id)))]
    )


def _flat_rows_of(app, release_id):
    with app.app_context():
        from app.models.release import Release
        from app.services.export_service import flatten_revision

        release = db.session.get(Release, release_id)
        return [flatten_revision(item.revision) for item in release.items]


def test_verify_recognises_an_untouched_file_and_a_tampered_one(app, client, cast, wcnv_ids):
    release_id = _release_with(app, client, cast, wcnv_ids, [{"title": "Verify me"}])
    login_as(client, cast["viewer"])
    exported = client.get(f"/api/v1/releases/{release_id}/export?format=csv")
    original = exported.data

    def verify(content, name="catalogue.csv", manifest=None):
        files = {"file": (io.BytesIO(content), name)}
        if manifest is not None:
            files["manifest"] = (io.BytesIO(manifest), "MANIFEST.json")
        return client.post(
            "/api/v1/exports/verify", data=files, content_type="multipart/form-data"
        ).get_json()

    good = verify(original)
    assert good["recorded"] is True and good["manifest"]["ok"] is True
    tampered = verify(original.replace(b"Verify me", b"Verify ME!"))
    assert tampered["recorded"] is False and "manifest" not in tampered

    job_id = good["export_job_ids"][0]
    login_as(client, cast["engineer"])
    manifest = client.get(f"/api/v1/exports/{job_id}/manifest").data
    login_as(client, cast["viewer"])
    offline = verify(original.replace(b"Verify me", b"Verify ME!"), manifest=manifest)
    assert offline["manifest"]["file_listed"] is False and offline["manifest"]["ok"] is False
    assert verify(b"x", manifest=b"not json").get("error") == "validation_error"


def test_signed_manifest_detects_edits_to_the_manifest_itself(app, client, cast, wcnv_ids):
    app.config["MANIFEST_SIGNING_KEY"] = "an on-premises signing key"
    release_id = _release_with(app, client, cast, wcnv_ids, [{"title": "Signed"}])
    login_as(client, cast["viewer"])
    archive = zipfile.ZipFile(
        io.BytesIO(client.get(f"/api/v1/releases/{release_id}/export?format=csv&bundle=true").data)
    )
    manifest = json.loads(archive.read("MANIFEST.json"))
    assert manifest["signature"]["algorithm"] == "HMAC-SHA256" and manifest["signature"]["key_id"]
    data_name = next(n for n in archive.namelist() if n != "MANIFEST.json")
    content = archive.read(data_name)
    key = b"an on-premises signing key"
    assert manifest_service.verify_signature(manifest, key) == "valid"
    assert manifest_service.verify_file(content, manifest, data_name, key)["ok"] is True

    forged = json.loads(json.dumps(manifest))
    forged["row_count"] = 999
    assert manifest_service.verify_signature(forged, key) == "invalid"
    stripped = {k: v for k, v in manifest.items() if k != "signature"}
    stripped["signature"] = None
    with app.app_context():  # a key is configured, so an unsigned manifest is not accepted
        assert manifest_service.verify_file(content, stripped, data_name)["ok"] is False
    with app.app_context():
        assert manifest_service.verify_signature(manifest) == "valid"  # the configured key


def test_verify_export_cli_works_without_the_database(app, client, cast, wcnv_ids, tmp_path):
    release_id = _release_with(app, client, cast, wcnv_ids, [{"title": "CLI check"}])
    login_as(client, cast["viewer"])
    archive = zipfile.ZipFile(
        io.BytesIO(client.get(f"/api/v1/releases/{release_id}/export?format=csv&bundle=true").data)
    )
    archive.extractall(tmp_path)
    data_file = next(p for p in tmp_path.iterdir() if p.suffix == ".csv")
    runner = app.test_cli_runner()
    ok = runner.invoke(args=["verify-export", str(data_file), str(tmp_path / "MANIFEST.json")])
    assert ok.exit_code == 0 and '"ok": true' in ok.output
    data_file.write_bytes(data_file.read_bytes() + b"tampered")
    bad = runner.invoke(args=["verify-export", str(data_file), str(tmp_path / "MANIFEST.json")])
    assert bad.exit_code == 1 and "MISMATCH" in bad.output


def test_export_history_lists_hashes_per_release(app, client, cast, wcnv_ids):
    release_id = _release_with(app, client, cast, wcnv_ids, [{"title": "History"}])
    login_as(client, cast["engineer"])
    client.get(f"/api/v1/releases/{release_id}/export?format=csv")
    client.get(f"/api/v1/releases/{release_id}/export?format=json&profile=SCADA_TAGS")
    history = client.get(f"/api/v1/releases/{release_id}/exports").get_json()["items"]
    assert [h["export_type"] for h in history] == ["JSON", "CSV"]
    assert history[0]["profile"] == "SCADA_TAGS" and len(history[0]["sha256"]) == 64
    login_as(client, cast["viewer"])
    assert client.get(f"/api/v1/releases/{release_id}/exports").status_code == 403


# ---------------------------------------------------------------- release notes (I-06)
def _deprecate(app, client, cast, status_code_id):
    login_as(client, cast["engineer"])
    deprecation = client.post(
        f"/api/v1/status-codes/{status_code_id}/deprecation-requests",
        json={"reason": "Replaced by a better code for this fault."},
    ).get_json()
    cr_id = cr_id_for_revision(app, deprecation["id"])
    domain_sign(client, cast, cr_id)
    submit(client, cast, cr_id)
    decide(client, cast["reviewer"], cr_id, "reviewer-signoff")
    decide(client, cast["admin"], cr_id, "admin-signoff")
    decide(client, cast["chief_engineer"], cr_id, "chief-engineer-decide")


def test_release_notes_list_added_changed_and_deprecated(app, client, cast, wcnv_ids):
    first_revision, _ = drive_to_approved(app, client, cast, wcnv_ids, title="Stays as it is")
    second_revision, _ = drive_to_approved(app, client, cast, wcnv_ids, title="Will change later")
    third_revision, _ = drive_to_approved(app, client, cast, wcnv_ids, title="Will be deprecated")
    release_revisions(
        client,
        cast,
        [first_revision["id"], second_revision["id"], third_revision["id"]],
        label="R1",
    )
    # R2: a new revision of the second code, plus one brand-new code; the third code is deprecated meanwhile
    login_as(client, cast["engineer"])
    new_rev = client.post(
        f"/api/v1/status-codes/{second_revision['status_code_id']}/revisions",
        json=valid_payload(*wcnv_ids, title="Will change later", set_delay="20ms"),
    ).get_json()
    cr_id = cr_id_for_revision(app, new_rev["id"])
    domain_sign(client, cast, cr_id)
    submit(client, cast, cr_id)
    decide(client, cast["reviewer"], cr_id, "reviewer-signoff")
    decide(client, cast["admin"], cr_id, "admin-signoff")
    decide(client, cast["chief_engineer"], cr_id, "chief-engineer-decide")
    brand_new, _ = drive_to_approved(app, client, cast, wcnv_ids, title="Brand new code")
    _deprecate(app, client, cast, third_revision["status_code_id"])
    second_release = release_revisions(client, cast, [new_rev["id"], brand_new["id"]], label="R2")

    login_as(client, cast["viewer"])
    notes = client.get(f"/api/v1/releases/{second_release}/notes?format=json").get_json()
    assert notes["previous_release"]["version_label"] == "R1"
    assert [a["title"] for a in notes["added"]] == ["Brand new code"]
    assert [c["title"] for c in notes["changed"]] == ["Will change later"]
    assert {ch["field"] for ch in notes["changed"][0]["changes"]} == {"set_delay"}
    assert [d["title"] for d in notes["deprecated"]] == ["Will be deprecated"]
    assert notes["deprecated"][0]["reason"].startswith("Replaced by")

    md = client.get(f"/api/v1/releases/{second_release}/notes?format=md").get_data(as_text=True)
    assert (
        "## Added (1)" in md and "| set_delay | 10ms | 20ms |" in md and "## Deprecated (1)" in md
    )
    csv_rows = _csv_rows(client.get(f"/api/v1/releases/{second_release}/notes?format=csv"))
    assert {r["kind"] for r in csv_rows} == {"ADDED", "CHANGED", "DEPRECATED"}
    pdf = client.get(f"/api/v1/releases/{second_release}/notes?format=pdf")
    assert pdf.data.startswith(b"%PDF")
    zipped = client.get(f"/api/v1/releases/{second_release}/notes?format=md&bundle=true")
    assert "MANIFEST.json" in zipfile.ZipFile(io.BytesIO(zipped.data)).namelist()
    assert client.get(f"/api/v1/releases/{second_release}/notes?format=docx").status_code == 422

    first_notes = client.get(
        f"/api/v1/releases/{release_revisions_first(app)}/notes?format=json"
    ).get_json()
    assert first_notes["previous_release"] is None and len(first_notes["added"]) == 3


def release_revisions_first(app):
    from app.models.release import Release

    with app.app_context():
        return db.session.query(Release).order_by(Release.id).first().id


def test_unpublished_release_notes_are_an_administrator_preview(app, client, cast, wcnv_ids):
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids)
    login_as(client, cast["admin"])
    release = client.post(
        "/api/v1/releases", json={"name": "Draft", "version_label": "D1"}
    ).get_json()
    client.put(
        f"/api/v1/releases/{release['id']}/items",
        json={"status_code_revision_ids": [revision["id"]]},
    )
    assert client.get(f"/api/v1/releases/{release['id']}/notes").status_code == 200
    login_as(client, cast["viewer"])
    assert client.get(f"/api/v1/releases/{release['id']}/notes").status_code == 404


# ---------------------------------------------------------------- offline bundle (I-24)
def test_offline_bundle_is_one_self_contained_page_with_the_data(app, client, cast, wcnv_ids):
    release_id = _release_with(
        app,
        client,
        cast,
        wcnv_ids,
        [{"title": "Tricky </script><b>title</b> & more", "remedy_text": "Do it."}],
    )
    login_as(client, cast["viewer"])
    response = client.get(f"/api/v1/releases/{release_id}/offline-bundle")
    assert response.status_code == 200 and response.mimetype == "text/html"
    html = response.get_data(as_text=True)
    assert "<script src=" not in html and "http://" not in html and "https://" not in html
    assert html.count("</script>") == 2  # the data cannot close its own script element
    embedded = re.search(
        r'<script id="data" type="application/json">(.*?)</script>', html, re.S
    ).group(1)
    data = json.loads(embedded)
    assert (
        data[0]["title"] == "Tricky </script><b>title</b> & more"
        and data[0]["remedy_text"] == "Do it."
    )
    assert manifest_service.sha256_hex(response.data) == response.headers["X-Content-SHA256"]

    bundled = client.get(f"/api/v1/releases/{release_id}/offline-bundle?bundle=true")
    assert "MANIFEST.json" in zipfile.ZipFile(io.BytesIO(bundled.data)).namelist()


def test_offline_bundle_respects_audiences_and_needs_a_published_release(
    app, client, cast, wcnv_ids
):
    login_as(client, cast["engineer"])
    standard = _lookup_id(client, "customer-access", "STANDARD")
    release_id = _release_with(
        app,
        client,
        cast,
        wcnv_ids,
        [{"title": "Customer visible", "customer_access": standard}, {"title": "Hidden"}],
    )
    login_as(client, cast["viewer"])
    html = client.get(f"/api/v1/releases/{release_id}/offline-bundle?audience=customer").get_data(
        as_text=True
    )
    assert "Customer visible" in html and "Hidden" not in html
    login_as(client, cast["admin"])
    unpublished = client.post(
        "/api/v1/releases", json={"name": "U", "version_label": "U1"}
    ).get_json()
    assert client.get(f"/api/v1/releases/{unpublished['id']}/offline-bundle").status_code == 409


# ---------------------------------------------------------------- software versions (I-07)
def _versions(client, cast, *codes):
    login_as(client, cast["admin"])
    for order, code in enumerate(codes, start=1):
        created = client.post(
            "/api/v1/lookups/controller-software-versions",
            json={"code": code, "label": f"Controller software {code}", "sort_order": order},
        )
        assert created.status_code == 201, created.get_json()


def test_applicability_matrix_and_changes_between_versions(app, client, cast, wcnv_ids):
    _versions(client, cast, "4.0", "4.1", "4.2")
    release_id = _release_with(
        app,
        client,
        cast,
        wcnv_ids,
        [
            {"title": "Always there"},
            {
                "title": "Only 4.0 to 4.1",
                "applies_from_version": "4.0",
                "applies_to_version": "4.1",
            },
            {"title": "New in 4.2", "applies_from_version": "4.2"},
        ],
    )
    login_as(client, cast["viewer"])
    on_40 = client.get("/api/v1/software-versions/matrix?version=4.0").get_json()
    assert [i["title"] for i in on_40["items"]] == ["Always there", "Only 4.0 to 4.1"]
    on_42 = client.get("/api/v1/software-versions/matrix?version=4.2").get_json()
    assert [i["title"] for i in on_42["items"]] == ["Always there", "New in 4.2"]
    changes = client.get("/api/v1/software-versions/changes?from=4.0&to=4.2").get_json()
    assert [r["title"] for r in changes["added"]] == ["New in 4.2"]
    assert [r["title"] for r in changes["removed"]] == ["Only 4.0 to 4.1"]
    assert client.get("/api/v1/software-versions/matrix?version=9.9").status_code == 404

    rows = _csv_rows(
        client.get(f"/api/v1/releases/{release_id}/export?format=csv&software_version=4.1")
    )
    assert [r["title"] for r in rows] == ["Always there", "Only 4.0 to 4.1"]


def test_version_range_must_be_ordered_and_known(app, client, cast, wcnv_ids):
    _versions(client, cast, "5.0", "5.1")
    login_as(client, cast["engineer"])
    backwards = client.post(
        "/api/v1/status-codes",
        json=valid_payload(*wcnv_ids, applies_from_version="5.1", applies_to_version="5.0"),
    )
    assert backwards.status_code == 422
    unknown = client.post(
        "/api/v1/status-codes", json=valid_payload(*wcnv_ids, applies_from_version="0.0")
    )
    assert unknown.status_code == 422


def test_release_targets_limit_the_candidates_and_freeze_at_publish(app, client, cast, wcnv_ids):
    _versions(client, cast, "6.0", "6.1")
    only_old, _ = drive_to_approved(
        app,
        client,
        cast,
        wcnv_ids,
        title="Old only",
        applies_from_version="6.0",
        applies_to_version="6.0",
    )
    only_new, _ = drive_to_approved(
        app, client, cast, wcnv_ids, title="New only", applies_from_version="6.1"
    )
    login_as(client, cast["admin"])
    release = client.post(
        "/api/v1/releases",
        json={"name": "For 6.1", "version_label": "T1", "target_software_versions": ["6.1"]},
    ).get_json()
    assert release["target_software_versions"] == ["6.1"]
    candidates = client.get(f"/api/v1/releases/{release['id']}/candidates").get_json()
    assert [c["title"] for c in candidates] == ["New only"]
    assert (
        client.put(
            f"/api/v1/releases/{release['id']}/target-versions",
            json={"software_versions": ["6.0", "6.1"]},
        ).status_code
        == 200
    )
    assert len(client.get(f"/api/v1/releases/{release['id']}/candidates").get_json()) == 2
    assert (
        client.put(
            f"/api/v1/releases/{release['id']}/target-versions",
            json={"software_versions": ["nope"]},
        ).status_code
        == 422
    )
    client.put(
        f"/api/v1/releases/{release['id']}/items",
        json={"status_code_revision_ids": [only_new["id"], only_old["id"]]},
    )
    assert client.post(f"/api/v1/releases/{release['id']}/publish").status_code == 200
    assert (
        client.put(
            f"/api/v1/releases/{release['id']}/target-versions", json={"software_versions": ["6.0"]}
        ).status_code
        == 409
    )


# ---------------------------------------------------------------- translations (I-15)
def test_translation_workflow_with_light_review_and_language_exports(app, client, cast, wcnv_ids):
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids, title="Grid undervoltage trip")
    other, _ = drive_to_approved(app, client, cast, wcnv_ids, title="Untranslated code")
    release_id = release_revisions(client, cast, [revision["id"], other["id"]], label="L1")
    url = f"/api/v1/revisions/{revision['id']}/translations/de"

    login_as(client, cast["viewer"])
    assert client.put(url, json={"title": "x", "description": "y"}).status_code == 403
    login_as(client, cast["engineer"])
    saved = client.put(
        url,
        json={
            "title": "Netzunterspannung Auslösung",
            "description": "Die DC-Zwischenkreisspannung ist unter dem Grenzwert.",
        },
    )
    assert saved.status_code == 200 and saved.get_json()["status"] == "DRAFT"
    assert client.post(f"{url}/approve").status_code == 403  # an Engineer cannot approve

    # a draft translation is not used by exports
    login_as(client, cast["viewer"])
    drafts = _csv_rows(client.get(f"/api/v1/releases/{release_id}/export?format=csv&language=de"))
    assert drafts[0]["title"] == "Grid undervoltage trip" and drafts[0]["content_language"] == "en"

    login_as(client, cast["engineer"])
    own = client.post(f"{url}/approve")
    assert own.status_code == 403
    login_as(client, cast["reviewer"])
    approved = client.post(f"{url}/approve")
    assert approved.status_code == 200 and approved.get_json()["approved_by"] == cast["reviewer"].id

    login_as(client, cast["viewer"])
    rows = _csv_rows(client.get(f"/api/v1/releases/{release_id}/export?format=csv&language=de"))
    by_title = {r["title"]: r for r in rows}
    assert by_title["Netzunterspannung Auslösung"]["content_language"] == "de"
    assert (
        by_title["Untranslated code"]["content_language"] == "en"
    )  # fallback is visible, not silent
    strict = _csv_rows(
        client.get(
            f"/api/v1/releases/{release_id}/export?format=csv&language=de&strict_language=true"
        )
    )
    assert [r["title"] for r in strict] == ["Netzunterspannung Auslösung"]
    status = client.get(f"/api/v1/revisions/{revision['id']}/translations").get_json()["items"]
    assert [e for e in status if e["language"] == "de"] == [
        {
            "language": "de",
            "label": "DE Deutsch 🇩🇪",
            "status": "APPROVED",
            "title": "Netzunterspannung Auslösung",
            "description": "Die DC-Zwischenkreisspannung ist unter dem Grenzwert.",
            "remedy_text": None,
            "translated_by": cast["engineer"].id,
            "approved_by": cast["reviewer"].id,
        }
    ]
    # the languages added since have no translation yet
    others = {e["language"]: e["status"] for e in status if e["language"] != "de"}
    assert set(others) == {
        "fr",
        "hi",
        "ar",
        "bn",
        "mr",
        "te",
        "ta",
        "gu",
        "ur",
        "kn",
        "or",
        "ml",
        "pa",
        "es",
        "it",
        "da",
        "ka",
    }
    assert set(others.values()) == {"MISSING"}

    # editing an approved translation sends it back to DRAFT and clears the approval
    login_as(client, cast["engineer"])
    client.put(
        url,
        json={
            "title": "Netzunterspannung",
            "description": "Neu formuliert, mindestens zehn Zeichen.",
        },
    )
    login_as(client, cast["viewer"])
    assert (
        client.get(f"/api/v1/revisions/{revision['id']}/translations").get_json()["items"][0][
            "status"
        ]
        == "MISSING"
    )
    login_as(client, cast["reviewer"])
    assert (
        client.get(f"/api/v1/revisions/{revision['id']}/translations").get_json()["items"][0][
            "status"
        ]
        == "DRAFT"
    )


def test_translation_validation_worklist_and_carry_over(app, client, cast, wcnv_ids):
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids, title="Worklist code")
    release_revisions(client, cast, [revision["id"]], label="W1")
    login_as(client, cast["engineer"])
    bad_language = client.put(
        f"/api/v1/revisions/{revision['id']}/translations/xx",
        json={"title": "t", "description": "d"},
    )
    assert bad_language.status_code == 422
    source = client.put(
        f"/api/v1/revisions/{revision['id']}/translations/en",
        json={"title": "t", "description": "d"},
    )
    assert source.status_code == 422  # the source language is edited on the revision itself
    too_long = client.put(
        f"/api/v1/revisions/{revision['id']}/translations/de",
        json={"title": "t" * 121, "description": "d"},
    )
    assert too_long.status_code == 422
    assert (
        client.get("/api/v1/translations/worklist?language=de").get_json()["items"][0]["status"]
        == "MISSING"
    )
    client.put(
        f"/api/v1/revisions/{revision['id']}/translations/de",
        json={"title": "Titel", "description": "Beschreibung"},
    )
    assert (
        client.get("/api/v1/translations/worklist?language=de").get_json()["items"][0]["status"]
        == "DRAFT"
    )

    # approve, then open a new revision and carry the approved text forward as a draft
    login_as(client, cast["reviewer"])
    client.post(f"/api/v1/revisions/{revision['id']}/translations/de/approve")
    assert client.get("/api/v1/translations/worklist?language=de").get_json()["items"] == []
    login_as(client, cast["engineer"])
    next_rev = client.post(
        f"/api/v1/status-codes/{revision['status_code_id']}/revisions",
        json=valid_payload(*wcnv_ids, title="Worklist code", set_delay="30ms"),
    ).get_json()
    cr_id = cr_id_for_revision(app, next_rev["id"])
    domain_sign(client, cast, cr_id)
    submit(client, cast, cr_id)
    decide(client, cast["reviewer"], cr_id, "reviewer-signoff")
    decide(client, cast["admin"], cr_id, "admin-signoff")
    decide(client, cast["chief_engineer"], cr_id, "chief-engineer-decide")
    login_as(client, cast["engineer"])
    copied = client.post(f"/api/v1/revisions/{next_rev['id']}/translations/carry-over").get_json()
    assert copied["copied_languages"] == ["de"]
    assert (
        client.post(f"/api/v1/revisions/{next_rev['id']}/translations/carry-over").get_json()[
            "copied_languages"
        ]
        == []
    )


def test_draft_source_text_cannot_be_translated_yet(app, client, cast, wcnv_ids):
    from tests.helpers import create_draft

    draft, _ = create_draft(app, client, cast, wcnv_ids)
    login_as(client, cast["engineer"])
    response = client.put(
        f"/api/v1/revisions/{draft['id']}/translations/de", json={"title": "t", "description": "d"}
    )
    assert response.status_code == 409


def test_publication_ui_pages_render(app, client, cast, wcnv_ids):
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids)
    release_id = release_revisions(client, cast, [revision["id"]], label="UI1")
    login_as(client, cast["admin"])
    for path in (
        "/admin/export-profiles",
        f"/releases/{release_id}",
        f"/status-codes/{revision['status_code_id']}/translations",
        "/software-versions",
        "/exports",
    ):
        assert client.get(path).status_code == 200, path
    for fmt in ("csv", "xlsx", "pdf", "json"):
        shaped = client.get(
            f"/releases/{release_id}/shaped-export?format={fmt}&profile=SERVICE_MANUAL"
        )
        assert shaped.status_code == 200 and shaped.headers["X-Content-SHA256"], fmt
    assert client.get(f"/releases/{release_id}/notes?format=md").status_code == 200
    assert client.get(f"/releases/{release_id}/offline-bundle").status_code == 200
    verify = client.post(
        "/exports/verify",
        data={"file": (io.BytesIO(b"not something we exported"), "x.csv")},
        content_type="multipart/form-data",
    )
    assert verify.status_code == 200 and "No record of this exact file" in verify.get_data(
        as_text=True
    )
    assert PASSWORD

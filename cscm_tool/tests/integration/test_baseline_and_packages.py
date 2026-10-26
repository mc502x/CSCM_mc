"""The baseline of a Release and the all-languages / all-access-levels package (docs/03-srs.md
FR-173, FR-174): a manual contains every code valid as of its Release, not only the ones the Release
changed; it can be narrowed to a platform (2XM / 3XM / 4XM) and a controller (MC / HC); one package
holds every language for every access level, with a manifest that vouches for each file.

TC-066. Requirements: FR-173, FR-174, FR-045, BR-007.
"""

import csv
import io
import json
import zipfile

import pytest

from app.extensions import db
from app.models.lookup import LookupFunctionalSubgroup, LookupFunctionalSystemGroup
from app.services import manifest_service
from app.services.audience_service import AUDIENCES
from app.services.baseline_service import BaselineService
from app.services.package_service import PackageService
from tests.helpers import drive_to_approved, login_as, make_cast, release_revisions


def _csv(response) -> list[dict]:
    return list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))


@pytest.fixture()
def two_releases(app, client, make_user, wcnv_ids):
    """Release 1 carries code A (3XM), Release 2 carries code B (2XM): its delta is only B, its
    baseline both."""
    cast = make_cast(make_user)
    first, _ = drive_to_approved(
        app, client, cast, wcnv_ids, title="Code A", turbine_platforms=["3XM"]
    )
    one = release_revisions(client, cast, [first["id"]], label="R1")
    second, _ = drive_to_approved(
        app, client, cast, wcnv_ids, title="Code B", turbine_platforms=["2XM"]
    )
    two = release_revisions(client, cast, [second["id"]], label="R2")
    return cast, one, two


def test_the_baseline_of_a_release_holds_every_code_valid_at_that_release(client, two_releases):
    cast, one, two = two_releases
    login_as(client, cast["viewer"])
    complete = _csv(client.get(f"/api/v1/releases/{two}/export?format=csv"))
    assert sorted(r["title"] for r in complete) == ["Code A", "Code B"]
    # release 1 was published before B existed: its baseline is, and stays, only A
    earlier = _csv(client.get(f"/api/v1/releases/{one}/export?format=csv"))
    assert [r["title"] for r in earlier] == ["Code A"]


def test_a_release_can_still_be_exported_as_only_its_own_changes(client, two_releases):
    cast, _one, two = two_releases
    login_as(client, cast["viewer"])
    delta = _csv(client.get(f"/api/v1/releases/{two}/export?format=csv&content=delta"))
    assert [r["title"] for r in delta] == ["Code B"]
    assert (
        client.get(f"/api/v1/releases/{two}/export?format=csv&content=everything").status_code
        == 422
    )


def test_the_baseline_narrows_to_a_platform(client, two_releases):
    cast, _one, two = two_releases
    login_as(client, cast["viewer"])
    only_2xm = _csv(client.get(f"/api/v1/releases/{two}/export?format=csv&platform=2XM"))
    assert [r["title"] for r in only_2xm] == ["Code B"]
    only_3xm = _csv(client.get(f"/api/v1/releases/{two}/export?format=csv&platform=3XM"))
    assert [r["title"] for r in only_3xm] == ["Code A"]
    assert client.get(f"/api/v1/releases/{two}/export?format=csv&platform=9XM").status_code == 422


def test_the_baseline_narrows_to_a_controller(app, client, make_user, wcnv_ids):
    cast = make_cast(make_user)
    revision, _ = drive_to_approved(app, client, cast, wcnv_ids, title="Main controller code")
    release = release_revisions(client, cast, [revision["id"]], label="R1")
    login_as(client, cast["viewer"])
    mc = _csv(client.get(f"/api/v1/releases/{release}/export?format=csv&controller=MC"))
    hc = _csv(client.get(f"/api/v1/releases/{release}/export?format=csv&controller=HC"))
    assert [r["title"] for r in mc] == ["Main controller code"]
    assert hc == []
    assert (
        client.get(f"/api/v1/releases/{release}/export?format=csv&controller=XX").status_code == 422
    )


def test_the_summary_counts_the_baseline_by_controller_and_platform(client, two_releases):
    cast, _one, two = two_releases
    login_as(client, cast["viewer"])
    summary = client.get(f"/api/v1/releases/{two}/baseline").get_json()
    assert summary["baseline"] == 2 and summary["in_release"] == 1
    assert summary["by_controller"] == {"MC": 2, "HC": 0}
    assert summary["by_platform"] == {"2XM": 1, "3XM": 1}


def test_an_unpublished_release_previews_what_its_manual_will_contain(app, client, two_releases):
    cast, _one, two = two_releases
    login_as(client, cast["admin"])
    draft = client.post("/api/v1/releases", json={"name": "Next", "version_label": "R3"}).get_json()
    with app.app_context():
        from app.models.release import Release

        release = db.session.get(Release, draft["id"])
        assert sorted(r.title for r in BaselineService.revisions(release)) == ["Code A", "Code B"]


def test_the_title_page_names_the_scope(client, two_releases):
    cast, _one, two = two_releases
    login_as(client, cast["viewer"])
    response = client.get(f"/api/v1/releases/{two}/export?format=pdf&platform=2XM&language=de")
    assert response.status_code == 200 and response.data.startswith(b"%PDF")


# ------------------------------------------------------------------------------ the package


def _package(client, release_id, **body):
    return client.post(f"/api/v1/releases/{release_id}/packages", json=body)


def _open(client, job_id) -> zipfile.ZipFile:
    download = client.get(f"/api/v1/packages/{job_id}/download")
    assert download.status_code == 200 and download.mimetype == "application/zip"
    return zipfile.ZipFile(io.BytesIO(download.data))


def test_a_package_holds_every_language_for_every_access_level(app, client, two_releases):
    cast, _one, two = two_releases
    login_as(client, cast["engineer"])
    created = _package(client, two, formats=["csv"])
    assert created.status_code == 201, created.get_json()
    job = created.get_json()
    assert job["status"] == "COMPLETE" and job["done"] == job["total"]

    with app.app_context():
        languages = [lang.code for lang in PackageService.languages()]
    assert len(languages) == 19
    archive = _open(client, job["id"])
    names = archive.namelist()
    csvs = [n for n in names if n.endswith(".csv")]
    assert len(csvs) == 19 * (len(AUDIENCES) + 1)  # every audience plus the unfiltered file
    assert "R2/release-notes.md" in names and "R2/MANIFEST.json" in names
    for language in languages:
        for audience in (*AUDIENCES, "all"):
            assert any(n.startswith(f"R2/{language}/{audience}/") for n in csvs), (
                language,
                audience,
            )


def test_the_manifest_vouches_for_every_file_and_reports_the_coverage(client, two_releases):
    cast, _one, two = two_releases
    login_as(client, cast["engineer"])
    job = _package(client, two, formats=["csv", "json"], languages=["en", "de"]).get_json()
    archive = _open(client, job["id"])
    manifest = json.loads(archive.read("R2/MANIFEST.json"))
    assert manifest["kind"] == "package" and manifest["row_count"] == 2
    assert manifest["scope"]["content"] == "baseline"
    assert manifest["scope"]["coverage"]["en"] == {"translated": 2, "of": 2}
    assert manifest["scope"]["coverage"]["de"]["of"] == 2
    listed = {f["name"]: f for f in manifest["files"]}
    assert set(listed) == set(archive.namelist()) - {"R2/MANIFEST.json"}
    for name, entry in listed.items():
        assert manifest_service.sha256_hex(archive.read(name)) == entry["sha256"], name
    unfiltered = [f for f in manifest["files"] if f["audience"] is None and f["format"] == "csv"]
    assert {f["rows"] for f in unfiltered} == {2}
    # the package itself is recorded with its hash, like every other export
    status = client.get(f"/api/v1/packages/{job['id']}").get_json()
    assert status["sha256"] and status["status"] == "COMPLETE"


def test_a_package_can_be_narrowed_to_a_platform_and_a_controller(client, two_releases):
    cast, _one, two = two_releases
    login_as(client, cast["engineer"])
    job = _package(
        client,
        two,
        formats=["csv"],
        languages=["en"],
        audiences=["customer"],
        platform="2XM",
        controller="MC",
        include_unfiltered=True,
    ).get_json()
    archive = _open(client, job["id"])
    csvs = [n for n in archive.namelist() if n.endswith(".csv")]
    assert len(csvs) == 2  # the customer file and the unfiltered one
    unfiltered = [n for n in csvs if "/all/" in n][0]
    assert "2XM" in unfiltered and "MC" in unfiltered
    rows = list(csv.DictReader(io.StringIO(archive.read(unfiltered).decode("utf-8"))))
    assert [r["title"] for r in rows] == ["Code B"]


def test_everybody_may_download_what_is_released_and_only_owner_and_admin_what_is_not(
    client, two_releases
):
    cast, _one, two = two_releases
    login_as(client, cast["engineer"])
    job = _package(client, two, formats=["csv"], languages=["en"]).get_json()
    for who in ("viewer", "reviewer", "stcd_owner", "admin", "chief_engineer", "engineer"):
        login_as(client, cast[who])
        assert client.get(f"/api/v1/packages/{job['id']}/download").status_code == 200, who
        assert client.get(f"/api/v1/releases/{two}/export?format=csv").status_code == 200, who
    login_as(client, cast["viewer"])
    assert _package(client, two, formats=["csv"], languages=["en"]).status_code == 201
    # a Release that is not published yet: only the StCd Owner and the Administrator
    login_as(client, cast["admin"])
    draft = client.post("/api/v1/releases", json={"name": "Next", "version_label": "R3"}).get_json()
    for who, expected in (("viewer", 404), ("engineer", 404), ("stcd_owner", 200), ("admin", 200)):
        login_as(client, cast[who])
        response = client.get(f"/api/v1/releases/{draft['id']}/export?format=csv")
        assert response.status_code == expected, who


def test_a_package_needs_a_published_release_and_valid_choices(client, two_releases):
    cast, _one, two = two_releases
    login_as(client, cast["admin"])
    draft = client.post("/api/v1/releases", json={"name": "Next", "version_label": "R3"}).get_json()
    assert _package(client, draft["id"], formats=["csv"]).status_code == 422
    assert _package(client, two, formats=["docx"]).status_code == 422
    assert _package(client, two, formats=["csv"], languages=["klingon"]).status_code == 422
    assert _package(client, two, formats=["csv"], audiences=["everybody"]).status_code == 422
    assert client.get("/api/v1/packages/9999").status_code == 404


def test_the_readiness_check_shows_what_is_still_missing(client, two_releases):
    cast, _one, two = two_releases
    login_as(client, cast["engineer"])
    readiness = client.get(f"/api/v1/releases/{two}/readiness").get_json()
    assert readiness["baseline"] == 2
    assert readiness["translation_coverage"]["de"] == {"translated": 0, "of": 2}
    assert readiness["unconfirmed_access"]["count"] == 0
    login_as(client, cast["viewer"])
    assert client.get(f"/api/v1/releases/{two}/readiness").status_code == 403


def test_the_release_page_offers_the_baseline_and_the_package(client, two_releases):
    cast, _one, two = two_releases
    login_as(client, cast["engineer"])
    html = client.get(f"/releases/{two}").get_data(as_text=True)
    assert "Complete baseline" in html and "Build package" in html
    assert 'name="platform"' in html and 'name="controller"' in html and 'name="content"' in html
    post = client.post(f"/releases/{two}/packages", data={"formats": ["csv"], "languages": ["en"]})
    assert post.status_code == 302
    html = client.get(f"/releases/{two}").get_data(as_text=True)
    assert "COMPLETE" in html and "Download" in html
    login_as(client, cast["viewer"])
    page = client.get(f"/releases/{two}").get_data(as_text=True)
    assert "Build package" in page and "Complete baseline" in page  # FR-175: everybody
    assert "Translated codes per language" not in page  # the readiness line is for working roles


def test_the_package_is_audited(client, two_releases, app):
    cast, _one, two = two_releases
    login_as(client, cast["engineer"])
    _package(client, two, formats=["csv"], languages=["en"])
    from app.models.audit import AuditLogEntry

    with app.app_context():
        actions = {a.action for a in db.session.query(AuditLogEntry).all()}
    assert {"PACKAGE_REQUEST", "PACKAGE_EXPORT"} <= actions


def test_a_hub_controller_group_exists_for_the_controller_filter(app):
    with app.app_context():
        hub_groups = (
            db.session.query(LookupFunctionalSystemGroup)
            .filter(LookupFunctionalSystemGroup.controller_type == "HUB")
            .count()
        )
        assert hub_groups > 0
        assert db.session.query(LookupFunctionalSubgroup).count() > 0

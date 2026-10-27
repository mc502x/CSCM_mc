"""A throw-away demo of the application for the screenshots (FR-186).

It builds its own database in a temporary folder - never the development or a production database -
fills it with fictitious people and status codes through the application's own API, and serves it
on 127.0.0.1 for the headless browser. Two routes exist only in this demo process, not in the
application: `/_show/as/<username>` signs the browser in (a headless browser cannot type a
password) and `/_show/st-preview` shows the preview page of an `.st` import."""

import datetime
import hashlib
import os
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP_DIR))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from flask import make_response, redirect, render_template, request, session  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.services.user_service import UserService  # noqa: E402
from app.utils import format_iso  # noqa: E402
from tests.helpers import PASSWORD, cr_id_for_revision, login_as, valid_payload  # noqa: E402

FIXTURES = APP_DIR / "tests" / "fixtures" / "st"
ST_FILES = [
    "StCd_1000.st",
    "StCd_1001.st",
    "StCd_1002.st",
    "StCd_14000.st",
    "StCd_14005.st",
    "StCd_14025.st",
]

# (username, role, name, domains, ui language)
PEOPLE = [
    ("admin", "ADMINISTRATOR", "Alex Administrator", None, "en"),
    ("owner", "STCD_OWNER", "Sam Owner", None, "en"),
    ("chief", "CHIEF_ENGINEER", "Chris Chief", None, "en"),
    ("reviewer", "REVIEWER", "Robin Reviewer", None, "en"),
    ("engineer", "ENGINEER", "Eli Engineer", ["CONTROLS"], "en"),
    ("viewer", "VIEWER", "Val Viewer", None, "en"),
    ("engineer_ar", "ENGINEER", "Eli Engineer", ["CONTROLS"], "ar"),
]

# (group id, subgroup id, title, category, description) - fictitious but typical for a turbine
CODES = [
    (
        1,
        1,
        "Converter grid undervoltage trip",
        "ERROR",
        "The DC-link voltage of the converter fell below the threshold.",
    ),
    (
        1,
        2,
        "Grid frequency out of range",
        "WARNING",
        "The measured grid frequency left the permitted band.",
    ),
    (
        2,
        3,
        "Generator winding temperature high",
        "WARNING",
        "A stator winding sensor exceeds the warning limit.",
    ),
    (
        2,
        4,
        "Generator overcurrent protection trip",
        "ERROR",
        "The generator protection opened the contactor.",
    ),
    (
        3,
        5,
        "Anemometer plausibility check failed",
        "WARNING",
        "The two wind speed sensors disagree.",
    ),
    (
        4,
        7,
        "Pitch position deviation between blades",
        "ERROR",
        "One blade differs from the others by more than the limit.",
    ),
    (
        4,
        8,
        "De-icing hot air temperature low",
        "INFO",
        "The hot air for the de-icing is cooler than expected.",
    ),
    (
        5,
        11,
        "Tower door open during operation",
        "WARNING",
        "The tower base door contact reports open.",
    ),
    (
        6,
        13,
        "Transformer oil temperature high",
        "WARNING",
        "The transformer oil is above the warning temperature.",
    ),
    (
        7,
        14,
        "Gearbox oil pressure low",
        "ERROR",
        "The pressure after the filter is below the limit.",
    ),
    (8, 18, "Yaw brake pressure low", "ERROR", "The yaw brake circuit cannot hold its pressure."),
    (
        9,
        20,
        "Controller watchdog timeout",
        "ERROR",
        "The safety controller did not answer in time.",
    ),
    (
        9,
        19,
        "Operating mode changed by remote command",
        "INFO",
        "The operator switched the mode from the control room.",
    ),
    (
        3,
        6,
        "Nacelle vibration above warning level",
        "WARNING",
        "The tower-top acceleration exceeds the warning level.",
    ),
]
# how far each code is taken: released, approved, pending (waits for the Chief Engineer), review, draft
STAGES = ["released"] * 6 + [
    "approved",
    "pending",
    "pending",
    "review",
    "review",
    "draft",
    "draft",
    "draft",
]


@dataclass
class Demo:
    app: object
    workdir: Path
    ids: dict = field(default_factory=dict)
    preview_html_context: dict = field(default_factory=dict)
    _server: object = None
    url: str = ""

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()  # type: ignore[attr-defined]


class _User:
    def __init__(self, username: str):
        self.username = username


def _ok(response, expected: tuple[int, ...] = (200, 201, 202)):
    if response.status_code not in expected:
        raise RuntimeError(
            f"demo data: {response.status_code} {response.get_data(as_text=True)[:300]}"
        )
    return response


def build(workdir: Path | None = None) -> Demo:
    """Creates the database and the data; returns the demo (not yet serving)."""
    workdir = Path(workdir or tempfile.mkdtemp(prefix="cscm_showcase_"))
    os.environ["CSCM_INSTANCE_PATH"] = str(workdir / "instance")
    app = create_app(
        "testing",
        {
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(workdir / 'demo.db').as_posix()}",
            "AUTH_MODE": "password",
            "SESSION_COOKIE_SECURE": False,
            "SESSION_COOKIE_SAMESITE": "Lax",
            "STEP_UP_REQUIRED": False,
        },
    )
    config = Config(str(APP_DIR / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(APP_DIR / "migrations"))
    demo = Demo(app, workdir)
    _register_show_routes(demo)
    with app.app_context():
        command.upgrade(config, "head")
        for username, role, name, domains, language in PEOPLE:
            user = UserService.create_user(
                username=username,
                email=f"{username}@example.test",
                full_name=name,
                role_code=role,
                password=PASSWORD,
                engineering_domain_codes=domains,
                actor=None,
            )
            user.ui_language = language
        db.session.commit()
    _seed(
        demo
    )  # outside the context above: its session must not hold the database while requests run
    return demo


def _seed(demo: Demo) -> None:
    client = demo.app.test_client()
    people = {name: _User(name) for name, *_ in PEOPLE}

    def login(name: str) -> None:
        with demo.app.app_context():
            login_as(client, people[name])

    # the migration batch: the real sample programs, previewed before they are imported
    login("engineer")
    files = [(FIXTURES / n).read_bytes() for n in ST_FILES]
    from app.services.st_import_service import StImportService
    from tests.helpers import seed_st_mapping

    with demo.app.app_context():
        seed_st_mapping()  # the title, the type and the access levels come from the mapping
        preview = StImportService.preview(
            [(n, c) for n, c in zip(ST_FILES, files, strict=True)],
            _actor("engineer"),
        )
        db.session.rollback()
    demo.preview_html_context = {"preview": preview}
    imported = _ok(
        client.post(
            "/api/v1/imports/st",
            json={"token": preview["token"], "change_set_name": "Migration wave 1"},
        )
    ).get_json()
    demo.ids["change_set"] = imported["change_set_id"]

    # a request to change the mapping that has two of its three approvals (the Administrator is next)
    login("engineer")
    change = _ok(
        client.post(
            "/api/v1/mapping-changes",
            json={
                "title": "New code: converter fan fault",
                "reason": "The new converter cabinet has a fan that the old library had no code for.",
                "items": [
                    {
                        "action": "ADD",
                        "fields": {
                            "family": "MC",
                            "legacy_number": 3100,
                            "new_number": 1150,
                            "description": "Converter fan fault",
                            "functional_group": "Converter",
                            "logical_node": "WCNV",
                            "status_type": "WARNING",
                            "up_down_counter": "No",
                        },
                    }
                ],
            },
        )
    ).get_json()
    for name in ("owner", "chief"):
        login(name)
        _ok(
            client.post(
                f"/api/v1/mapping-changes/{change['id']}/decisions", json={"decision": "APPROVE"}
            )
        )
    demo.ids["mapping_change"] = change["id"]

    # hand-made codes, taken through the governance as far as their stage says
    revisions = []
    for (group, subgroup, title, category, text), stage in zip(CODES, STAGES, strict=True):
        login("engineer")
        payload = valid_payload(
            group, subgroup, title=title, description=text, status_category=category
        )
        revision = _ok(client.post("/api/v1/status-codes", json=payload)).get_json()
        cr = cr_id_for_revision(demo.app, revision["id"])
        revisions.append((revision, cr, stage))
        if stage == "draft":
            continue
        login("engineer")
        _ok(
            client.post(
                f"/api/v1/change-requests/{cr}/domain-signoffs",
                json={"engineering_domain": "CONTROLS"},
            )
        )
        _ok(client.post(f"/api/v1/change-requests/{cr}/submit", json={}), (200,))
        if stage == "review":
            continue
        login("reviewer")
        _ok(
            client.post(
                f"/api/v1/change-requests/{cr}/reviewer-signoff", json={"decision": "APPROVE"}
            ),
            (200,),
        )
        login("admin")
        _ok(
            client.post(
                f"/api/v1/change-requests/{cr}/admin-signoff", json={"decision": "APPROVE"}
            ),
            (200,),
        )
        if stage == "pending":
            continue
        login("chief")
        _ok(
            client.post(
                f"/api/v1/change-requests/{cr}/chief-engineer-decide", json={"decision": "APPROVE"}
            ),
            (200,),
        )
    released = [r["id"] for r, _cr, stage in revisions if stage == "released"]
    login("admin")
    release = _ok(
        client.post("/api/v1/releases", json={"name": "Release 2026.1", "version_label": "2026.1"})
    ).get_json()
    _ok(
        client.put(
            f"/api/v1/releases/{release['id']}/items", json={"status_code_revision_ids": released}
        )
    )
    _ok(client.post(f"/api/v1/releases/{release['id']}/publish"), (200,))
    demo.ids["release"] = release["id"]
    # a second, open release for the builder screen
    open_release = _ok(
        client.post("/api/v1/releases", json={"name": "Release 2026.2", "version_label": "2026.2"})
    ).get_json()
    approved = [r["id"] for r, _cr, stage in revisions if stage == "approved"]
    _ok(
        client.put(
            f"/api/v1/releases/{open_release['id']}/items",
            json={"status_code_revision_ids": approved},
        )
    )
    demo.ids["open_release"] = open_release["id"]

    first = next(r for r, _cr, stage in revisions if stage == "released")
    demo.ids["released_code"] = first["status_code_id"]
    demo.ids["pending_cr"] = next(cr for _r, cr, stage in revisions if stage == "pending")
    demo.ids["review_cr"] = next(cr for _r, cr, stage in revisions if stage == "review")
    demo.ids["draft_code"] = next(
        r["status_code_id"] for r, _cr, stage in revisions if stage == "draft"
    )

    # the migration batch goes to review; the reviewer draws the sample and has looked at three codes
    set_id = demo.ids["change_set"]
    login("engineer")
    _ok(client.post(f"/api/v1/change-sets/{set_id}/bulk-submit", json={}), (200,))
    login("reviewer")
    sample = _ok(
        client.post(f"/api/v1/change-sets/{set_id}/samples", json={"step": "reviewer"}), (200, 201)
    ).get_json()
    for item in sample["items"][:3]:
        _ok(
            client.put(
                f"/api/v1/bulk-samples/{sample['id']}/items/{item['change_request_id']}",
                json={"verdict": "OK"},
            ),
            (200,),
        )
    demo.ids["sample"] = sample["id"]


def _actor(username: str):
    from app.auth.providers import AuthenticatedUser
    from app.models.user import User

    return AuthenticatedUser.from_model(db.session.query(User).filter_by(username=username).one())


def _register_show_routes(demo: Demo) -> None:
    app = demo.app

    @app.route("/_show/as/<username>")  # type: ignore[attr-defined]
    def _show_as(username: str):
        from app.models.user import User

        user = db.session.query(User).filter_by(username=username).one()
        now = format_iso(datetime.datetime.now(datetime.UTC))
        session.clear()
        session["user_id"] = user.id
        session["login_at"] = now
        session["last_activity_at"] = now
        session["pw_fingerprint"] = hashlib.sha256(user.password_hash.encode()).hexdigest()
        session.permanent = True
        response = redirect(request.args.get("next", "/"))
        if request.args.get("theme") in ("dark", "light"):
            response.set_cookie("show_theme", request.args["theme"])
        return response

    @app.route("/_show/theme/<mode>")  # type: ignore[attr-defined]
    def _show_theme(mode: str):
        response = redirect(request.args.get("next", "/"))
        response.set_cookie("show_theme", mode if mode in ("dark", "light") else "light")
        return response

    @app.after_request  # type: ignore[attr-defined]
    def _show_theme_file(response):
        # a headless browser cannot choose the theme: the demo hands it a theme.js that has chosen
        mode = request.cookies.get("show_theme")
        if mode in ("dark", "light") and request.path.endswith("/js/theme.js"):
            script = (
                f"document.documentElement.setAttribute('data-theme','{mode}');"
                f"document.documentElement.setAttribute('data-theme-mode','{mode}');"
            )
            response = make_response(script)
            response.headers["Content-Type"] = "application/javascript"
        return response

    @app.route("/_show/st-preview")  # type: ignore[attr-defined]
    def _show_st_preview():
        return render_template("imports/st_preview.html", **demo.preview_html_context)


def serve(demo: Demo, port: int = 0) -> str:
    """Starts the demo on 127.0.0.1 in a thread; returns its address."""
    server = make_server("127.0.0.1", port, demo.app, threaded=True)  # type: ignore[arg-type]
    demo._server = server
    demo.url = f"http://127.0.0.1:{server.server_port}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return demo.url

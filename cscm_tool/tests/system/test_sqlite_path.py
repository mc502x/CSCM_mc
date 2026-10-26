"""A new machine: the database file is found, and its folder created, from the example .env
(`DATABASE_URL=sqlite:///instance/cscm.db`) as well as from an absolute path. Requirement: NFR-013."""

import os
import shutil
from pathlib import Path

import app as application
from app import create_app
from app.extensions import db


def _open(app) -> str:
    with app.app_context():
        db.session.execute(db.text("SELECT 1"))
        path = str(db.engine.url.database)
        db.session.remove()
        db.engine.dispose()
    return path


def test_a_relative_sqlite_path_is_read_from_the_application_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app_dir = Path(application.__file__).resolve().parents[1]
    scratch = app_dir / "instance" / "sqlite_path_test"
    try:
        app = create_app(
            "testing", {"SQLALCHEMY_DATABASE_URI": "sqlite:///instance/sqlite_path_test/cscm.db"}
        )
        path = Path(_open(app))
        assert path.is_absolute() and scratch.is_dir()
        assert os.path.samefile(path.parent, scratch)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def test_an_absolute_path_gets_its_folder_and_memory_is_left_alone(tmp_path):
    target = tmp_path / "data" / "cscm.db"
    app = create_app("testing", {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{target.as_posix()}"})
    _open(app)
    assert target.parent.is_dir() and os.path.isabs(target)
    memory = create_app("testing", {"SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    assert memory.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"

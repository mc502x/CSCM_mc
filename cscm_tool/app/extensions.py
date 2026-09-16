"""Shared extension instances, initialized against the app in create_app().

Models subclass Base (not db.Model) so mypy can resolve them as ordinary
SQLAlchemy 2.0 declarative classes; db.Model is dynamically generated per
SQLAlchemy() instance and mypy cannot introspect it as a base class."""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # Models use legacy-style `col = db.Column(...)` / `rel = db.relationship(...)`
    # rather than SQLAlchemy 2.0's Mapped[]/mapped_column() style, but some
    # attributes still carry a plain type annotation (e.g. `role: Role = ...`)
    # purely so mypy can resolve relationship types precisely (see
    # app/models/user.py). Without this flag, SQLAlchemy's runtime
    # "Annotated Declarative" scanner misreads those as ORM mapping
    # directives instead of the typing-only hints they are.
    __allow_unmapped__ = True


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
csrf = CSRFProtect()

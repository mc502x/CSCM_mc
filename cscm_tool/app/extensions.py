"""Shared extension instances, initialized against the app in create_app().

Models subclass Base (not db.Model) so mypy can resolve them as ordinary
SQLAlchemy 2.0 declarative classes; db.Model is dynamically generated per
SQLAlchemy() instance and mypy cannot introspect it as a base class."""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
migrate = Migrate()

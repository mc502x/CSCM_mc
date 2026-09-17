"""Generic CRUD repository. No business rules live here — see
docs/15-development-standards.md §1 (Service Layer owns business rules)."""

from typing import Generic, TypeVar

from werkzeug.exceptions import NotFound

from app.extensions import db

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    model: type[ModelType]

    def get(self, id_: int) -> ModelType | None:
        return db.session.get(self.model, id_)

    def get_or_404(self, id_: int) -> ModelType:
        obj = self.get(id_)
        if obj is None:
            raise NotFound(f"{self.model.__name__} {id_} not found")
        return obj

    def list(self) -> list[ModelType]:
        return list(db.session.query(self.model).all())

    def add(self, obj: ModelType) -> ModelType:
        db.session.add(obj)
        return obj

    def delete(self, obj: ModelType) -> None:
        db.session.delete(obj)

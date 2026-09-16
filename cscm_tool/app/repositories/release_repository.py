from app.models.release import Release
from app.repositories.base import BaseRepository


class ReleaseRepository(BaseRepository[Release]):
    model = Release

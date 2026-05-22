"""StudyRepository interface."""

from abc import abstractmethod

from ...domain.models.study import Study
from .base_crud_repository import BaseCrudRepository


class StudyRepository(BaseCrudRepository[Study, dict]):
    """Port for the Study entity."""

    @abstractmethod
    def get_by_name(self, name: str) -> Study | None:
        """Fetch a study by its name."""

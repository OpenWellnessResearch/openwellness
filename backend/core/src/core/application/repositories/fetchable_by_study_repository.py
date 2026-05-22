"""FetchableByStudyRepository interface."""

from abc import ABC, abstractmethod
from typing import Generic, Type, TypeVar

Entity = TypeVar("Entity")


class FetchableByStudyRepository(ABC, Generic[Entity]):
    """Repositories that can fetch entities by study ID."""

    def __init__(self, entity: Type[Entity]):
        self.entity = entity

    @abstractmethod
    def get_by_study_id(self, study_id: str) -> list[Entity]:
        """Fetch entities by study ID."""

"""MetaDataRepository interface."""

from abc import abstractmethod
from typing import Generic, Optional, TypeVar

from ...domain.models.meta_data import MetaData
from .base_crud_repository import BaseCrudRepository

SomeMetaData = TypeVar("SomeMetaData", bound=MetaData)


class MetaDataRepository(BaseCrudRepository[SomeMetaData, str], Generic[SomeMetaData]):
    """Interface for the MetaData entity."""

    @abstractmethod
    def get_for_related_id(
        self,
        related_id: Optional[str],
        ordering: str,
    ) -> list[SomeMetaData]:
        """Fetch MetaData for a related ID."""

    @abstractmethod
    def get_for_owner(
        self,
        owner: str,
        related_id: Optional[str],
        ordering: str,
    ) -> list[SomeMetaData]:
        """Fetch MetaData for an owner."""

    @abstractmethod
    def get_for_study_id(self, study_id: str, ordering: str) -> list[SomeMetaData]:
        """Fetch MetaData for a study ID."""

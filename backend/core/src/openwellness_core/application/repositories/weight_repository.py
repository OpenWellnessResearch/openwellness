"""WeightRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from arrow import Arrow

from ...domain.models.weight import Weight
from .owner_crud_repository import OwnerCrudRepository

SomeWeight = TypeVar("SomeWeight", bound=Weight)


class WeightRepository(
    OwnerCrudRepository[SomeWeight, Arrow],
    Generic[SomeWeight],
):
    """Interface for Weight entity."""

    @abstractmethod
    def get_for_owner(self, owner_id: str, date: Arrow) -> list[SomeWeight]:
        """Fetch Weights for an owner created on the day of `date`."""

    @abstractmethod
    def get_for_owner_between(
        self, owner_id: str, start: Arrow, end: Arrow
    ) -> list[SomeWeight]:
        """Fetch Weights for an owner created between two dates (inclusive)."""

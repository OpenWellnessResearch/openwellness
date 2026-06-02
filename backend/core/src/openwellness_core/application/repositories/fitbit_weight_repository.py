"""FitbitWeightRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.fitbit_weight import FitbitWeight
from .base_crud_repository import BaseCrudRepository

SomeFitbitWeight = TypeVar("SomeFitbitWeight", bound=FitbitWeight)


class FitbitWeightRepository(
    BaseCrudRepository[SomeFitbitWeight, str], Generic[SomeFitbitWeight]
):
    """Interface for FitbitWeight."""

    @abstractmethod
    def get_for_owner(self, owner: str, date: str) -> list[SomeFitbitWeight]:
        """Fetch FitbitWeights for an owner created on a specific date."""

    @abstractmethod
    def get_for_owner_between(
        self, owner: str, start: str, end: str
    ) -> list[SomeFitbitWeight]:
        """Fetch FitbitWeights for an owner between two dates (inclusive)."""

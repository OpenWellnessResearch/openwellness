"""FitbitSleepRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from arrow import Arrow

from ...domain.models.fitbit_sleep import FitbitSleep
from .owner_crud_repository import OwnerCrudRepository

SomeFitbitSleep = TypeVar("SomeFitbitSleep", bound=FitbitSleep)


class FitbitSleepRepository(
    OwnerCrudRepository[SomeFitbitSleep, Arrow],
    Generic[SomeFitbitSleep],
):
    """Interface for the FitbitSleep entity."""

    @abstractmethod
    def create_from(self, d: dict) -> SomeFitbitSleep:
        """Create a FitbitSleep from a dictionary."""

    @abstractmethod
    def update_from(self, entity: SomeFitbitSleep, d: dict) -> SomeFitbitSleep:
        """Update a FitbitSleep from a dictionary."""

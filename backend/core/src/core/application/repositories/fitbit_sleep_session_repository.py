"""FitbitSleepSessionRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from arrow import Arrow

from ...domain.models.fitbit_sleep_session import FitbitSleepSession
from .owner_crud_repository import OwnerCrudRepository

SomeFitbitSleepSession = TypeVar("SomeFitbitSleepSession", bound=FitbitSleepSession)


class FitbitSleepSessionRepository(
    OwnerCrudRepository[SomeFitbitSleepSession, Arrow],
    Generic[SomeFitbitSleepSession],
):
    """Interface for FitbitSleepSession entity."""

    @abstractmethod
    def create_from(self, d: dict) -> SomeFitbitSleepSession:
        """Create a FitbitSleepSession from a dictionary."""

    @abstractmethod
    def update_from(
        self, entity: SomeFitbitSleepSession, d: dict
    ) -> SomeFitbitSleepSession:
        """Update a FitbitSleepSession from a dictionary."""

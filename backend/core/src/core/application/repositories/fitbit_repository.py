"""FitbitRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.fitbit import Fitbit
from .base_crud_repository import BaseCrudRepository

SomeFitbit = TypeVar("SomeFitbit", bound=Fitbit)


class FitbitRepository(BaseCrudRepository[SomeFitbit, dict], Generic[SomeFitbit]):
    """Port for the Fitbit entity."""

    @abstractmethod
    def get_by_participant_id(self, participant_id: str) -> SomeFitbit | None:
        """Get a Fitbit by its participant ID."""

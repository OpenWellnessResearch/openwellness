"""DailyStateRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from arrow import Arrow

from ...domain.models.daily_state import DailyState
from .owner_crud_repository import OwnerCrudRepository

SomeDailyState = TypeVar("SomeDailyState", bound=DailyState)


class DailyStateRepository(
    OwnerCrudRepository[SomeDailyState, Arrow],
    Generic[SomeDailyState],
):
    """Interface for DailyState entity."""

    @abstractmethod
    def get_for_owner(self, owner_id: str, arg: Arrow) -> SomeDailyState | None:
        """Fetch the DailyState for an owner on a specific date."""

    @abstractmethod
    def get_for_owner_between(
        self, owner_id: str, start: Arrow, end: Arrow
    ) -> list[SomeDailyState]:
        """Fetch DailyStates for an owner between two dates (inclusive)."""

"""UserSleepRepository interface."""

from abc import abstractmethod
from typing import Generic, List, TypeVar

from ...domain.models.user_sleep import UserSleep
from .base_crud_repository import BaseCrudRepository

SomeUserSleep = TypeVar("SomeUserSleep", bound=UserSleep)


class UserSleepRepository(
    BaseCrudRepository[SomeUserSleep, str], Generic[SomeUserSleep]
):
    """Interface for the UserSleep repository."""

    @abstractmethod
    def get_user_sleeps_in_range(
        self, owner: str, start: str, end: str
    ) -> List[SomeUserSleep]:
        """Fetch UserSleeps for an owner with sleepDate in [start, end]."""

    @abstractmethod
    def get_user_sleeps_for_date(self, owner: str, date: str) -> List[SomeUserSleep]:
        """Fetch UserSleeps for an owner on a date."""

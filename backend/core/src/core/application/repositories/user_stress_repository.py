"""UserStressRepository interface."""

from abc import abstractmethod
from typing import Generic, List, TypeVar

from ...domain.models.user_stress import UserStress
from .base_crud_repository import BaseCrudRepository

SomeUserStress = TypeVar("SomeUserStress", bound=UserStress)


class UserStressRepository(
    BaseCrudRepository[SomeUserStress, str], Generic[SomeUserStress]
):
    """Interface for the UserStress repository."""

    @abstractmethod
    def get_user_stresses_in_range(
        self, owner: str, start: str, end: str
    ) -> List[SomeUserStress]:
        """Fetch UserStresses with stressDate in [start, end]."""

    @abstractmethod
    def get_user_stresses_for_date(
        self, owner: str, date: str
    ) -> List[SomeUserStress]:
        """Fetch UserStresses for an owner on a date."""

"""UserFoodRepository interface."""

from abc import abstractmethod
from typing import Generic, List, TypeVar

from arrow import Arrow

from ...domain.models.user_food import UserFood
from .owner_crud_repository import OwnerCrudRepository

SomeUserFood = TypeVar("SomeUserFood", bound=UserFood)


class UserFoodRepository(
    OwnerCrudRepository[SomeUserFood, Arrow], Generic[SomeUserFood]
):
    """Interface for the UserFood repository."""

    @abstractmethod
    def get_for_owner(self, owner: str, arg: Arrow) -> SomeUserFood | None:
        """Fetch the UserFood for an owner at a specific time."""

    @abstractmethod
    def get_for_owner_between(
        self, owner: str, start: Arrow, end: Arrow
    ) -> List[SomeUserFood]:
        """Fetch UserFoods for an owner with `eaten_at` in [start, end]."""

    @abstractmethod
    def get_for_owner_on_day(self, owner: str, arg: Arrow) -> List[SomeUserFood]:
        """Fetch UserFoods for an owner on the day of `arg`."""

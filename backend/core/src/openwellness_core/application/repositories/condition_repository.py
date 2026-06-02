"""ConditionRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.condition import Condition
from .owner_crud_repository import OwnerCrudRepository

SomeCondition = TypeVar("SomeCondition", bound=Condition)


class ConditionRepository(
    OwnerCrudRepository[SomeCondition, int],
    Generic[SomeCondition],
):
    """Interface for Condition entity."""

    @abstractmethod
    def get_for_owner(self, owner_id: str, arg: int) -> SomeCondition | None:
        """Fetch the Condition for an owner on a specific week."""

    @abstractmethod
    def get_for_owner_between(
        self, owner_id: str, start: int, end: int
    ) -> list[SomeCondition]:
        """Fetch Conditions for an owner between two weeks (inclusive)."""

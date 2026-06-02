"""GoalRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from arrow import Arrow

from ...domain.models.goal import Goal, SomeKind, SomeKindArg
from .owner_crud_repository import OwnerCrudRepository

SomeGoal = TypeVar("SomeGoal", bound=Goal)


class GoalRepository(OwnerCrudRepository[SomeGoal, Arrow], Generic[SomeGoal]):
    """Port for the Goal entity."""

    @abstractmethod
    def get_all_for_owner(self, owner_id: str, arg: Arrow) -> list[SomeGoal]:
        """Fetch all Goals for an owner whose startDate is the day of `arg`."""

    @abstractmethod
    def get_all_for_owner_by_kind(
        self, owner_id: str, arg: Arrow, kind: SomeKindArg | None = None
    ) -> list[SomeGoal]:
        """Fetch SomeGoals for an owner whose startDate is the day of `arg`,
        filtered by kind."""

    @abstractmethod
    def get_all_for_owner_between(
        self, owner_id: str, start: Arrow, end: Arrow
    ) -> list[SomeGoal]:
        """Fetch all Goals for an owner between `start` and `end`."""

    @abstractmethod
    def get_all_for_owner_by_kind_between(
        self,
        owner_id: str,
        start: Arrow,
        end: Arrow,
        kind: SomeKindArg | None = None,
    ) -> list[SomeGoal]:
        """Fetch Goals for an owner between `start` and `end`, filtered by kind."""

    @abstractmethod
    def get_for_owner_by_kind(
        self, owner_id: str, arg: Arrow, kind: SomeKind | None = None
    ) -> SomeGoal | None:
        """Fetch the latest created Goal for an owner on the day of `arg`."""

    @abstractmethod
    def get_for_owner_by_kind_between(
        self,
        owner_id: str,
        start: Arrow,
        end: Arrow,
        kind: SomeKindArg | None = None,
    ) -> list[SomeGoal]:
        """Fetch latest-per-day Goals for an owner between `start` and `end`."""

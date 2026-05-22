"""SharedGoalProgressRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.shared_goal_progress import SharedGoalProgress
from .owner_crud_repository import OwnerCrudRepository

SomeSharedGoalProgress = TypeVar("SomeSharedGoalProgress", bound=SharedGoalProgress)


class SharedGoalProgressRepository(
    OwnerCrudRepository[SomeSharedGoalProgress, str],
    Generic[SomeSharedGoalProgress],
):
    """Interface for SharedGoalProgress entity."""

    @abstractmethod
    def create_using(
        self, date: str, channels: list[str], owner: str, study_id: str
    ) -> SomeSharedGoalProgress:
        """Create a SharedGoalProgress using the given parameters."""

    @abstractmethod
    def get_for_owner(self, owner_id: str, arg: str) -> SomeSharedGoalProgress | None:
        """Fetch the SharedGoalProgress for an owner on a specific date."""

    @abstractmethod
    def get_for_owner_between(
        self, owner_id: str, start: str, end: str
    ) -> list[SomeSharedGoalProgress]:
        """Fetch SharedGoalProgresses for an owner between two dates."""

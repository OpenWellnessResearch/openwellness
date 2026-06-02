"""UserSettingsRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.user_settings import UserSettings
from .base_crud_repository import BaseCrudRepository

SomeUserSettings = TypeVar("SomeUserSettings", bound=UserSettings)


class UserSettingsRepository(
    BaseCrudRepository[SomeUserSettings, str], Generic[SomeUserSettings]
):
    """Port for the UserSettings entity."""

    @abstractmethod
    def get_for_owner(self, owner_id: str) -> SomeUserSettings | None:
        """Fetch the most recently created UserSettings for an owner."""

    @abstractmethod
    def get_all_for_owner(self, owner_id: str) -> list[SomeUserSettings]:
        """Fetch all UserSettings for an owner, ordered by created descending."""

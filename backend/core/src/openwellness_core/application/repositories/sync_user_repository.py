"""SyncUserRepository interface."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from ...domain.models.sync_user import SyncUser

SomeSyncUser = TypeVar("SomeSyncUser", bound="SyncUser")


class SyncUserRepository(ABC, Generic[SomeSyncUser]):
    """Interface for the SyncUser repository."""

    @abstractmethod
    def get_by_id(self, entity_id: str) -> SomeSyncUser | None:
        """Get a SyncUser by its ID."""

    @abstractmethod
    def save(self, user: SomeSyncUser) -> SomeSyncUser:
        """Save a SyncUser."""

"""MessageRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from arrow import Arrow

from ...domain.models.message import Message
from .base_crud_repository import BaseCrudRepository

SomeMessage = TypeVar("SomeMessage", bound=Message)


class MessageRepository(BaseCrudRepository[SomeMessage, str], Generic[SomeMessage]):
    """Port for the Message entity."""

    @abstractmethod
    def get_for_owner_between(
        self,
        owner: str,
        start: Arrow,
        end: Arrow,
        subtype: int | None = None,
        condition: int | None = None,
    ) -> list[SomeMessage]:
        """Fetch messages for an owner between start and end dates."""

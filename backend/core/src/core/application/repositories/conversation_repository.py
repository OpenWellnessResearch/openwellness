"""ConversationRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.conversation import Conversation
from .base_crud_repository import BaseCrudRepository

SomeConversation = TypeVar("SomeConversation", bound=Conversation)


class ConversationRepository(
    BaseCrudRepository[SomeConversation, str], Generic[SomeConversation]
):
    """Interface for Conversation entity."""

    @abstractmethod
    def get_for_filters(
        self, filters: list[Conversation.Filter]
    ) -> list[SomeConversation]:
        """Fetch Conversations matching a list of filters."""

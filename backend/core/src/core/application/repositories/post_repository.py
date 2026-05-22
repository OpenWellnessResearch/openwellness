"""PostRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.post import Post
from .base_crud_repository import BaseCrudRepository

SomePost = TypeVar("SomePost", bound=Post)


class PostRepository(BaseCrudRepository[SomePost, str], Generic[SomePost]):
    """Interface for Post entity."""

    @abstractmethod
    def get_for_channel_between(
        self,
        channel: str,
        start: float,
        end: float,
        conversation_id: str | None = None,
    ) -> list[SomePost]:
        """Fetch Posts in a channel between two timestamps."""

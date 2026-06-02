"""MessageDraftRepository interface."""

from abc import abstractmethod

from ...domain.models.message_draft import MessageDraft
from .base_crud_repository import BaseCrudRepository


class MessageDraftRepository(BaseCrudRepository[MessageDraft, str]):
    """Port for the MessageDraft entity."""

    @abstractmethod
    def get_for_study_subtype(
        self,
        study_id: str,
        subtype: int,
        week: int | None = None,
        day: int | None = None,
    ) -> list[MessageDraft]:
        """Fetch message drafts for a study subtype."""

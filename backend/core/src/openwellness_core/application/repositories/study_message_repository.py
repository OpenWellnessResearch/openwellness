"""StudyMessageRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.study_message import StudyMessage
from .base_crud_repository import BaseCrudRepository

SomeStudyMessage = TypeVar("SomeStudyMessage", bound=StudyMessage)
SomeMessageType = TypeVar("SomeMessageType", bound=int)


class StudyMessageRepository(
    BaseCrudRepository[SomeStudyMessage, dict],
    Generic[SomeStudyMessage, SomeMessageType],
):
    """Port for the StudyMessage entity."""

    @abstractmethod
    def get_for_study(self, study_id: str) -> list[SomeStudyMessage]:
        """Get all StudyMessages for a study."""

    @abstractmethod
    def get_for_study_message_type(
        self, study_id: str, message_type: SomeMessageType
    ) -> list[SomeStudyMessage]:
        """Get all StudyMessages for a study of a certain type."""

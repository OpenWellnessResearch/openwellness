"""ParticipantRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.participant import Participant
from .base_crud_repository import BaseCrudRepository
from .fetchable_by_study_repository import FetchableByStudyRepository

SomeParticipant = TypeVar("SomeParticipant", bound=Participant)


class ParticipantRepository(
    BaseCrudRepository[SomeParticipant, dict],
    FetchableByStudyRepository[SomeParticipant],
    Generic[SomeParticipant],
):
    """Port for the Participant entity."""

    @abstractmethod
    def get_by_num_study_id(self, num: str, study_id: str) -> SomeParticipant | None:
        """Get a participant by their participant number and study ID."""

    @abstractmethod
    def get_by_study_id(self, study_id: str) -> list[SomeParticipant]:
        """Get participants by study ID."""

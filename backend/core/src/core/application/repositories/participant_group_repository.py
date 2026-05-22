"""ParticipantGroupRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.participant_group import ParticipantGroup
from .base_crud_repository import BaseCrudRepository

SomeParticipantGroup = TypeVar("SomeParticipantGroup", bound=ParticipantGroup)


class ParticipantGroupRepository(
    BaseCrudRepository[SomeParticipantGroup, str], Generic[SomeParticipantGroup]
):
    """Interface for ParticipantGroup entity."""

    @abstractmethod
    def get_by_channel(self, channel: str) -> SomeParticipantGroup | None:
        """Fetch the ParticipantGroup by channel."""

    @abstractmethod
    def create_participant_group(
        self, owner: str, study_id: str, **kwargs
    ) -> SomeParticipantGroup:
        """Create a new ParticipantGroup."""

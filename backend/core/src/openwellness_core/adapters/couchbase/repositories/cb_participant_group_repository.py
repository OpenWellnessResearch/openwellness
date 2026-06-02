"""Couchbase repository for ParticipantGroup.

Channels derivation lives on `CBParticipantGroup.from_domain`, so the
legacy two-save pattern (`save → mutate channels → save`) is no longer
needed. A single `save` after `create_participant_group` writes the entity
with channels already set.
"""

from ....application.repositories.participant_group_repository import (
    ParticipantGroupRepository,
    SomeParticipantGroup,
)
from ....domain.models.participant_group import ParticipantGroup
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_participant_group import CBParticipantGroup
from .cb_base_repository import CBBaseRepository


class CBParticipantGroupRepository(
    ParticipantGroupRepository,
    CBBaseRepository[SomeParticipantGroup, CBParticipantGroup],
):
    """Couchbase repository for the ParticipantGroup entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: type[SomeParticipantGroup] = ParticipantGroup,
        persistence_type: type[CBParticipantGroup] = CBParticipantGroup,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def get_by_channel(self, channel: str) -> SomeParticipantGroup | None:
        doc_id = channel.split(":")[-1]
        return self.get_by_id(doc_id)

    def create_participant_group(
        self, owner: str, study_id: str, **kwargs
    ) -> SomeParticipantGroup:
        kwargs["owner"] = owner
        kwargs["studyId"] = study_id
        pg = self.init_entity_valid_fields(kwargs)
        return self.save(pg)

"""Mongo repository for Participant."""

from typing import Generic, Type

from bson.objectid import ObjectId

from ....application.repositories.participant_repository import (
    ParticipantRepository,
    SomeParticipant,
)
from ....domain.models.participant import Participant
from ....infrastructure.interfaces.collection_repository import CollectionRepository
from ..model.mongo_participant import MongoParticipant
from .mongo_base_repository import MongoBaseRepository


class MongoParticipantRepository(
    MongoBaseRepository[SomeParticipant, MongoParticipant],
    ParticipantRepository[SomeParticipant],
    Generic[SomeParticipant],
):
    """Mongo repository for the Participant entity."""

    def __init__(
        self,
        mongo_repo: CollectionRepository,
        entity_type: Type[SomeParticipant] = Participant,
        persistence_type: type[MongoParticipant] = MongoParticipant,
    ) -> None:
        super().__init__(mongo_repo, entity_type, persistence_type)
        self.entity_type: Type[SomeParticipant] = entity_type

    def get_by_num_study_id(self, num: str, study_id: str) -> SomeParticipant | None:
        results = self.get_by_query(
            {
                "participantNumber": num,
                "studyId": ObjectId(study_id),
            }
        )
        if len(results) == 0:
            return None
        return results[0]

    def get_by_study_id(self, study_id: str) -> list[SomeParticipant]:
        return self.get_by_query({"studyId": ObjectId(study_id)})

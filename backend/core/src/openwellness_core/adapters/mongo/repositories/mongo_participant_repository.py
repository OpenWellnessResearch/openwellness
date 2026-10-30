"""Mongo repository for Participant."""

from typing import Generic, Type

from ....application.repositories.participant_repository import (
    ParticipantRepository,
    SomeParticipant,
)
from ....domain.exceptions.domain_exception import EntityNotFoundException
from ....domain.models.participant import Participant
from ...interfaces.collection_repository import CollectionRepository
from ..model.mongo_participant import MongoParticipant
from .mongo_base_repository import MongoBaseRepository, object_id_or_none


class MongoParticipantRepository(
    MongoBaseRepository[SomeParticipant, MongoParticipant],
    ParticipantRepository[SomeParticipant],
    Generic[SomeParticipant],
):
    """Mongo repository for the Participant entity.

    Owns ObjectId coercion so the domain stays datastore-free (FOUND-04): the
    entity carries string ids and every write path goes through ``_to_doc``,
    which stores the reference ids as ObjectId. Reads are stringified by
    ``MongoBaseEntity``.
    """

    def __init__(
        self,
        mongo_repo: CollectionRepository,
        entity_type: Type[SomeParticipant] = Participant,
        persistence_type: type[MongoParticipant] = MongoParticipant,
    ) -> None:
        super().__init__(mongo_repo, entity_type, persistence_type)
        self.entity_type: Type[SomeParticipant] = entity_type

    def get_by_num_study_id(self, num: str, study_id: str) -> SomeParticipant | None:
        oid = object_id_or_none(study_id)
        if oid is None:
            return None
        results = self.get_by_query({"participantNumber": num, "studyId": oid})
        if len(results) == 0:
            return None
        return results[0]

    def get_by_study_id(self, study_id: str) -> list[SomeParticipant]:
        oid = object_id_or_none(study_id)
        if oid is None:
            return []
        return self.get_by_query({"studyId": oid})

    def _to_doc(self, entity: SomeParticipant) -> dict:
        doc = super()._to_doc(entity)
        for alias, required in (
            ("assignedCoachId", False),
            ("userId", False),
            ("studyId", True),
        ):
            value = doc.get(alias)
            if not required and not value:
                doc[alias] = None
                continue
            # A malformed (or, for studyId, empty) reference names no document.
            oid = object_id_or_none(value)
            if oid is None:
                raise EntityNotFoundException(f"{alias} {value} not found")
            doc[alias] = oid
        return doc

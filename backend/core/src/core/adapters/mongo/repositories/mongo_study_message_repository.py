"""Mongo repository for StudyMessage."""

from typing import Generic, Type

from ....application.repositories.study_message_repository import (
    SomeMessageType,
    SomeStudyMessage,
    StudyMessageRepository,
)
from ....domain.models.study_message import StudyMessage
from ....infrastructure.interfaces.collection_repository import CollectionRepository
from ..model.mongo_study_message import MongoStudyMessage
from .mongo_base_repository import MongoBaseRepository


class MongoStudyMessageRepository(
    StudyMessageRepository,
    MongoBaseRepository[SomeStudyMessage, MongoStudyMessage],
    Generic[SomeStudyMessage, SomeMessageType],
):
    """Mongo repository for the StudyMessage entity."""

    def __init__(
        self,
        mongo_repo: CollectionRepository,
        entity_type: Type[SomeStudyMessage] = StudyMessage,
        persistence_type: type[MongoStudyMessage] = MongoStudyMessage,
    ) -> None:
        super().__init__(mongo_repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def get_for_study(self, study_id: str) -> list[SomeStudyMessage]:
        return self.get_by_query({"studyId": study_id})

    def get_for_study_message_type(
        self, study_id: str, message_type: SomeMessageType
    ) -> list[SomeStudyMessage]:
        return self.get_by_query({"studyId": study_id, "messageType": message_type})

"""Mongo repository for Fitbit."""

from typing import Generic, Type

from ....application.repositories.fitbit_repository import (
    FitbitRepository,
    SomeFitbit,
)
from ....domain.models.fitbit import Fitbit
from ....infrastructure.interfaces.collection_repository import CollectionRepository
from ..model.mongo_fitbit import MongoFitbit
from .mongo_base_repository import MongoBaseRepository


class MongoFitbitRepository(
    MongoBaseRepository[SomeFitbit, MongoFitbit],
    FitbitRepository[SomeFitbit],
    Generic[SomeFitbit],
):
    """Mongo repository for the Fitbit entity."""

    def __init__(
        self,
        mongo_repo: CollectionRepository,
        entity_type: Type[SomeFitbit] = Fitbit,
        persistence_type: type[MongoFitbit] = MongoFitbit,
    ) -> None:
        super().__init__(mongo_repo, entity_type, persistence_type)
        self.entity_type: Type[SomeFitbit] = entity_type

    def get_by_participant_id(self, participant_id: str) -> SomeFitbit | None:
        result = self.get_by_query({"participantId": participant_id})
        return result[0] if len(result) == 1 else None

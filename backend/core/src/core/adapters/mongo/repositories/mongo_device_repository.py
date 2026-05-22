"""Mongo repository for Device."""

from typing import Generic, Type

from bson.objectid import ObjectId

from ....application.repositories.device_repository import (
    DeviceRepository,
    SomeDevice,
)
from ....domain.models.device import Device
from ....infrastructure.interfaces.collection_repository import CollectionRepository
from ..model.mongo_device import MongoDevice
from .mongo_base_repository import MongoBaseRepository


class MongoDeviceRepository(
    MongoBaseRepository[SomeDevice, MongoDevice],
    DeviceRepository[SomeDevice],
    Generic[SomeDevice],
):
    """Mongo repository for the Device entity."""

    def __init__(
        self,
        mongo_repo: CollectionRepository,
        entity_type: Type[SomeDevice] = Device,
        persistence_type: type[MongoDevice] = MongoDevice,
    ) -> None:
        super().__init__(mongo_repo, entity_type, persistence_type)
        self.entity_type: Type[SomeDevice] = entity_type

    def get_by_serial_number(self, serial_number: str) -> list[SomeDevice]:
        return self.get_by_query({"serialNumber": serial_number})

    def get_by_participant_id(self, participant_id: str) -> list[SomeDevice]:
        return self.get_by_query({"participantId": ObjectId(participant_id)})

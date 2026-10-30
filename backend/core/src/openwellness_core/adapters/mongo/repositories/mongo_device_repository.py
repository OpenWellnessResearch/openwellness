"""Mongo repository for Device."""

from typing import Generic, Type

from ....application.repositories.device_repository import (
    DeviceRepository,
    SomeDevice,
)
from ....domain.models.device import Device
from ...interfaces.collection_repository import CollectionRepository
from ..model.mongo_device import MongoDevice
from .mongo_base_repository import MongoBaseRepository, object_id_or_none


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
        oid = object_id_or_none(participant_id)
        if oid is None:
            return []
        return self.get_by_query({"participantId": oid})

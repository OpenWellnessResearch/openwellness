"""DeviceRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.device import Device
from .base_crud_repository import BaseCrudRepository

SomeDevice = TypeVar("SomeDevice", bound=Device)


class DeviceRepository(BaseCrudRepository[SomeDevice, dict], Generic[SomeDevice]):
    """Port for the Device entity."""

    @abstractmethod
    def get_by_serial_number(self, serial_number: str) -> list[SomeDevice]:
        """Get a device by its serial number."""

    @abstractmethod
    def get_by_participant_id(self, participant_id: str) -> list[SomeDevice]:
        """Get a device by its participant id."""

"""FitbitHeartRecordRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.fitbit_heart_record import FitbitHeartRecord
from .owner_crud_repository import OwnerCrudRepository

SomeFitbitHeartRecord = TypeVar("SomeFitbitHeartRecord", bound=FitbitHeartRecord)


class FitbitHeartRecordRepository(
    OwnerCrudRepository[SomeFitbitHeartRecord, str],
    Generic[SomeFitbitHeartRecord],
):
    """Interface for FitbitHeartRecord entity."""

    @abstractmethod
    def create_from_raw(self, data: dict) -> SomeFitbitHeartRecord:
        """Create a FitbitHeartRecord from raw data."""

    @abstractmethod
    def update_from_raw(
        self, record: SomeFitbitHeartRecord, data: dict
    ) -> SomeFitbitHeartRecord:
        """Update a FitbitHeartRecord from raw data."""

    @abstractmethod
    def get_for_owner(self, owner_id: str, arg: str) -> SomeFitbitHeartRecord | None:
        """Fetch the FitbitHeartRecord for an owner on a specific date."""

    @abstractmethod
    def get_for_owner_between(
        self, owner_id: str, start: str, end: str
    ) -> list[SomeFitbitHeartRecord]:
        """Fetch FitbitHeartRecords for an owner between two dates (inclusive)."""

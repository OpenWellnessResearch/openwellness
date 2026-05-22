"""FitbitRecordRepository interface."""

from abc import abstractmethod

from ...domain.models.fitbit_record import FitbitRecord
from ..dtos.activity_data_dto import ActivityDataInputDTO
from .owner_crud_repository import OwnerCrudRepository


class FitbitRecordRepository(OwnerCrudRepository[FitbitRecord, str]):
    """Interface for FitbitRecord."""

    @abstractmethod
    def create_from_notification(
        self,
        pid: str,
        fitbit_date: str,
        study_id: str,
        data: ActivityDataInputDTO,
    ) -> FitbitRecord:
        """Create a FitbitRecord from a notification."""

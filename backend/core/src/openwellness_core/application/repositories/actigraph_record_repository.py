"""ActigraphRecordRepository interface."""

from abc import abstractmethod

from arrow import Arrow

from ...domain.models.actigraph_record import ActigraphRecord
from .owner_crud_repository import OwnerCrudRepository


class ActigraphRecordRepository(OwnerCrudRepository[ActigraphRecord, Arrow]):
    """Interface for ActigraphRecord."""

    @abstractmethod
    def get_for_owner(self, owner_id: str, arg: Arrow) -> ActigraphRecord | None:
        """DO NOT USE."""

    @abstractmethod
    def get_for_owner_between(
        self, owner_id: str, start: Arrow, end: Arrow
    ) -> list[ActigraphRecord]:
        """Fetch actigraph records whose timestamp_utc is between start and end."""

"""PhysicalActivityRepository interface."""

from abc import abstractmethod
from typing import List

from ...domain.models.physical_activity import PhysicalActivity
from .base_crud_repository import BaseCrudRepository


class PhysicalActivityRepository(BaseCrudRepository[PhysicalActivity, str]):
    """Port for the PhysicalActivity entity."""

    @abstractmethod
    def fetch_all_in_range(
        self, owner: str, start: float, end: float, descending: bool = False
    ) -> List[PhysicalActivity]:
        """Fetch all PhysicalActivities in a time range, regardless of MET."""

    @abstractmethod
    def fetch_for_week_of_date(
        self, owner: str, date: float
    ) -> List[PhysicalActivity]:
        """Fetch PhysicalActivities for the week containing `date` (US/Central)."""

    @abstractmethod
    def fetch_for_date(self, owner: str, date: float) -> List[PhysicalActivity]:
        """Fetch PhysicalActivities for an owner on a date."""

    @abstractmethod
    def fetch_mvpa_in_range(
        self, owner: str, start: float, end: float
    ) -> List[PhysicalActivity]:
        """Fetch MVPA (met ≥ 3) records for an owner in a time range."""

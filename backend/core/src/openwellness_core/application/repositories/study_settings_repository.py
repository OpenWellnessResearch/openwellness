"""StudySettingsRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.study_settings import StudySettings
from .base_crud_repository import BaseCrudRepository

SomeStudySettings = TypeVar("SomeStudySettings", bound=StudySettings)


class StudySettingsRepository(
    BaseCrudRepository[SomeStudySettings, str], Generic[SomeStudySettings]
):
    """Port for the StudySettings entity."""

    @abstractmethod
    def get_for_study_id(self, study_id: str) -> SomeStudySettings | None:
        """Fetch StudySettings by study ID."""

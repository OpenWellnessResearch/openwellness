"""JobRuleRepository interface."""

from abc import abstractmethod
from typing import Generic, TypeVar

from ...domain.models.job_rule import JobRule
from .base_crud_repository import BaseCrudRepository

SomeJobRule = TypeVar("SomeJobRule", bound=JobRule)


class JobRuleRepository(BaseCrudRepository[SomeJobRule, str], Generic[SomeJobRule]):
    """Port for the JobRule entity."""

    SomeEventTrigger = JobRule.EventTrigger | None

    @abstractmethod
    def get_by_study_id(self, study_id: str) -> list[SomeJobRule]:
        """Fetch JobRules by study ID."""

    @abstractmethod
    def get_by_study_subtype(self, study_id: str, subtype: int) -> SomeJobRule | None:
        """Fetch a JobRule by study and subtype."""

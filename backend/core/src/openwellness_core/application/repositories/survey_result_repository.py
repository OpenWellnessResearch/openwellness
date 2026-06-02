"""SurveyResultRepository interface."""

from abc import abstractmethod
from typing import Generic, List, Optional, TypeVar, Union

from ...domain.models.survey_result import SurveyResult
from .base_crud_repository import BaseCrudRepository

SomeSurveyResult = TypeVar("SomeSurveyResult", bound=SurveyResult)
KindArg = Union[int, List[int]]


class SurveyResultRepository(
    BaseCrudRepository[SomeSurveyResult, str], Generic[SomeSurveyResult]
):
    """Port for the SurveyResult entity."""

    @abstractmethod
    def get_survey_results_on(
        self,
        owner: str,
        date: str,
        kind: Optional[KindArg] = None,
    ) -> SomeSurveyResult | None:
        """Get survey results for a participant on a date."""

    @abstractmethod
    def get_survey_results_between(
        self,
        owner: str,
        start: str,
        end: str,
        kind: Optional[KindArg] = None,
    ) -> list[SomeSurveyResult]:
        """Get survey results for a participant between two dates."""

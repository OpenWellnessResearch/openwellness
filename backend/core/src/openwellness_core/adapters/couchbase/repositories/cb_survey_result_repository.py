"""Couchbase repository for SurveyResult."""

from typing import Any, List, Optional, Type, TypeVar, Union

from ....application.repositories.survey_result_repository import (
    SomeSurveyResult,
    SurveyResultRepository,
)
from ....domain.models.survey_result import SurveyResult
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_survey_result import CBSurveyResult
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository

T = TypeVar("T", bound=int)
KindArg = Union[T, List[T]]


class CBSurveyResultRepository(
    SurveyResultRepository[SomeSurveyResult],
    CBBaseRepository[SomeSurveyResult, CBSurveyResult],
):
    """Couchbase repository for the SurveyResult entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: Type[SomeSurveyResult] = SurveyResult,
        persistence_type: type[CBSurveyResult] = CBSurveyResult,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def get_survey_results_on(
        self,
        owner: str,
        date: str,
        kind: Optional[KindArg] = None,
    ) -> SomeSurveyResult | None:
        q, params = self._generate_query(owner, date, date, kind)
        results = self.get_by_query(q, params)
        return results[0] if results else None

    def get_survey_results_between(
        self,
        owner: str,
        start: str,
        end: str,
        kind: Optional[KindArg] = None,
    ) -> list[SomeSurveyResult]:
        q, params = self._generate_query(owner, start, end, kind)
        return self.get_by_query(q, params)

    def _generate_query(
        self,
        owner: str,
        start: str,
        end: str,
        kind: Optional[KindArg],
    ) -> tuple[str, dict[str, Any]]:
        b = bucket_ident(self.repo.bucket)
        params: dict[str, Any] = {
            "type": CBSurveyResult.type,
            "owner": owner,
            "start": start,
            "end": end,
        }
        kind_clause, kind_params = self._kind_expression(kind)
        params.update(kind_params)
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND owner = $owner "
            f"AND surveyDate BETWEEN $start AND $end "
            f"{kind_clause}"
            f"ORDER BY surveyDate, createdAt"
        )
        return q, params

    def _kind_expression(
        self, kind: Optional[KindArg]
    ) -> tuple[str, dict[str, Any]]:
        if kind is None:
            return "AND (kind IS MISSING OR kind IS NULL) ", {}
        if isinstance(kind, list):
            return "AND kind IN $kinds ", {"kinds": [int(k) for k in kind]}
        if isinstance(kind, int) or hasattr(kind, "real"):
            return "AND kind = $kind ", {"kind": int(kind)}
        raise Exception(f"Invalid `kind` type: {type(kind)}")

"""Couchbase persistence for SurveyResult."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBSurveyResult(CBBaseOwnerEntity):
    """Persistence for SurveyResult."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "SurveyResult"

    survey_date: Any = Field(alias="surveyDate", default=None)

"""SurveyResult domain model."""

from dataclasses import dataclass

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class SurveyResult(BaseOwnerEntity):
    """A survey result for a participant."""

    survey_date: str
    """Date in YYYY-MM-DD format."""

"""FitbitRecord domain model."""

from dataclasses import dataclass

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class FitbitRecord(BaseOwnerEntity):
    """Activity data from a Fitbit device for a specific day."""

    active_score: int
    activity_calories: int
    calories_bmr: int
    calories_out: int
    distances: list
    fairly_active_minutes: int
    fitbit_date: str
    lightly_active_minutes: int
    marginal_calories: int
    sedentary_minutes: int
    steps: int
    very_active_minutes: int

    @property
    def year_month_day(self) -> str:
        return self.fitbit_date

    def mvpa_minutes(self) -> int:
        return self.fairly_active_minutes + self.very_active_minutes

    def non_mvpa_minutes(self) -> int:
        return self.lightly_active_minutes

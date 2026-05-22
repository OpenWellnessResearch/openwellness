"""DTO for activity data input."""

from dataclasses import dataclass


@dataclass
class ActivityDataInputDTO:
    """Input DTO for Fitbit-style activity data."""

    active_score: int
    activity_calories: int
    calories_bmr: int
    calories_out: int
    distances: list
    fairly_active_minutes: int
    lightly_active_minutes: int
    marginal_calories: int
    sedentary_minutes: int
    steps: int
    very_active_minutes: int

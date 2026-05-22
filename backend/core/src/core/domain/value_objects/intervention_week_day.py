"""A specific week-day in an intervention."""

from dataclasses import dataclass


@dataclass(kw_only=True)
class InterventionWeekDay:
    """A week day for an intervention."""

    week: int
    day: int

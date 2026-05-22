"""PhysicalActivity domain model."""

from dataclasses import dataclass

import arrow

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class PhysicalActivity(BaseOwnerEntity):
    """Self-reported physical activity entry."""

    activity_id: str
    name: str
    item_description: str
    minutes: int
    intensity: int
    date_of_activity: float
    enjoyment: int
    met: float
    steps: int = 0

    def mvpa_minutes(self) -> int:
        return 0 if self.met < 3.0 else self.minutes

    @property
    def year_month_day(self) -> str:
        return arrow.get(self.date_of_activity).format("YYYY-MM-DD")

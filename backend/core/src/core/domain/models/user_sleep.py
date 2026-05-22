"""UserSleep domain model."""

from dataclasses import dataclass

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class UserSleep(BaseOwnerEntity):
    """A single sleep session, from time in bed to time out of bed."""

    awake_time: float
    in_bed_time: float
    minutes_awoken: int
    minutes_to_sleep: int
    out_of_bed_time: float
    sleep_date: str
    rating: int
    times_awoken: int

    def year_month_day(self) -> str:
        return self.sleep_date

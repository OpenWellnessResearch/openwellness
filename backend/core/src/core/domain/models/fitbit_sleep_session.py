"""FitbitSleepSession domain model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import arrow

from ..value_objects.sleep_metric import SleepMetric
from .base_owner_entity import BaseOwnerEntity

# pylint: disable=invalid-name


@dataclass(kw_only=True)
class FitbitSleepSession(BaseOwnerEntity):
    """A single sleep session within a FitbitSleep document."""

    date_of_sleep: str
    duration: int
    efficiency: int
    info_code: int
    is_main_sleep: bool
    levels: Dict
    log_id: int
    minutes_after_wakeup: int
    minutes_asleep: int
    minutes_awake: int
    minutes_to_fall_asleep: int
    sleep_id: str
    sleep_type: str
    start_date: str
    start_time: str
    time_in_bed: int

    @property
    def start_arrow(self):
        return arrow.get(self.start_time)

    @property
    def end_arrow(self):
        return self.start_arrow.shift(minutes=+self.time_in_bed)

    @property
    def time_in_bed_in_seconds(self):
        return self.time_in_bed * 60.0

    def __post_init__(self) -> None:
        super().__post_init__()
        self.id = f"{self.owner}-{self.log_id}"

    def year_month_day(self) -> str:
        return self.date_of_sleep

    def metric(self) -> SleepMetric:
        return SleepMetric(
            start=self.start_arrow,
            end=self.end_arrow,
            duration_in_seconds=self.duration // 1000,
        )

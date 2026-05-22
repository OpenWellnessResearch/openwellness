"""StudyWeekDay dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from arrow import Arrow


@dataclass
class StudyWeekDay:
    """Week and day of the study relative to a start date."""

    week: int
    day: int
    start_date: Arrow
    compare_date: Arrow

    def __post_init__(self):
        assert (
            self.start_date.tzinfo == self.compare_date.tzinfo
        ), "Timezones must match"

    def study_date_for(self, week: int, day: int) -> StudyWeekDay:
        start = self.start_date.floor("week")
        compare = start.shift(weeks=week - 1, days=day - 1)
        return StudyWeekDay(week, day, start, compare)

    def to_tuple(self) -> Tuple[int, int]:
        return self.week, self.day

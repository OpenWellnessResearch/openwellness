"""UserSettings domain model."""

import datetime
from dataclasses import dataclass, field

import arrow

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class UserSettings(BaseOwnerEntity):
    """Settings for a study participant."""

    wake_time: float | None = field(default=None)
    sleep_time: float | None = field(default=None)
    start_date: float | None = field(default=None)
    end_study_message: str | None = field(default=None)
    should_email_notifications: bool = field(default=True)
    run_in_start_date: float = field(default=0)

    @property
    def start_date_arrow(self) -> arrow.Arrow:
        assert self.start_date is not None
        return arrow.get(self.start_date)

    @property
    def sleep_time_arrow(self) -> arrow.Arrow:
        assert self.sleep_time is not None
        return arrow.get(self.sleep_time)

    @property
    def sleep_today(self) -> arrow.Arrow:
        return self._to_today(self.sleep_time_arrow)

    @property
    def wake_time_arrow(self) -> arrow.Arrow:
        assert self.wake_time is not None
        return arrow.get(self.wake_time)

    @property
    def wake_today(self) -> arrow.Arrow:
        return self._to_today(self.wake_time_arrow)

    def _to_today(self, date: arrow.Arrow) -> arrow.Arrow:
        today = arrow.utcnow()
        return date.replace(year=today.year, month=today.month, day=today.day)

    def get_intervention_week(self, is_utc: bool = True) -> int:
        current_date = arrow.Arrow.now()
        tz_string = ""

        if is_utc:
            tz_string = "UTC"
            if current_date.tzinfo.utcoffset(None) != datetime.timedelta(0):
                raise ValueError("Current date must be in UTC timezone")
        else:
            tz_string = "Local"
            if current_date.tzinfo.utcoffset(None) == datetime.timedelta(0):
                raise ValueError("Current date must be in Local timezone")

        if self.start_date_arrow.tzinfo != current_date.tzinfo:
            raise ValueError(f"Both dates must be in {tz_string} timezone")

        start_week = self.start_date_arrow.floor("week")
        current_week = current_date.floor("week")
        return ((current_week - start_week).days // 7) + 1

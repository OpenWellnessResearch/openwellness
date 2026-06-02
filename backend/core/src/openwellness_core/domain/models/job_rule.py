"""JobRule entity."""

from dataclasses import dataclass, field
from enum import IntEnum

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class JobRule(BaseOwnerEntity):
    """Constraints for scheduling a job."""

    class EventTrigger(IntEnum):
        ACTIVITY = 1
        FITBIT_HEART_RECORD = 2
        POST = 3

    name: str
    subtype: int

    days_valid: list[int] | None = field(default=None)
    description: str | None = field(default=None)
    event_trigger: EventTrigger | None = field(default=None)
    processor: str | None = field(default=None)
    related_subtypes: list[int] | None = field(default=None)
    time_trigger: int | None = field(default=None)
    weeks_valid: list[int] | None = field(default=None)

    def __post_init__(self) -> None:
        super().__post_init__()
        if isinstance(self.event_trigger, int):
            self.event_trigger = self.EventTrigger(self.event_trigger)

    def validate(self, week: int, day: int, app_group: int | None = None) -> bool:
        week_is_valid = self.weeks_valid is None or week in self.weeks_valid
        day_is_valid = self.days_valid is None or day in self.days_valid
        return week_is_valid and day_is_valid

    def has_event_trigger(self, trigger: EventTrigger | None = None) -> bool:
        if trigger is None:
            return self.event_trigger is not None
        return self.event_trigger == trigger

    def has_time_trigger(self, trigger: int | None = None) -> bool:
        if trigger is None:
            return self.time_trigger is not None
        return self.time_trigger == trigger

    @staticmethod
    def generate_id(study_id: str, subtype: int) -> str:
        return f"JobRule:{study_id}:{subtype}"

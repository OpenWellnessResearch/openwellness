"""Participant entity."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Optional
from zoneinfo import ZoneInfo

from bson.objectid import ObjectId

from .base_entity import BaseEntity


@dataclass
class Participant(BaseEntity):
    """A participant enrolled in a study."""

    class Gender(IntEnum):
        FEMALE = 0
        MALE = 1

    class Type(IntEnum):
        DEMO = -1
        PARTICIPANT = 0
        BUDDY = 1

    assigned_coach_id: Optional[ObjectId] = None
    couch_id: str = field(default="", metadata={"deprecated": True})
    time_created: datetime = field(default_factory=datetime.now)
    user_id: Optional[ObjectId] = None
    study_id: ObjectId = field(default_factory=ObjectId)
    google_id: Optional[str] = None
    device_id: Optional[str] = None
    is_active: bool = False
    participant_number: str = ""
    assessment_weight: float = 0.0
    start_weight: float = 0.0
    height_in_inches: float = 0.0
    participant_type: Type = Type.PARTICIPANT
    tz: Optional[str] = None
    gender: Optional[Gender] = None

    def __post_init__(self):
        if self.gender and isinstance(self.gender, int):
            self.gender = self.Gender(self.gender)
        if self.participant_type and isinstance(self.participant_type, int):
            self.participant_type = self.Type(self.participant_type)

    @property
    def id_number(self) -> str:
        return f"{self.participant_number} ({self.id})"

    def get_utc_seconds_offset(self) -> float:
        if not self.tz or self.tz == "":
            return 0.0

        tz = ZoneInfo(self.tz)
        current_time = datetime.now(tz)
        return current_time.utcoffset().total_seconds()

"""UTC and participant times helper."""

from dataclasses import dataclass, field

from arrow import Arrow
from arrow import get as arrow_get


@dataclass
class UTCAndParticipantTimes:
    """Pair of UTC and participant-local times, derived from a participant TZ."""

    participant_timezone: str
    utc_time: Arrow = field(default_factory=arrow_get)
    participant_time: Arrow = field(init=False)

    def __post_init__(self):
        self.participant_timezone = self.participant_timezone or "America/Chicago"
        self.participant_time = self.utc_time.to(self.participant_timezone)

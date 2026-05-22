"""WeightGoalStudyMessage entity."""

from dataclasses import dataclass
from enum import IntEnum

from .study_message import StudyMessage


@dataclass(kw_only=True)
class WeightGoalStudyMessage(StudyMessage):
    """Weight goal study message."""

    class MessageType(IntEnum):
        HEALTHY = 0
        GOOD = 1
        BAD = 2

    message_type: MessageType

    def __post_init__(self) -> None:
        if isinstance(self.message_type, int):
            self.message_type = self.MessageType(self.message_type)

    def format_message(self, weight_goal: float):
        self.message = self.message.format(f"{weight_goal:.0f}")

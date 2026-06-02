"""WeightCondition domain entity."""

from dataclasses import dataclass, field

from ...value_objects.weight_goal_level import WeightGoalLevel
from .base import Condition


@dataclass(kw_only=True)
class WeightCondition(Condition):
    """State of a Participant's weight goal."""

    weight_goal_level: WeightGoalLevel = WeightGoalLevel.NOT_MET_ORIGINAL
    weight_loss_protocol: int = 0
    weight_start_id: str | None = field(default=None)
    weight_end_id: str | None = field(default=None)

    def __post_init__(self) -> None:
        super().__post_init__()
        if isinstance(self.weight_goal_level, int):
            self.weight_goal_level = WeightGoalLevel(self.weight_goal_level)

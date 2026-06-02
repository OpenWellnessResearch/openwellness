"""Weight goal achievement levels."""

from __future__ import annotations

from enum import IntEnum


class WeightGoalLevel(IntEnum):
    """Weight goal achievement levels."""

    NOT_MET_ORIGINAL = 0
    MET_ORIGINAL = 1
    MET_FIRST_NEW = 2
    MET_SECOND_NEW = 3
    HEALTHY_WEIGHT = 4

    @property
    def percentage(self) -> float:
        return {
            WeightGoalLevel.NOT_MET_ORIGINAL: 0.05,
            WeightGoalLevel.MET_ORIGINAL: 0.07,
            WeightGoalLevel.MET_FIRST_NEW: 0.10,
            WeightGoalLevel.MET_SECOND_NEW: 0.00,
            WeightGoalLevel.HEALTHY_WEIGHT: 0.00,
        }[self]

    def earliest_week_level_allowed(self) -> int:
        return {
            WeightGoalLevel.NOT_MET_ORIGINAL: 0,
            WeightGoalLevel.MET_ORIGINAL: 12,
            WeightGoalLevel.MET_FIRST_NEW: 24,
            WeightGoalLevel.HEALTHY_WEIGHT: 24,
        }[self]

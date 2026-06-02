"""LegacyGoal for legacy studies."""

from dataclasses import dataclass, field

from .base import Goal


@dataclass(kw_only=True)
class LegacyGoal(Goal):
    """A legacy-study Goal of intended targets."""

    activity: float = field(default=0.0)
    calories: float = field(default=0.0)
    fat: float = field(default=0.0)
    steps: int = field(default=0)
    weight: float = field(default=0.0)

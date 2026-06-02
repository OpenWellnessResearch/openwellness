"""WeeklyGoal."""

from dataclasses import dataclass

from .base import Goal
from .kind import Kind


@dataclass(kw_only=True)
class WeeklyGoal(Goal):
    """A goal classified as `Kind.WEEKLY`."""

    kind: Kind = Kind.WEEKLY

    def __post_init__(self) -> None:
        super().__post_init__()
        if isinstance(self.kind, int):
            self.kind = Kind.WEEKLY
        assert self.kind == Kind.WEEKLY

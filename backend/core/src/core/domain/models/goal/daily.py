"""DailyGoal."""

from dataclasses import dataclass

from .base import Goal
from .kind import Kind


@dataclass(kw_only=True)
class DailyGoal(Goal):
    """A goal classified as `Kind.DAILY`."""

    kind: Kind

    def __post_init__(self) -> None:
        super().__post_init__()
        if isinstance(self.kind, int):
            self.kind = Kind.DAILY
        assert self.kind == Kind.DAILY

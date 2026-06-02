"""SleepMetric value object."""

from __future__ import annotations

from dataclasses import dataclass, field

import arrow
from arrow import Arrow


@dataclass(frozen=True)
class SleepMetric:
    """A sleep metric: start, end, and duration."""

    start: Arrow = field(default_factory=lambda: arrow.get())
    end: Arrow = field(default_factory=lambda: arrow.get())
    duration_in_seconds: int = -1

    @property
    def duration_in_minutes(self):
        return int(float(self.duration_in_seconds) / 60.0)

    def __post_init__(self):
        if self.start > self.end or self.duration_in_seconds < 0:
            raise ValueError("Invalid start and end times or duration")

    def percent_overlap_by(self, other_metric: SleepMetric, buffer: int = 0) -> float:
        if other_metric.end < self.start or other_metric.start > self.end:
            return 0.0

        start = max(self.start, other_metric.start)
        end = min(self.end, other_metric.end)

        duration = self.duration_in_seconds
        comparison = (end - start).total_seconds() + (buffer * 60)
        comparison = min(comparison, duration)

        return comparison / duration if duration > 0 else 0.0

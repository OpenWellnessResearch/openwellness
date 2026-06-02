"""ActigraphRecord domain model."""

import math
from dataclasses import dataclass, field

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class ActigraphRecord(BaseOwnerEntity):
    """Activity data from an Actigraph device for a specific time."""

    timestamp_utc: float
    timestamp_subject_tz: str
    steps: int
    wear: bool

    axis_x_counts: int = field(default=0)
    axis_y_counts: int = field(default=0)
    axis_z_counts: int = field(default=0)
    intensity: float = field(default=0.0)

    def calculate_intensity(self) -> float:
        x2 = self.axis_x_counts * self.axis_x_counts
        y2 = self.axis_y_counts * self.axis_y_counts
        z2 = self.axis_z_counts * self.axis_z_counts
        return math.sqrt(x2 + y2 + z2)

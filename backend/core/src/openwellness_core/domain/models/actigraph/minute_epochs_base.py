"""Base minute epochs data."""

from dataclasses import dataclass


@dataclass
class MinuteEpochsBase:
    """Base for minute epochs data."""

    steps: int
    wear: bool
    axis_x_counts: int
    axis_y_counts: int
    axis_z_counts: int

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            steps=data["Steps"],
            wear=data["Wear"],
            axis_x_counts=data["AxisXCounts"],
            axis_y_counts=data["AxisYCounts"],
            axis_z_counts=data["AxisZCounts"],
        )

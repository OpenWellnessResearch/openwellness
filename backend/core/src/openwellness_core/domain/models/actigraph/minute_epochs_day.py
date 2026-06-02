"""Minute epochs for a subject on a given day."""

from dataclasses import dataclass

from .minute_epochs_base import MinuteEpochsBase


@dataclass
class MinuteEpochsDay(MinuteEpochsBase):
    """Minute epochs for a given subject on a given day."""

    timestamp: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            steps=data["Steps"],
            wear=data["Wear"],
            axis_x_counts=data["AxisXCounts"],
            axis_y_counts=data["AxisYCounts"],
            axis_z_counts=data["AxisZCounts"],
            timestamp=data["Timestamp"],
        )

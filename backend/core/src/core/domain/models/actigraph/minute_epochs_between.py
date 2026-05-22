"""Minute epochs for a subject in a time range."""

from dataclasses import dataclass

from .minute_epochs_base import MinuteEpochsBase


@dataclass
class MinuteEpochsBetween(MinuteEpochsBase):
    """Minute epochs for a given subject between specified time range."""

    timestamp_utc: float
    timestamp_subject_tz: str

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            steps=data["Steps"],
            wear=data["Wear"],
            axis_x_counts=data["AxisXCounts"],
            axis_y_counts=data["AxisYCounts"],
            axis_z_counts=data["AxisZCounts"],
            timestamp_utc=data["TimestampUTC"],
            timestamp_subject_tz=data["TimestampSubjectTZ"],
        )

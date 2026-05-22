"""Couchbase persistence for ActigraphRecord."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBActigraphRecord(CBBaseOwnerEntity):
    """Persistence for ActigraphRecord."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "ActigraphRecord"

    timestamp_utc: Any = Field(default=None, alias="timestampUTC")
    timestamp_subject_tz: Any = Field(default=None, alias="timestampSubjectTZ")
    steps: Any = None
    wear: Any = None
    axis_x_counts: Any = Field(default=None, alias="axisXCounts")
    axis_y_counts: Any = Field(default=None, alias="axisYCounts")
    axis_z_counts: Any = Field(default=None, alias="axisZCounts")
    intensity: Any = None

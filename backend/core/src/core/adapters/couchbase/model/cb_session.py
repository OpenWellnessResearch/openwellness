"""Couchbase persistence for Session."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBSession(CBBaseOwnerEntity):
    """Persistence for Session."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "Session"

    views: Any = None
    session_type: Any = Field(default=None, alias="sessionType")
    time_start_in_ms: Any = Field(default=None, alias="timeStartInMS")
    duration_in_ms: Any = Field(default=None, alias="durationInMS")

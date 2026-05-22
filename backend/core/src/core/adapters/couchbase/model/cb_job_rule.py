"""Couchbase persistence for JobRule."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBJobRule(CBBaseOwnerEntity):
    """Persistence for JobRule."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "JobRule"

    name: Any = None
    subtype: Any = None
    days_valid: Any = Field(default=None, alias="daysValid")
    description: Any = None
    event_trigger: Any = Field(default=None, alias="eventTrigger")
    processor: Any = None
    related_subtypes: Any = Field(default=None, alias="relatedSubtypes")
    time_trigger: Any = Field(default=None, alias="timeTrigger")
    weeks_valid: Any = Field(default=None, alias="weeksValid")

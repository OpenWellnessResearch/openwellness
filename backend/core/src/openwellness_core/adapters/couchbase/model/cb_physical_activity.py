"""Couchbase persistence for PhysicalActivity."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBPhysicalActivity(CBBaseOwnerEntity):
    """Persistence for PhysicalActivity."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "PhysicalActivity"

    activity_id: Any = Field(default=None, alias="activityId")
    name: Any = None
    item_description: Any = Field(default=None, alias="itemDescription")
    minutes: Any = None
    intensity: Any = None
    date_of_activity: Any = Field(default=None, alias="dateOfActivity")
    enjoyment: Any = None
    met: Any = None
    steps: Any = None

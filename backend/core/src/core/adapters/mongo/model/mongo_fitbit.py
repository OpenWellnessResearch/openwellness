"""Mongo persistence for Fitbit."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .mongo_base_entity import MongoBaseEntity


class MongoFitbit(MongoBaseEntity):
    """Persistence for Fitbit."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    collection: ClassVar[str] = "fitbits"

    participant_id: Any = Field(alias="participantId", default=None)
    access_token: Any = Field(alias="accessToken", default=None)
    refresh_token: Any = Field(alias="refreshToken", default=None)
    owner_id: Any = Field(alias="ownerId", default=None)
    subscription_id: Any = Field(alias="subscriptionId", default=None)
    time_created: Any = Field(alias="timeCreated", default=None)

"""Mongo persistence for Device."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .mongo_base_entity import MongoBaseEntity


class MongoDevice(MongoBaseEntity):
    """Persistence for Device."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    collection: ClassVar[str] = "devices"

    serial_number: Any = Field(alias="serialNumber", default=None)
    platform: Any = None
    participant_id: Any = Field(alias="participantId", default=None)
    time_created: Any = Field(alias="timeCreated", default=None)
    is_standard_time: Any = Field(alias="isStandardTime", default=None)

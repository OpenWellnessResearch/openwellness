"""Mongo persistence for StudyMessage."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .mongo_base_entity import MongoBaseEntity


class MongoStudyMessage(MongoBaseEntity):
    """Persistence for StudyMessage."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    collection: ClassVar[str] = "studyMessages"

    study_id: Any = Field(alias="studyId", default=None)
    message: Any = None
    message_type: Any = Field(alias="messageType", default=None)
    time_created: Any = Field(alias="timeCreated", default=None)

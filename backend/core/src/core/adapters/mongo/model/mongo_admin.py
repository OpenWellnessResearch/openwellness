"""Mongo persistence for Admin."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .mongo_base_entity import MongoBaseEntity


class MongoAdmin(MongoBaseEntity):
    """Persistence for Admin."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    collection: ClassVar[str] = "admins"

    name: Any = None
    user: Any = None
    groups: Any = None
    study_ids: Any = Field(alias="studyIds", default=None)
    time_created: Any = Field(alias="timeCreated", default=None)

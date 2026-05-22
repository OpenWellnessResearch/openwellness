"""Mongo persistence for User."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .mongo_base_entity import MongoBaseEntity


class MongoUser(MongoBaseEntity):
    """Persistence for User."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    collection: ClassVar[str] = "users"

    email: Any = None
    is_active: Any = Field(alias="isActive", default=None)
    username: Any = None
    location: Any = None
    roles: Any = None
    time_created: Any = Field(alias="timeCreated", default=None)

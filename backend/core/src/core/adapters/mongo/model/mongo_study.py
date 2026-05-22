"""Mongo persistence for Study."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .mongo_base_entity import MongoBaseEntity


class MongoStudy(MongoBaseEntity):
    """Persistence for Study."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    collection: ClassVar[str] = "studies"

    app_id: Any = Field(alias="appId", default=None)
    name: Any = None
    time_created: Any = Field(alias="timeCreated", default=None)
    description: Any = None
    end_intervention_week: Any = Field(alias="endInterventionWeek", default=None)
    time_updated: Any = Field(alias="timeUpdated", default=None)
    updated_by: Any = Field(alias="updatedBy", default=None)

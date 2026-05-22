"""Mongo persistence for Participant."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .mongo_base_entity import MongoBaseEntity


class MongoParticipant(MongoBaseEntity):
    """Persistence for Participant."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    collection: ClassVar[str] = "participants"

    assigned_coach_id: Any = Field(alias="assignedCoachId", default=None)
    couch_id: Any = Field(alias="couchId", default=None)
    time_created: Any = Field(alias="timeCreated", default=None)
    user_id: Any = Field(alias="userId", default=None)
    study_id: Any = Field(alias="studyId", default=None)
    google_id: Any = Field(alias="googleId", default=None)
    device_id: Any = Field(alias="deviceId", default=None)
    is_active: Any = Field(alias="isActive", default=None)
    participant_number: Any = Field(alias="participantNumber", default=None)
    assessment_weight: Any = Field(alias="assessmentWeight", default=None)
    start_weight: Any = Field(alias="startWeight", default=None)
    height_in_inches: Any = Field(alias="heightInInches", default=None)
    participant_type: Any = Field(alias="participantType", default=None)
    tz: Any = None
    gender: Any = None

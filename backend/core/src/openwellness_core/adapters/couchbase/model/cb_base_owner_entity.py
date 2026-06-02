"""Couchbase persistence base for participant-owned entities."""

from pydantic import Field

from .cb_base_entity import CBBaseEntity


class CBBaseOwnerEntity(CBBaseEntity):
    """Couchbase persistence base for BaseOwnerEntity-derived domain models."""

    owner: str = ""
    study_id: str = Field(alias="studyId", default="")
    created_at: float = Field(alias="createdAt", default=0.0)
    updated_at: float = Field(alias="updatedAt", default=0.0)
    updated_by: str = Field(alias="updatedBy", default="unknown")
    created_at_tz_offset: int = Field(alias="createdAtTzOffset", default=0)
    updated_at_tz_offset: int = Field(alias="updatedAtTzOffset", default=0)

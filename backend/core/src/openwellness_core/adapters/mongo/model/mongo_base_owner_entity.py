"""Mongo persistence base for participant-owned entities.

Provided for symmetry with the domain hierarchy. Currently unused by any
concrete Mongo persistence class — all BaseOwnerEntity-derived entities
in the ported subset persist to Couchbase, not Mongo. Kept so a future
BaseOwnerEntity-backed Mongo collection can subclass this with the audit
field aliases pre-mapped.
"""

from typing import Any

from pydantic import Field

from .mongo_base_entity import MongoBaseEntity


class MongoBaseOwnerEntity(MongoBaseEntity):
    """Mongo persistence base for BaseOwnerEntity-derived domain models."""

    owner: Any = None
    study_id: Any = Field(alias="studyId", default=None)
    created_at: Any = Field(alias="createdAt", default=None)
    updated_at: Any = Field(alias="updatedAt", default=None)
    updated_by: Any = Field(alias="updatedBy", default=None)
    created_at_tz_offset: Any = Field(alias="createdAtTzOffset", default=None)
    updated_at_tz_offset: Any = Field(alias="updatedAtTzOffset", default=None)

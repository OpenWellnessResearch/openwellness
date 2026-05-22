"""Mongo persistence base for all entities.

Each subclass declares its `collection` name as a `ClassVar` class constant,
so the repository can resolve the collection from the persistence type
without touching the domain.

Owns the ObjectId↔str translation at the adapter boundary so the domain
model carries a plain string id.
"""

from typing import Any, ClassVar, Type, TypeVar

from bson import ObjectId
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

E = TypeVar("E")


def _coerce_objectids(value: Any) -> Any:
    """Recursively replace any ObjectId with its string form."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {k: _coerce_objectids(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_coerce_objectids(v) for v in value]
    return value


class MongoBaseEntity(BaseModel):
    """Mongo persistence base for BaseEntity-derived domain models."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
        arbitrary_types_allowed=True,
    )

    collection: ClassVar[str] = ""

    id: str = Field(default="", alias="_id")

    @model_validator(mode="before")
    @classmethod
    def _stringify_objectid_fields(cls, data: Any) -> Any:
        # Reference fields (participant_id, owner, study_id, ...) come back
        # from Mongo as ObjectId; the domain and the API expect plain str.
        return _coerce_objectids(data)

    @field_validator("id", mode="before")
    @classmethod
    def _stringify_objectid(cls, v: Any) -> Any:
        return str(v) if isinstance(v, ObjectId) else v

    @field_serializer("id", when_used="always")
    def _to_objectid(self, v: str) -> ObjectId:
        if not v:
            return ObjectId()
        try:
            return ObjectId(v)
        except Exception:
            # Domain default ids are uuid4 strings; Mongo assigns its own
            # ObjectId on insert and the repository updates entity.id from
            # the result.
            return ObjectId()

    @classmethod
    def from_domain(cls, entity: Any) -> "MongoBaseEntity":
        data = {
            name: getattr(entity, name)
            for name in cls.model_fields
            if hasattr(entity, name)
        }
        return cls(**data)

    def to_domain(self, entity_cls: Type[E]) -> E:
        return entity_cls(**self.model_dump(by_alias=False))

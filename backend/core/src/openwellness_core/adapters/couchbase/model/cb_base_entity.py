"""Couchbase persistence base for all entities.

Owns Couchbase-routing concerns (`type`, `_rev`, `channels`) so the domain
layer stays free of persistence opinions.

Each subclass declares its document `type` as a class constant. The base
class merges that constant into the wire-format dict during `model_dump`.
Archived writes use a separate `type_archived` constant (defaults to
`f"{type}Archived"`).
"""

from typing import Any, ClassVar, Type, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from ....domain.models.base_entity import BaseEntity

E = TypeVar("E", bound=BaseEntity)


class CBBaseEntity(BaseModel):
    """Couchbase persistence base for BaseEntity-derived domain models."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    type: ClassVar[str] = ""
    type_archived: ClassVar[str] = ""

    id: str = ""
    rev: str = Field(alias="_rev", default="")
    channels: list[str] | None = None

    @classmethod
    def _type_for(cls, archived: bool) -> str:
        if archived:
            return cls.type_archived or f"{cls.type}Archived"
        return cls.type

    @classmethod
    def from_domain(cls, entity: Any, archived: bool = False) -> "CBBaseEntity":
        """Build a persistence instance from a domain entity.

        Reads attributes by snake_case name. The Pydantic field `rev`
        corresponds to the entity's dataclass field `_rev`.
        """
        data: dict[str, Any] = {}
        for name in cls.model_fields:
            if name == "rev":
                data[name] = getattr(entity, "_rev", "")
            elif hasattr(entity, name):
                data[name] = getattr(entity, name)
        instance = cls(**data)
        object.__setattr__(instance, "_archived", archived)
        return instance

    def model_dump(self, *args, **kwargs) -> dict[str, Any]:
        """Serialize, with `type` injected from the class constant."""
        data = super().model_dump(*args, **kwargs)
        data["type"] = self._type_for(getattr(self, "_archived", False))
        return data

    def model_post_init(self, __context: Any) -> None:
        # Pydantic's __init__ doesn't run user __setattr__ for non-field
        # attributes; declare here so model_dump can read it safely.
        object.__setattr__(self, "_archived", False)

    def to_domain(self, entity_cls: Type[E]) -> E:
        """Construct a domain entity from this persistence instance."""
        data = super().model_dump(by_alias=False)
        if "rev" in data:
            data["_rev"] = data.pop("rev")
        valid = entity_cls.valid_fields()
        data = {k: v for k, v in data.items() if k in valid}
        return entity_cls(**data)

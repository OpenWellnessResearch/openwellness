"""Universal base for all domain entities."""

from dataclasses import dataclass, field, fields
from typing import Self
from uuid import uuid4


@dataclass
class BaseEntity:
    """Universal base for all domain entities.

    Persistence concerns (`type`, `_rev`, `channels`, collection routing) live
    on the persistence-layer classes in `adapters/`, not here.
    """

    id: str = field(default_factory=lambda: str(uuid4()))

    @classmethod
    def valid_fields(cls) -> set[str]:
        """Return the set of declared field names for this entity."""
        return {f.name for f in fields(cls)}

    @classmethod
    def create(cls, data: dict) -> Self:
        """Construct an entity from a dict of field values."""
        return cls(**data)

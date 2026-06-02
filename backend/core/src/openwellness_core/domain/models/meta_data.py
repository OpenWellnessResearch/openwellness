"""MetaData entity."""

from dataclasses import dataclass

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class MetaData(BaseOwnerEntity):
    """Study-specific metadata for a related document."""

    related_id: str

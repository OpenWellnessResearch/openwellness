"""Asset domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

from .base_owner_entity import BaseOwnerEntity
from .card import Card


@dataclass(kw_only=True)
class Asset(BaseOwnerEntity):
    """An Asset is a resource that is accessible via a URL."""

    MediaType = Card.MediaType
    SomeMediaType = Union[MediaType, int]

    source_changed_at: float
    title: str
    url: str

    category: Optional[int] = None
    description: Optional[str] = None
    kind: Optional[int] = None
    media_type: SomeMediaType = field(default=MediaType.URL)
    placeholder_url: Optional[str] = None
    week: Optional[int] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if isinstance(self.media_type, int):
            self.media_type = Asset.MediaType(self.media_type)

"""Card domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Union

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class Card(BaseOwnerEntity):
    """A Card is a rich preview generated using OpenGraph tags from a URL."""

    class MediaType(IntEnum):
        URL = 0
        IMAGE = 1
        AUDIO = 2
        VIDEO = 3

    SomeMediaType = Union[MediaType, int]

    title: str
    description: str
    url: str

    image: Optional[str] = None
    media_type: SomeMediaType = field(default=MediaType.URL)

    def __post_init__(self) -> None:
        super().__post_init__()
        if isinstance(self.media_type, int):
            self.media_type = self.MediaType(self.media_type)

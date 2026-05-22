"""Couchbase persistence for Card."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBCard(CBBaseOwnerEntity):
    """Persistence for Card."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "Card"

    title: Any = None
    description: Any = None
    url: Any = None
    image: Any = None
    media_type: Any = Field(default=None, alias="mediaType")

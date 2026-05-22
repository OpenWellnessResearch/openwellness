"""Couchbase persistence for Asset."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBAsset(CBBaseOwnerEntity):
    """Persistence for Asset."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "Asset"

    category: Any = None
    description: Any = None
    kind: Any = None
    media_type: Any = Field(default=None, alias="mediaType")
    placeholder_url: Any = Field(default=None, alias="placeholderUrl")
    source_changed_at: Any = Field(default=None, alias="sourceChangedAt")
    title: Any = None
    url: Any = None
    week: Any = None

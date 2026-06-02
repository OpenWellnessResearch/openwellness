"""Couchbase persistence for MetaData."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBMetaData(CBBaseOwnerEntity):
    """Persistence for MetaData."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "MetaData"

    related_id: Any = Field(alias="relatedId", default=None)

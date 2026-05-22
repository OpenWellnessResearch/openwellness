"""Couchbase persistence for Weight."""

from typing import ClassVar

from pydantic import ConfigDict

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBWeight(CBBaseOwnerEntity):
    """Persistence for Weight."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "Weight"

    weight: float | None = None

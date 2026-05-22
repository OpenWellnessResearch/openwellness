"""Couchbase persistence for DailyState."""

from typing import Any, ClassVar

from pydantic import ConfigDict

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBDailyState(CBBaseOwnerEntity):
    """Persistence for DailyState."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "DailyState"

    date: Any = None

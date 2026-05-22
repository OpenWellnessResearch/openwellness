"""Couchbase persistence for SharedGoalProgress."""

from typing import ClassVar

from pydantic import ConfigDict

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBSharedGoalProgress(CBBaseOwnerEntity):
    """Persistence for SharedGoalProgress."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "SharedGoalProgress"

    progress: float = 0.0
    date: str = ""

"""SharedGoalProgress domain model."""

from dataclasses import dataclass, field

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class SharedGoalProgress(BaseOwnerEntity):
    """Progress data shared between multiple users."""

    date: str
    """Date in YYYY-MM-DD format."""

    progress: float = field(default=0.0)

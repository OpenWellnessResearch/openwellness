"""DailyState domain model."""

from dataclasses import dataclass

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class DailyState(BaseOwnerEntity):
    """Per-day participant state, defined per-study. One per participant per day."""

    date: str
    """Date in YYYY-MM-DD format."""

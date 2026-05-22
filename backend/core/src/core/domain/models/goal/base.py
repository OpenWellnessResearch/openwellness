"""Base Goal entity."""

from dataclasses import dataclass

from ..base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class Goal(BaseOwnerEntity):
    """A collection of intended targets starting at a particular time."""

    start_date: float = 0

"""UserStress domain model."""

from dataclasses import dataclass

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class UserStress(BaseOwnerEntity):
    """Perceived stress rating at a point in time."""

    rating: int
    stress_date: str

"""UserFood domain model."""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Union

from .base_owner_entity import BaseOwnerEntity

SomeSourceType = Union[int, "UserFood.SourceType"]


@dataclass(kw_only=True)
class UserFood(BaseOwnerEntity):
    """Self-reported consumption of food and associated nutritional values."""

    class SourceType(IntEnum):
        DATABASE = 0
        CUSTOM = 1
        RECIPE = 2

    food_id: str
    name: str
    amount: float
    source_type: SomeSourceType
    eaten_at: float

    fat: Optional[float] = 0.0
    calories: Optional[float] = 0.0
    serving_name: Optional[str] = None
    serving_id: Optional[str] = None
    cholesterol: Optional[float] = 0.0
    fiber: Optional[float] = 0.0
    protein: Optional[float] = 0.0
    sat_fat: Optional[float] = 0.0
    sodium: Optional[float] = 0.0
    sugars: Optional[float] = 0.0
    total_carbohydrate: Optional[float] = 0.0

    def __post_init__(self) -> None:
        super().__post_init__()
        if isinstance(self.source_type, int):
            self.source_type = self.SourceType(self.source_type)

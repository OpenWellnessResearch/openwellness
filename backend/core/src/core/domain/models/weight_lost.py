"""WeightLost dataclass."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class WeightLost:
    """Weight lost in a week."""

    week: int
    weight: float
    """Negative number indicates weight lost."""

    start_weight_id: Optional[str] = None
    end_weight_id: Optional[str] = None

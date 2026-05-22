"""WeightDelta value object."""

from dataclasses import dataclass


@dataclass
class WeightDelta:
    """Change in weight in a given week."""

    week: int
    delta: float
    earliest_weight_id: str
    latest_weight_id: str

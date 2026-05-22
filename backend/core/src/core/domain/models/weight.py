"""Weight entry domain model."""

from dataclasses import dataclass

import arrow

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class Weight(BaseOwnerEntity):
    """Weight at a point in time (the `created_at` timestamp)."""

    weight: float

    @property
    def year_month_day(self) -> str:
        return arrow.get(self.created_at + self.created_at_tz_offset).format(
            "YYYY-MM-DD"
        )

    def in_pounds(self) -> float:
        return self.weight

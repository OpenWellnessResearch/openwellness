"""FitbitWeight domain model."""

from dataclasses import dataclass

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class FitbitWeight(BaseOwnerEntity):
    """A weight measurement from a Fitbit device."""

    weight: float
    bmi: float
    date: str
    fitbit_date: str
    log_id: int
    source: str
    time: str
    fat: float = 0.0

    def in_pounds(self):
        return float(self.weight) * 2.2046

    @property
    def year_month_day(self) -> str:
        return self.fitbit_date

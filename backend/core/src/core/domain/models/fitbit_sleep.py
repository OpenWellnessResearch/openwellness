"""FitbitSleep domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class FitbitSleep(BaseOwnerEntity):
    """Sleep data from a Fitbit for a single day."""

    fitbit_date: str
    sleep: List[str]

    stages: Dict[str, int] = field(default_factory=dict)
    total_minutes_asleep: int = 0
    total_sleep_records: int = 0
    total_time_in_bed: int = 0

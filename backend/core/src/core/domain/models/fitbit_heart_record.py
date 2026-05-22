"""FitbitHeartRecord domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

from .base_owner_entity import BaseOwnerEntity

# pylint: disable=invalid-name


@dataclass(kw_only=True)
class FitbitHeartRecord(BaseOwnerEntity):
    """One day of Fitbit heart rate time series data."""

    class ZoneName(str, Enum):
        outOfRange = "outOfRange"
        fatBurn = "fatBurn"
        cardio = "cardio"
        peak = "peak"

    class HRZone:
        def __init__(self, data: dict):
            self.caloriesOut: float = data.get("caloriesOut", 0.0)
            self.max: int = data["max"]
            self.min: int = data["min"]
            self.minutes: int = data.get("minutes", 0)
            self.name: str = data["name"]
            self.zoneMinutes: int = data.get(
                "zoneMinutes", self.calculate_zone_minutes(self.minutes)
            )

        @property
        def attribute_name(self):
            if self.name == "Out of Range":
                return FitbitHeartRecord.ZoneName.outOfRange
            elif self.name == "Fat Burn":
                return FitbitHeartRecord.ZoneName.fatBurn
            elif self.name == "Cardio":
                return FitbitHeartRecord.ZoneName.cardio
            elif self.name == "Peak":
                return FitbitHeartRecord.ZoneName.peak

        def calculate_zone_minutes(self, minutes: int) -> int:
            if self.name == "Out of Range":
                return 0
            elif self.name == "Fat Burn":
                return minutes
            elif self.name == "Cardio":
                return minutes * 2
            elif self.name == "Peak":
                return minutes * 2
            else:
                return -1

    fitbit_date: str
    out_of_range: dict
    fat_burn: dict
    cardio: dict
    peak: dict

    custom_heart_rate_zones: List[Dict] = field(default_factory=list)
    resting_heart_rate: int = field(default=0)
    zone_minutes: int = field(default=0)

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name in ("cardio", "fat_burn", "peak") and not all(
            hasattr(self, z) for z in ("cardio", "fat_burn", "peak")
        ):
            return
        if name in ("cardio", "fat_burn", "peak"):
            super().__setattr__("zone_minutes", self.mvpa_minutes)

    def __post_init__(self) -> None:
        super().__post_init__()
        self.zone_minutes = self.mvpa_minutes

    @property
    def cardio_zone(self):
        return self.HRZone(self.cardio)

    @property
    def fat_burn_zone(self) -> HRZone:
        return self.HRZone(self.fat_burn)

    @property
    def peak_zone(self) -> HRZone:
        return self.HRZone(self.peak)

    @property
    def out_of_range_zone(self) -> HRZone:
        return self.HRZone(self.out_of_range)

    @property
    def mvpa_minutes(self):
        return (
            self.cardio_zone.zoneMinutes
            + self.peak_zone.zoneMinutes
            + self.fat_burn_zone.zoneMinutes
        )

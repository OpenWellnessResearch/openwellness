"""Fitbit API sleep summary value objects."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .fitbit_api_sleep_record import FitbitAPISleepRecord

# pylint: disable=invalid-name


@dataclass
class Stages:
    """Sleep stage minute counts."""

    light: int
    deep: int
    rem: int
    wake: int


@dataclass
class FitbitAPISleepSummary:
    """Aggregate sleep summary."""

    totalTimeInBed: int
    stages: Optional[Stages]
    totalMinutesAsleep: int
    totalSleepRecords: int

    @staticmethod
    def from_dict(d: Dict) -> "FitbitAPISleepSummary":
        return FitbitAPISleepSummary(
            totalTimeInBed=d["totalTimeInBed"],
            stages=Stages(**d["stages"]) if "stages" in d else None,
            totalMinutesAsleep=d["totalMinutesAsleep"],
            totalSleepRecords=d["totalSleepRecords"],
        )

    def to_dict(self):
        d: dict[str, Any] = {
            "totalTimeInBed": self.totalTimeInBed,
            "totalMinutesAsleep": self.totalMinutesAsleep,
            "totalSleepRecords": self.totalSleepRecords,
        }
        if self.stages:
            d["stages"] = self.stages.__dict__
        return d


@dataclass
class FitbitAPISleepLog:
    """Sleep log payload from the Fitbit API."""

    summary: FitbitAPISleepSummary
    sleep: List[FitbitAPISleepRecord]

    def to_dict(self):
        return {
            "summary": self.summary.to_dict(),
            "sleep": [record.to_dict() for record in self.sleep],
        }

    @staticmethod
    def from_dict(d: Dict) -> "FitbitAPISleepLog":
        return FitbitAPISleepLog(
            summary=FitbitAPISleepSummary.from_dict(d["summary"]),
            sleep=[FitbitAPISleepRecord(**record) for record in d["sleep"]],
        )

    def __post_init__(self):
        if isinstance(self.sleep, list) and all(
            isinstance(item, dict) for item in self.sleep
        ):
            self.sleep = [
                FitbitAPISleepRecord(**item)
                for item in self.sleep
                if isinstance(item, dict)
            ]
        if isinstance(self.summary, dict):
            self.summary = FitbitAPISleepSummary.from_dict(self.summary)

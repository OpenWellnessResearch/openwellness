"""Fitbit API sleep record value objects."""

from dataclasses import dataclass
from typing import Dict, List

# pylint: disable=invalid-name


@dataclass
class SleepLevelData:
    """Sleep level datum from the Fitbit API."""

    dateTime: str
    level: str
    seconds: int

    def to_dict(self):
        return {
            "dateTime": self.dateTime,
            "level": self.level,
            "seconds": self.seconds,
        }


@dataclass
class SleepSummary:
    """Sleep level summary from the Fitbit API."""

    count: int
    minutes: int
    thirtyDayAvgMinutes: int | None = None

    def to_dict(self):
        d = {
            "count": self.count,
            "minutes": self.minutes,
        }
        if self.thirtyDayAvgMinutes is not None:
            d["thirtyDayAvgMinutes"] = self.thirtyDayAvgMinutes
        return d


@dataclass
class SleepLevels:
    """Sleep levels payload from the Fitbit API."""

    data: List[SleepLevelData] | List[dict]
    summary: Dict[str, SleepSummary] | Dict[str, dict]
    shortData: List[SleepLevelData] | List[dict] | None = None

    def __post_init__(self):
        if isinstance(self.data, list) and all(
            isinstance(item, dict) for item in self.data
        ):
            self.data = [
                SleepLevelData(**item) for item in self.data if isinstance(item, dict)
            ]
        if isinstance(self.shortData, list):
            if all(isinstance(item, dict) for item in self.shortData):
                self.shortData = [
                    SleepLevelData(**item)
                    for item in self.shortData
                    if isinstance(item, dict)
                ]
        if isinstance(self.summary, dict):
            self.summary = {
                k: SleepSummary(**v)
                for k, v in self.summary.items()
                if isinstance(v, dict)
            }

    def to_dict(self):
        d = {
            "data": [
                item.to_dict() for item in self.data if isinstance(item, SleepLevelData)
            ],
            "summary": {
                k: v.to_dict()
                for k, v in self.summary.items()
                if isinstance(v, SleepSummary)
            },
        }
        if self.shortData is not None:
            d["shortData"] = [
                item.to_dict()
                for item in self.shortData
                if isinstance(item, SleepLevelData)
            ]
        return d


@dataclass
class FitbitAPISleepRecord:
    """A single sleep session from the Fitbit API response."""

    dateOfSleep: str
    duration: int
    efficiency: int
    endTime: str
    infoCode: int
    isMainSleep: bool
    levels: SleepLevels | dict
    logId: int
    minutesAfterWakeup: int
    minutesAsleep: int
    minutesAwake: int
    minutesToFallAsleep: int
    startTime: str
    timeInBed: int
    type: str
    logType: str | None = None

    def __post_init__(self):
        if isinstance(self.levels, dict):
            self.levels = SleepLevels(**self.levels)

    def to_dict(self):
        return {
            "dateOfSleep": self.dateOfSleep,
            "duration": self.duration,
            "efficiency": self.efficiency,
            "infoCode": self.infoCode,
            "isMainSleep": self.isMainSleep,
            "levels": (
                self.levels.to_dict()
                if isinstance(self.levels, SleepLevels)
                else self.levels
            ),
            "logId": self.logId,
            "minutesAfterWakeup": self.minutesAfterWakeup,
            "minutesAsleep": self.minutesAsleep,
            "minutesAwake": self.minutesAwake,
            "minutesToFallAsleep": self.minutesToFallAsleep,
            "startTime": self.startTime,
            "timeInBed": self.timeInBed,
            "type": self.type,
        }

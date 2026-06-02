"""Couchbase persistence for Fitbit family entities."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBFitbitRecord(CBBaseOwnerEntity):
    """Persistence for FitbitRecord."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "FitbitRecord"

    active_score: Any = Field(alias="activeScore", default=None)
    activity_calories: Any = Field(alias="activityCalories", default=None)
    calories_bmr: Any = Field(alias="caloriesBMR", default=None)
    calories_out: Any = Field(alias="caloriesOut", default=None)
    distances: Any = None
    fairly_active_minutes: Any = Field(alias="fairlyActiveMinutes", default=None)
    fitbit_date: Any = Field(alias="fitbitDate", default=None)
    lightly_active_minutes: Any = Field(alias="lightlyActiveMinutes", default=None)
    marginal_calories: Any = Field(alias="marginalCalories", default=None)
    sedentary_minutes: Any = Field(alias="sedentaryMinutes", default=None)
    steps: Any = None
    very_active_minutes: Any = Field(alias="veryActiveMinutes", default=None)


class CBFitbitHeartRecord(CBBaseOwnerEntity):
    """Persistence for FitbitHeartRecord."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "FitbitHeartRecord"

    custom_heart_rate_zones: Any = Field(alias="customHeartRateZones", default=None)
    fitbit_date: Any = Field(alias="fitbitDate", default=None)
    resting_heart_rate: Any = Field(alias="restingHeartRate", default=None)
    out_of_range: Any = Field(alias="outOfRange", default=None)
    fat_burn: Any = Field(alias="fatBurn", default=None)
    cardio: Any = None
    peak: Any = None
    zone_minutes: Any = Field(alias="zoneMinutes", default=None)


class CBFitbitSleep(CBBaseOwnerEntity):
    """Persistence for FitbitSleep."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "FitbitSleep"

    fitbit_date: Any = Field(alias="fitbitDate", default=None)
    sleep: Any = None
    stages: Any = None
    total_minutes_asleep: Any = Field(alias="totalMinutesAsleep", default=None)
    total_sleep_records: Any = Field(alias="totalSleepRecords", default=None)
    total_time_in_bed: Any = Field(alias="totalTimeInBed", default=None)


class CBFitbitSleepSession(CBBaseOwnerEntity):
    """Persistence for FitbitSleepSession."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "FitbitSleepSession"

    date_of_sleep: Any = Field(alias="dateOfSleep", default=None)
    duration: Any = None
    efficiency: Any = None
    info_code: Any = Field(alias="infoCode", default=None)
    is_main_sleep: Any = Field(alias="isMainSleep", default=None)
    levels: Any = None
    log_id: Any = Field(alias="logId", default=None)
    minutes_after_wakeup: Any = Field(alias="minutesAfterWakeup", default=None)
    minutes_asleep: Any = Field(alias="minutesAsleep", default=None)
    minutes_awake: Any = Field(alias="minutesAwake", default=None)
    minutes_to_fall_asleep: Any = Field(alias="minutesToFallAsleep", default=None)
    sleep_id: Any = Field(alias="sleepId", default=None)
    sleep_type: Any = Field(alias="sleepType", default=None)
    start_date: Any = Field(alias="startDate", default=None)
    start_time: Any = Field(alias="startTime", default=None)
    time_in_bed: Any = Field(alias="timeInBed", default=None)


class CBFitbitWeight(CBBaseOwnerEntity):
    """Persistence for FitbitWeight."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "FitbitWeight"

    weight: Any = None
    bmi: Any = None
    date: Any = None
    fitbit_date: Any = Field(alias="fitbitDate", default=None)
    log_id: Any = Field(alias="logId", default=None)
    source: Any = None
    time: Any = None
    fat: Any = None

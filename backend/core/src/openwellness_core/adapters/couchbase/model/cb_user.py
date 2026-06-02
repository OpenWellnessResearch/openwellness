"""Couchbase persistence for User-related entities (settings, sleep, stress, food)."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBUserSettings(CBBaseOwnerEntity):
    """Persistence for UserSettings."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "UserSettings"

    wake_time: Any = Field(alias="wakeTime", default=None)
    sleep_time: Any = Field(alias="sleepTime", default=None)
    start_date: Any = Field(alias="startDate", default=None)
    end_study_message: Any = Field(alias="endStudyMessage", default=None)
    should_email_notifications: Any = Field(
        alias="shouldEmailNotifications", default=None
    )
    run_in_start_date: Any = Field(alias="runInStartDate", default=None)


class CBUserSleep(CBBaseOwnerEntity):
    """Persistence for UserSleep."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "UserSleep"

    awake_time: Any = Field(alias="awakeTime", default=None)
    in_bed_time: Any = Field(alias="inBedTime", default=None)
    minutes_awoken: Any = Field(alias="minutesAwoken", default=None)
    minutes_to_sleep: Any = Field(alias="minutesToSleep", default=None)
    out_of_bed_time: Any = Field(alias="outOfBedTime", default=None)
    sleep_date: Any = Field(alias="sleepDate", default=None)
    rating: Any = None
    times_awoken: Any = Field(alias="timesAwoken", default=None)


class CBUserStress(CBBaseOwnerEntity):
    """Persistence for UserStress."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "UserStress"

    rating: Any = None
    stress_date: Any = Field(alias="stressDate", default=None)


class CBUserFood(CBBaseOwnerEntity):
    """Persistence for UserFood."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "UserFood"

    food_id: Any = Field(alias="foodId", default=None)
    name: Any = None
    amount: Any = None
    source_type: Any = Field(alias="sourceType", default=None)
    eaten_at: Any = Field(alias="eatenAt", default=None)
    fat: Any = None
    calories: Any = None
    serving_name: Any = Field(alias="servingName", default=None)
    serving_id: Any = Field(alias="servingID", default=None)
    cholesterol: Any = None
    fiber: Any = None
    protein: Any = None
    sat_fat: Any = Field(alias="satFat", default=None)
    sodium: Any = None
    sugars: Any = None
    total_carbohydrate: Any = Field(alias="totalCarbohydrate", default=None)

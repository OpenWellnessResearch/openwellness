"""Couchbase persistence for Goal family."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBGoal(CBBaseOwnerEntity):
    """Persistence for Goal."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "Goal"

    start_date: Any = Field(alias="startDate", default=None)


class CBDailyGoal(CBGoal):
    """Persistence for DailyGoal."""

    kind: Any = None


class CBWeeklyGoal(CBGoal):
    """Persistence for WeeklyGoal."""

    kind: Any = None


class CBLegacyGoal(CBGoal):
    """Persistence for LegacyGoal."""

    activity: Any = None
    calories: Any = None
    fat: Any = None
    steps: Any = None
    weight: Any = None

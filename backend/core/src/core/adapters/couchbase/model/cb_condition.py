"""Couchbase persistence for Condition family."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBCondition(CBBaseOwnerEntity):
    """Persistence for Condition."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "Condition"

    app_group: Any = Field(alias="appGroup", default=None)
    app_group_note: Any = Field(alias="appGroupNote", default=None)
    week: Any = None


class CBWeightCondition(CBCondition):
    """Persistence for WeightCondition."""

    weight_goal_level: Any = Field(alias="weightGoalLevel", default=None)
    weight_loss_protocol: Any = Field(alias="weightLossProtocol", default=None)
    weight_start_id: Any = Field(alias="weightStartId", default=None)
    weight_end_id: Any = Field(alias="weightEndId", default=None)


class CBLegacyCondition(CBWeightCondition):
    """Persistence for LegacyCondition."""

    was_inactive: Any = Field(alias="wasInactive", default=None)

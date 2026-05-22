"""Couchbase persistence for StudySettings."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBStudySettings(CBBaseOwnerEntity):
    """Persistence for StudySettings."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "StudySettings"

    goals: Any = None
    fitbit_activity: Any = Field(alias="fitbitActivity", default=None)
    principal_investigator: Any = Field(alias="principalInvestigator", default=None)

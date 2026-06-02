"""StudySettings domain model."""

from dataclasses import dataclass, field

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class StudySettings(BaseOwnerEntity):
    """Per-study configuration."""

    goals: list[int] = field(default_factory=list)
    fitbit_activity: bool = field(default=True)
    principal_investigator: str | None = field(default=None)

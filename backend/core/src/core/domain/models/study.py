"""Study entity."""

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity


@dataclass(kw_only=True)
class Study(BaseEntity):
    """A research study."""

    app_id: str
    name: str
    time_created: datetime

    description: str | None = None
    end_intervention_week: int = 99999
    time_updated: datetime = field(default_factory=datetime.now)
    updated_by: str | None = None

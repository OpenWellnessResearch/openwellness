"""Base for participant-owned entities with audit metadata."""

import time
from dataclasses import dataclass, field

from .base_entity import BaseEntity


def _local_tz_offset() -> int:
    """Current local timezone offset in seconds east of UTC."""
    return -(time.altzone if time.localtime().tm_isdst else time.timezone)


@dataclass
class BaseOwnerEntity(BaseEntity):
    """Base for entities owned by a participant within a study.

    Adds ownership and audit metadata. Timezone offsets are domain audit
    metadata (the participant's local TZ at the time of each event) and stay
    on the domain — they are not persistence routing.
    """

    owner: str = ""
    study_id: str = ""
    updated_by: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    created_at_tz_offset: int = field(default_factory=_local_tz_offset)
    updated_at_tz_offset: int = field(default_factory=_local_tz_offset)

    def __post_init__(self) -> None:
        if not self.updated_by:
            self.updated_by = self.owner

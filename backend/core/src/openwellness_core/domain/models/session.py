"""Session domain model."""

from dataclasses import dataclass, field
from typing import List, Optional

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class Session(BaseOwnerEntity):
    """A time period concerning significant usage."""

    views: List[dict] = field(default_factory=list)
    session_type: Optional[int] = None
    time_start_in_ms: float = 0.0
    duration_in_ms: float = 0.0

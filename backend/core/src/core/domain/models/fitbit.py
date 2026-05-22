"""Connected Fitbit account."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .base_entity import BaseEntity


@dataclass(kw_only=True)
class Fitbit(BaseEntity):
    """A connected Fitbit account."""

    participant_id: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    owner_id: Optional[str] = None
    subscription_id: Optional[str] = None
    time_created: datetime = field(default_factory=datetime.now)

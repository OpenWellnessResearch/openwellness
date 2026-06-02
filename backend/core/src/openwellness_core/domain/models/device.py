"""Device entity."""

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity


@dataclass(kw_only=True)
class Device(BaseEntity):
    """A device in the system."""

    serial_number: str
    platform: str = field(default="unknown")
    participant_id: str | None = None
    time_created: datetime = field(default_factory=datetime.now)
    is_standard_time: bool | None = None

    @property
    def can_receive_notifications(self) -> bool:
        return self.platform.lower() in ["ios", "android"]

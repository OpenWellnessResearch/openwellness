"""User entity."""

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity


@dataclass(kw_only=True)
class User(BaseEntity):
    """A unique account recognized by the system."""

    email: str
    is_active: bool
    username: str

    location: str | None = None
    roles: dict = field(default_factory=dict)
    time_created: datetime = field(default_factory=datetime.now)

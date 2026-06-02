"""Admin entity and AdminUser dataclass."""

from dataclasses import dataclass, field
from datetime import datetime

from .base_entity import BaseEntity


@dataclass
class AdminUser:
    """Abbreviated user stored in an Admin object."""

    id: str
    name: str = ""
    location: str = ""


@dataclass(kw_only=True)
class Admin(BaseEntity):
    """An admin manages participants."""

    name: dict
    user: AdminUser = field(default_factory=lambda: AdminUser("", "", ""))
    groups: dict = field(default_factory=dict)
    study_ids: list = field(default_factory=list)
    time_created: datetime = field(default_factory=datetime.now)

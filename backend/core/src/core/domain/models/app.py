"""App entity."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .base_entity import BaseEntity


@dataclass(kw_only=True)
class App(BaseEntity):
    """An instance of a mobile app and its configuration."""

    name: str
    time_created: datetime = field(default_factory=datetime.now)

    android_package_name: Optional[str] = None
    app_store_id: Optional[str] = None
    ios_bundle_id: Optional[str] = None
    one_signal_app_id: Optional[str] = None

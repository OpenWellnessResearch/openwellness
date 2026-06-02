"""SyncUser dataclass."""

from dataclasses import dataclass, field


@dataclass(kw_only=True)
class SyncUser:
    """User in the Sync Gateway."""

    name: str
    admin_channels: list[str] = field(default_factory=list)
    all_channels: list[str] = field(default_factory=list)
    sequence: int = field(default=1)

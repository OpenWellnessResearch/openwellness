"""Record of activity for a resource."""

from dataclasses import dataclass

from arrow import Arrow


@dataclass
class ActivityRecord:
    """Record of activity for a resource."""

    source_id: str
    source_name: str
    date: Arrow
    mvpa_minutes: int

"""StudyMessage entity."""

from dataclasses import dataclass
from datetime import datetime

from .base_entity import BaseEntity


@dataclass(kw_only=True)
class StudyMessage(BaseEntity):
    """Content of a push notification associated with a study."""

    study_id: str
    message: str
    message_type: int
    time_created: datetime

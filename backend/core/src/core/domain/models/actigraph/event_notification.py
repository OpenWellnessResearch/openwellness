"""EventNotification from Actigraph."""

from __future__ import annotations

from dataclasses import dataclass

import arrow
from arrow import Arrow


@dataclass
class EventNotification:
    """A notification sent by Actigraph."""

    status: str
    upload_id: str
    study_id: str
    subject_id: str
    start: Arrow
    end: Arrow

    @staticmethod
    def from_dict(d: dict) -> EventNotification:
        return EventNotification(
            status=d["status"],
            upload_id=d["uploadId"],
            study_id=d["studyId"],
            subject_id=d["subjectId"],
            start=arrow.get(d["start"]),
            end=arrow.get(d["end"]),
        )

    @property
    def start_date(self) -> str:
        return self.start.format("YYYY-MM-DDTHH:mm:ss") + "Z"

    @property
    def end_date(self) -> str:
        return self.end.format("YYYY-MM-DDTHH:mm:ss") + "Z"

    @property
    def is_more_than_7_days(self) -> bool:
        return (self.end - self.start).days >= 7

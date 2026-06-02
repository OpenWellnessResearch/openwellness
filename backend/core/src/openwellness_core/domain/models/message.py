"""Message entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Union

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class Message(BaseOwnerEntity):
    """A push notification that was sent to a participant."""

    class ReadState(IntEnum):
        SENT = 0
        READ = 1
        DELETED = 2

    SomeReadState = Union[ReadState, int]

    class LikeState(IntEnum):
        UNKNOWN = 0
        LIKE = 1
        DISLIKE = 2

    SomeLikeState = Union[LikeState, int]

    body: str

    like_state: SomeLikeState = field(default=LikeState.UNKNOWN)
    read_state: SomeReadState = field(default=ReadState.SENT)
    opened_at: float | None = field(default=None)
    message_id: str | None = field(default=None)
    delivery_date: float | None = field(default=None)
    subtype: int | None = field(default=None)
    condition: int | None = field(default=None)
    tz_offset: int | None = field(default=None)
    url: str | None = field(default=None)

    def __post_init__(self) -> None:
        super().__post_init__()
        if isinstance(self.like_state, int):
            self.like_state = self.LikeState(self.like_state)
        if isinstance(self.read_state, int):
            self.read_state = self.ReadState(self.read_state)

    def replace_xyz(self, x: str = "", y: str = "", z: str = "") -> None:
        body = self.body
        body = body.replace("[X]", f"{x}")
        body = body.replace("[Y]", f"{y}")
        body = body.replace("[Z]", f"{z}")
        self.body = body

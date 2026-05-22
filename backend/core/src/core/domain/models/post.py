"""Post entity."""

from dataclasses import dataclass, field

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class Post(BaseOwnerEntity):
    """A message shared among 2 or more users."""

    attachments: list[str]
    conversation_id: str
    content: str

    card: str | None = field(default=None)
    in_reply_to_id: str | None = field(default=None)
    replies_count: int = 0

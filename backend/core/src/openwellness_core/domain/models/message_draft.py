"""MessageDraft entity."""

from dataclasses import dataclass, field

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class MessageDraft(BaseOwnerEntity):
    """Basis of a push notification; `content` can be customized before sending."""

    content: str
    delivery_type: int
    destination: int
    subtype: int

    url: str | None = field(default=None)
    content2: str | None = field(default=None)
    day: int | None = field(default=None)
    week: int | None = field(default=None)

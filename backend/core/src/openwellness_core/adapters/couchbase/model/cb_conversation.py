"""Couchbase persistence for Conversation, Message, MessageDraft."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBConversation(CBBaseOwnerEntity):
    """Persistence for Conversation."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "Conversation"

    kind: Any = None
    title: Any = None


class CBMessage(CBBaseOwnerEntity):
    """Persistence for Message."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "Message"

    body: Any = None
    like_state: Any = Field(alias="likeState", default=None)
    read_state: Any = Field(alias="readState", default=None)
    opened_at: Any = Field(alias="openedAt", default=None)
    message_id: Any = Field(alias="messageId", default=None)
    delivery_date: Any = Field(alias="deliveryDate", default=None)
    subtype: Any = None
    condition: Any = None
    tz_offset: Any = Field(alias="tzOffset", default=None)
    url: Any = None


class CBMessageDraft(CBBaseOwnerEntity):
    """Persistence for MessageDraft."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "MessageDraft"

    content: Any = None
    delivery_type: Any = Field(alias="deliveryType", default=None)
    destination: Any = None
    subtype: Any = None
    url: Any = None
    content2: Any = None
    day: Any = None
    week: Any = None

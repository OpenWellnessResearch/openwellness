"""Couchbase persistence for Post."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBPost(CBBaseOwnerEntity):
    """Persistence for Post."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "Post"

    attachments: Any = None
    conversation_id: Any = Field(alias="conversationId", default=None)
    card: Any = None
    content: Any = None
    in_reply_to_id: Any = Field(alias="inReplyToId", default=None)
    replies_count: Any = Field(alias="repliesCount", default=None)

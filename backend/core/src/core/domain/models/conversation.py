"""Conversation domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .base_owner_entity import BaseOwnerEntity

# pylint: disable=redefined-builtin


@dataclass(kw_only=True)
class Conversation(BaseOwnerEntity):
    """A Conversation is a collection of shared Posts."""

    class Filter:
        """A way to narrow down a set of Conversations."""

        class Type(Enum):
            CHANNELS = auto()
            KIND = auto()
            WEEK = auto()

            def __str__(self) -> str:
                if self == Conversation.Filter.Type.CHANNELS:
                    return "channels"
                elif self == Conversation.Filter.Type.KIND:
                    return "kind"
                elif self == Conversation.Filter.Type.WEEK:
                    return "week"
                else:
                    return "unknown"

        def __init__(self, type: Type, val: Any) -> None:
            self.type = type
            self.val = val

        def to_n1ql(self, idx: int) -> tuple[str, dict[str, Any]]:
            """Return a parameterized clause + params for this filter.

            ``idx`` is appended to the parameter names so a query that
            stacks several filters of the same type doesn't collide.
            """
            if self.type == Conversation.Filter.Type.CHANNELS:
                key = f"channels_{idx}"
                clause = f"ANY c IN channels SATISFIES c IN ${key} END"
                return clause, {key: list(self.val)}
            if self.type == Conversation.Filter.Type.KIND:
                key = f"kind_{idx}"
                return f"kind = ${key}", {key: int(self.val)}
            if self.type == Conversation.Filter.Type.WEEK:
                key = f"week_{idx}"
                return f"week = ${key}", {key: int(self.val)}
            return "", {}

    kind: int
    title: str | None = field(default=None)

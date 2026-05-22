"""Classification of a Goal."""

from __future__ import annotations

from enum import IntEnum
from typing import Union


class Kind(IntEnum):
    WEEKLY = 0
    DAILY = 1


SomeKind = Union[Kind, int]
SomeKindArg = Union[SomeKind, list[Kind], list[int]]

"""Shared type variables used by generic value objects."""

from typing import Any, Protocol, TypeVar

from arrow import Arrow

SomeDateType = TypeVar("SomeDateType", int, float, str, Arrow)


class Comparable(Protocol):
    """Protocol for types supporting ordering comparisons."""

    def __lt__(self, value: Any, /) -> bool: ...
    def __le__(self, value: Any, /) -> bool: ...
    def __gt__(self, value: Any, /) -> bool: ...
    def __ge__(self, value: Any, /) -> bool: ...


SomeComparableType = TypeVar("SomeComparableType", bound=Comparable)

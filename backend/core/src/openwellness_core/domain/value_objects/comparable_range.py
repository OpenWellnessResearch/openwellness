"""Generic comparable range type."""

from dataclasses import dataclass
from typing import Generic

from ..exceptions.domain_exception import DomainException
from ._type_vars import SomeComparableType


@dataclass
class ComparableRange(Generic[SomeComparableType]):
    """Range of comparable values."""

    start: SomeComparableType
    end: SomeComparableType

    def __post_init__(self):
        if self.start > self.end:
            raise DomainException(
                f"Start {self.start} must be less than or equal to end {self.end}."
            )

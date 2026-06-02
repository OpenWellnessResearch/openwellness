"""Date range value object."""

from dataclasses import dataclass
from typing import Generic

from ..exceptions.domain_exception import DomainException
from ._type_vars import SomeDateType


@dataclass
class DateRange(Generic[SomeDateType]):
    """Range of dates."""

    start_date: SomeDateType
    end_date: SomeDateType

    def __post_init__(self):
        if self.start_date > self.end_date:
            raise DomainException(
                f"Start {self.start_date} must be less than or equal to end {self.end_date}."
            )

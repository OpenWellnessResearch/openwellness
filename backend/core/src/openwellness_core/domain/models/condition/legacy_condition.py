"""LegacyCondition for legacy studies."""

from dataclasses import dataclass, field

from .weight_condition import WeightCondition


@dataclass(kw_only=True)
class LegacyCondition(WeightCondition):
    """A Condition document for a participant in a legacy study."""

    was_inactive: bool = field(default=False)

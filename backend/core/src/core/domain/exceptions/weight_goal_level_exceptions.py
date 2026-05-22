"""Exceptions for weight goal levels."""

from ..value_objects.weight_goal_level import WeightGoalLevel
from .domain_exception import DomainException


class WeightGoalLevelException(DomainException):
    """Base for all weight-goal-level exceptions."""


class UnhandledWeightGoalLevelException(WeightGoalLevelException):
    """Raised when a weight goal level is not handled."""

    level: WeightGoalLevel


class InvalidGoalWeightException(WeightGoalLevelException):
    """Raised when a goal weight is invalid."""

    goal_weight: float

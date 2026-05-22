"""Exceptions related to goal operations."""

from .domain_exception import DomainException


class GoalException(DomainException):
    """Base for all goal-related exceptions."""


class GoalNotFoundException(GoalException):
    """Raised when a goal entry cannot be found."""


class InvalidGoalTimezoneException(GoalException):
    """Raised when a goal entry has an invalid timezone."""

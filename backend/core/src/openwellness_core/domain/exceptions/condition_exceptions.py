"""Exceptions related to condition operations."""

from .domain_exception import DomainException


class ConditionException(DomainException):
    """Base for all condition-related exceptions."""


class ConditionNotFoundException(ConditionException):
    """Raised when a condition entry cannot be found."""

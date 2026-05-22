"""Exceptions related to aggregate weight operations."""

from .domain_exception import DomainException


class AggregateWeightException(DomainException):
    """Base for all aggregate-weight-related exceptions."""


class AggregateWeightNotFoundException(AggregateWeightException):
    """Raised when an aggregate weight entry cannot be found."""

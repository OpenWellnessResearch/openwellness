"""Exceptions related to weight operations."""

from .domain_exception import DomainException


class WeightException(DomainException):
    """Base for all weight-related exceptions."""


class WeightNotFoundException(WeightException):
    """Raised when a weight entry cannot be found."""

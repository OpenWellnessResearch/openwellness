"""Exceptions related to survey result operations."""

from .domain_exception import DomainException


class SurveyResultException(DomainException):
    """Base class for exceptions in the survey result module."""


class SurveyResultNotFoundException(SurveyResultException):
    """Raised when a survey result cannot be found."""

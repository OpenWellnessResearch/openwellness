"""Exceptions related to JobRule operations."""

from .domain_exception import DomainException


class JobRuleException(DomainException):
    """Base for all JobRule-related exceptions."""


class AppGroupNoneException(JobRuleException):
    """Raised when an app group reference is None."""

    def __init__(self, message: str = "App group is None"):
        super().__init__(message=message)


class NoRelatedSubtypesException(JobRuleException):
    """Raised when no related subtypes are found."""


class JobRuleNotFoundException(JobRuleException):
    """Raised when a job rule cannot be found."""


class UnknownJobRuleProcessorException(JobRuleException):
    """Raised when no processor is registered for a job rule."""

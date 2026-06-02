"""Exceptions related to message draft operations."""

from .domain_exception import DomainException


class MessageDraftException(DomainException):
    """Base for all message-draft-related exceptions."""


class MessageDraftNotFoundException(MessageDraftException):
    """Raised when a message draft entry cannot be found."""

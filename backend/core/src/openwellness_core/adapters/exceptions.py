"""Adapter-layer exceptions."""

from ..application.exceptions import (
    DuplicateEntityException,
    LimitExceededException,
)

__all__ = [
    "AdapterException",
    "DuplicateEntityException",
    "LimitExceededException",
]


class AdapterException(Exception):
    """Base class for adapter-layer exceptions."""

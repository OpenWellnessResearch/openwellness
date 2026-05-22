"""Adapter-layer exceptions."""

from ..application.exceptions import LimitExceededException

__all__ = ["AdapterException", "LimitExceededException"]


class AdapterException(Exception):
    """Base class for adapter-layer exceptions."""

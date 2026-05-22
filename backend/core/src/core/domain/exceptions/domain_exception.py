"""Base class for domain-layer exceptions."""

from dataclasses import dataclass


@dataclass
class DomainException(Exception):
    """Base class for domain-layer exceptions."""

    message: str

    def __repr__(self) -> str:
        return self.message


@dataclass
class EntityNotFoundException(DomainException):
    """Raised when an entity is not found."""


class Unhandled(DomainException):
    """Unhandled case."""


class UnexpectedCount(DomainException):
    """Actual number of results does not equal expected number."""

    def __init__(
        self,
        *args: object,
        expected: int,
        actual: int,
        results: list | None = None,
    ) -> None:
        self.expected = expected
        self.actual = actual
        self.results = results
        super().__init__(*args)

    def __str__(self) -> str:
        return f"Expected: {self.expected}, Actual: {self.actual}"


class NotFound(DomainException):
    """Result(s) not found."""


class MaxAttemptsReached(DomainException):
    """Maximum number of attempts reached."""

    def __init__(self, *args: object, max_attempt: int) -> None:
        self.max_attempt = max_attempt
        super().__init__(*args)

    def __str__(self) -> str:
        return f"Maximum number of attempts reached: {self.max_attempt}"

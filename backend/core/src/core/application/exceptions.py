"""Application-layer exceptions raised across adapter boundaries.

These exceptions are signals the API surface needs to map to HTTP responses
(e.g. ``LimitExceededException`` → 429). They live in ``application`` rather
than ``adapters`` so the API can depend on them without reaching into a
backend-specific module.
"""


class LimitExceededException(Exception):
    """Raised when a rate or quota limit is exceeded."""

    def __init__(
        self,
        message: str = "Limit exceeded",
        start: str = "",
        end: str = "",
        retry_after_secs: int = 3600,
    ):
        super().__init__(message)
        self.start = start
        self.end = end
        self.retry_after_secs = retry_after_secs

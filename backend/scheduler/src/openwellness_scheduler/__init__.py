"""OpenWellness scheduler — Celery workers (and beat) over the shared core.

The ``celery -A openwellness_scheduler`` entrypoint resolves the
``celery_app`` exported here.
"""

from .infrastructure.celery_app import celery_app

__all__ = ["celery_app"]

"""Celery application factory and DI bootstrap.

This is the outermost ring: it owns the Celery instance, the broker/result
configuration, and the one :class:`SchedulerContainer` instance the worker
process resolves dependencies from. Nothing inner imports this module — the
dependency arrow points outward only.

The container is exposed through :func:`get_container` so task adapters (and
tests) resolve interactors against the *live* instance, which is what makes
``container.repositories.<name>.override(...)`` visible to running tasks —
the same dynamic-resolution approach the API uses for its routes.
"""

from __future__ import annotations

import logging

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
from dependency_injector import providers

from ..config import AppConfig, CelerySettings
from ..container import SchedulerContainer

logger = logging.getLogger(__name__)

# Task modules whose ``@inject``-free adapters resolve via ``get_container``.
TASK_MODULES = ["openwellness_scheduler.infrastructure.tasks"]

_container: SchedulerContainer | None = None


def build_container() -> SchedulerContainer:
    """Construct the container and bind the concrete ``AppConfig``."""
    container = SchedulerContainer()
    container.app_config.override(providers.Object(AppConfig()))
    return container


def get_container() -> SchedulerContainer:
    """Return the process-wide container, building it on first use."""
    global _container
    if _container is None:
        _container = build_container()
    return _container


def set_container(container: SchedulerContainer) -> None:
    """Swap the process-wide container (used by tests to inject fakes)."""
    global _container
    _container = container


def create_celery_app() -> Celery:
    """Build the configured Celery app and register task modules."""
    settings = CelerySettings()
    app = Celery("openwellness_scheduler")
    app.conf.update(
        broker_url=settings.broker_url,
        result_backend=settings.result_backend,
        task_default_queue=settings.task_default_queue,
        timezone=settings.timezone,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        # Example beat entry — uncomment and set a real study id to run the
        # sample task on a schedule:
        # beat_schedule={
        #     "count-study-participants-hourly": {
        #         "task": "openwellness.count_study_participants",
        #         "schedule": 3600.0,
        #         "args": ("<study-object-id>",),
        #     },
        # },
    )
    app.autodiscover_tasks(["openwellness_scheduler.infrastructure"])
    # Import for side-effect: registers the ``@shared_task``-decorated tasks.
    from . import tasks  # noqa: F401

    return app


@worker_process_init.connect
def _init_worker(**_kwargs: object) -> None:
    """Open the Couchbase connection once per worker process."""
    try:
        get_container().repositories.entity_repository().initialize()
    except Exception:  # pragma: no cover - broker/db may be absent in dev
        logger.exception("Couchbase initialize() failed; continuing")


@worker_process_shutdown.connect
def _shutdown_worker(**_kwargs: object) -> None:
    """Close the Couchbase connection when the worker process exits."""
    try:
        get_container().repositories.entity_repository().cleanup()
    except Exception:  # pragma: no cover - shutdown best-effort
        logger.exception("Couchbase cleanup() failed")


celery_app = create_celery_app()

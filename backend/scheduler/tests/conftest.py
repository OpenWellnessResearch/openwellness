"""Shared fakes for scheduler tests.

The interactor depends only on the ``ParticipantRepository`` port, so an
in-memory implementation is enough to exercise it end-to-end without
Couchbase, Mongo, Celery, or a broker.
"""

from __future__ import annotations

import os
from typing import Any

# Keep config construction deterministic before anything imports it.
os.environ.setdefault("COUCHBASE_URL", "couchbase://stub")
os.environ.setdefault("MONGO_URL", "mongodb://stub")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

import pytest

from openwellness_core.application.repositories import ParticipantRepository


class FakeParticipantRepo(ParticipantRepository):  # type: ignore[misc]
    """Minimal in-memory ``ParticipantRepository`` for the use-case tests."""

    def __init__(self) -> None:
        self._by_study: dict[str, list[Any]] = {}

    def add(self, study_id: str, participant: Any) -> None:
        self._by_study.setdefault(study_id, []).append(participant)

    def get_by_study_id(self, study_id: str) -> list[Any]:
        return list(self._by_study.get(study_id, []))

    # --- unused port methods (not exercised by the sample task) ---
    def get_by_num_study_id(self, num: str, study_id: str) -> Any | None:
        raise NotImplementedError

    def create(self, entity: Any) -> Any:
        raise NotImplementedError

    def execute_query(self, query: Any) -> Any:
        raise NotImplementedError

    def get_by_id(self, entity_id: str) -> Any | None:
        raise NotImplementedError

    def get_by_query(self, query: Any) -> list[Any]:
        raise NotImplementedError

    def list_all(self) -> list[Any]:
        raise NotImplementedError

    def save(self, entity: Any) -> Any:
        raise NotImplementedError

    def delete(self, entity_id: str) -> Any | None:
        raise NotImplementedError

    def archive(self, entity_id: str) -> None:
        raise NotImplementedError

    def unarchive(self, entity_id: str) -> None:
        raise NotImplementedError


@pytest.fixture
def fake_participants() -> FakeParticipantRepo:
    return FakeParticipantRepo()

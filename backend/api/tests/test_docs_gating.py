"""D-09: /docs, /redoc and /openapi.json are off unless API_ENABLE_DOCS is on.

Every default-reading ``APISettings`` is built with ``_env_file=None`` and the
variable set or cleared through ``monkeypatch``, so a developer's ``.env`` or
shell cannot change the result.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openwellness_api.config import APISettings
from openwellness_api.main import create_app

DOC_PATHS = ("/docs", "/redoc", "/openapi.json")


def test_docs_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_ENABLE_DOCS", raising=False)
    settings = APISettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.enable_docs is False
    client = TestClient(create_app(lifespan=None, settings=settings))
    assert [p for p in DOC_PATHS if client.get(p).status_code != 404] == []


def test_docs_on_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    client = TestClient(create_app(lifespan=None, settings=APISettings(enable_docs=True)))
    assert client.get("/openapi.json").status_code == 200
    monkeypatch.setenv("API_ENABLE_DOCS", "1")
    assert APISettings(_env_file=None).enable_docs is True  # type: ignore[call-arg]

"""Env-file resolution, precedence (env > .env > default) and config inheritance."""

from __future__ import annotations

from pathlib import Path

import pytest

from openwellness_core.infrastructure.config.settings import (
    ENV_FILE_VAR,
    MongoSettings,
    OpenWellnessSettings,
    PostgresSettings,
    resolve_env_file,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_repo_root_contains_compose_marker() -> None:
    assert (REPO_ROOT / "docker-compose.yml").is_file()


def test_resolve_env_file_defaults_to_repo_root_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ENV_FILE_VAR)
    assert resolve_env_file() == REPO_ROOT / ".env"


def test_resolve_env_file_is_cwd_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(ENV_FILE_VAR)
    monkeypatch.chdir(tmp_path)
    assert resolve_env_file() == REPO_ROOT / ".env"


def test_resolve_env_file_honours_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "custom.env"
    monkeypatch.setenv(ENV_FILE_VAR, str(target))
    assert resolve_env_file() == target


def test_env_file_value_beats_default(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("MONGO_DB=from-file\n")
    assert MongoSettings(_env_file=env_file).db == "from-file"


def test_environment_beats_env_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("MONGO_DB=from-file\n")
    monkeypatch.setenv("MONGO_DB", "from-env")
    assert MongoSettings(_env_file=env_file).db == "from-env"


def test_default_applies_without_file_or_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("MONGO_DB", raising=False)
    assert MongoSettings(_env_file=tmp_path / "absent.env").db == "openwellness"


def test_subclass_merges_base_model_config() -> None:
    assert MongoSettings.model_config["env_prefix"] == "MONGO_"
    assert (
        MongoSettings.model_config["env_file"]
        == OpenWellnessSettings.model_config["env_file"]
    )


def test_postgres_url_defaults_to_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    assert PostgresSettings(_env_file=None).url == ""

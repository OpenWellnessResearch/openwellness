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


def _mongo(env_file: Path | None) -> MongoSettings:
    # pyright does not see pydantic-settings' init-time ``_env_file`` kwarg.
    return MongoSettings(_env_file=env_file)  # type: ignore[call-arg]


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
    assert _mongo(env_file).db == "from-file"


def test_environment_beats_env_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("MONGO_DB=from-file\n")
    monkeypatch.setenv("MONGO_DB", "from-env")
    assert _mongo(env_file).db == "from-env"


def test_default_applies_without_file_or_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("MONGO_DB", raising=False)
    assert _mongo(tmp_path / "absent.env").db == "openwellness"


def test_subclass_merges_base_model_config() -> None:
    config = dict(MongoSettings.model_config)
    assert config["env_prefix"] == "MONGO_"
    assert config["env_file"] == dict(OpenWellnessSettings.model_config)["env_file"]


def test_postgres_url_defaults_to_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTGRES_URL", raising=False)
    settings = PostgresSettings(_env_file=None)  # type: ignore[call-arg]
    assert settings.url == ""


def test_app_settings_read_from_env_file(tmp_path: Path) -> None:
    from openwellness_core.infrastructure.config.settings import AppSettings

    env = tmp_path / ".env"
    env.write_text("APP_STORE_ID=123\nAPP_IOS_BUNDLE_ID=edu.x\n")
    cfg = AppSettings(_env_file=env)  # type: ignore[call-arg]
    assert (cfg.store_id, cfg.ios_bundle_id, cfg.one_signal_app_id) == (
        "123",
        "edu.x",
        None,
    )


def test_create_app_stamps_settings_values() -> None:
    from typing import Any, cast

    from openwellness_core.adapters.mongo.repositories.mongo_app_repository import (
        MongoAppRepository,
    )
    from openwellness_core.infrastructure.config.settings import AppSettings

    class _Repo(MongoAppRepository):
        def create(self, entity: Any) -> Any:  # no datastore needed
            return entity

    cfg = AppSettings(store_id="42")
    repo = _Repo(cast(Any, None), app_settings=cfg)
    assert repo.create_app("a").app_store_id == "42"
    assert repo.create_app("a", False).app_store_id is None

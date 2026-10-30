"""End-to-end: services load the env file named by OPENWELLNESS_ENV_FILE.

A subprocess is needed because ``env_file`` is resolved when the settings
class is defined, i.e. at import time.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _run(code: str, cwd: Path, env_file: Path, drop: tuple[str, ...]) -> str:
    env = {k: v for k, v in os.environ.items() if k not in drop}
    env["OPENWELLNESS_ENV_FILE"] = str(env_file)
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_api_app_config_loads_env_file_from_backend_dir(tmp_path: Path) -> None:
    env_file = tmp_path / "test.env"
    env_file.write_text("MONGO_DB=from-env-file\nCOUCHBASE_BUCKET_NAME=bucket-from-file\n")
    out = _run(
        "from openwellness_api.config import AppConfig\n"
        "c = AppConfig()\n"
        "print(c.mongo.db, c.couchbase.bucket_name)",
        BACKEND_DIR,
        env_file,
        ("MONGO_DB", "COUCHBASE_BUCKET_NAME"),
    )
    assert out.split() == ["from-env-file", "bucket-from-file"]


def test_scheduler_and_api_share_one_app_config(tmp_path: Path) -> None:
    # Subprocess: importing the scheduler package in the api test process trips
    # dependency-injector once the api container classes are already loaded.
    out = _run(
        "from openwellness_api.config import AppConfig as A\n"
        "from openwellness_scheduler.config import AppConfig as S\n"
        "print(A is S)",
        BACKEND_DIR,
        tmp_path / "absent.env",
        (),
    )
    assert out.strip() == "True"


def test_scheduler_celery_settings_load_env_file_from_scheduler_dir(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / "test.env"
    env_file.write_text("CELERY_BROKER_URL=memory://from-file\n")
    out = _run(
        "from openwellness_scheduler.config import CelerySettings\n"
        "print(CelerySettings().broker_url)",
        BACKEND_DIR / "scheduler",
        env_file,
        ("CELERY_BROKER_URL",),
    )
    assert out.strip() == "memory://from-file"

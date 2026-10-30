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

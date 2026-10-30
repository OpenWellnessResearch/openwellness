"""FOUND-01: CI workflow shape, using the 01-01 plan's yaml asserts.

Triggers, least-privilege permissions, SHA-pinned actions, no job
dependencies, and the iOS nightly workflow running on schedule only.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
SHA_PIN = re.compile(r"@[0-9a-f]{40}$")


def test_ci_triggers_permissions_pins_and_job_shape() -> None:
    text = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    # PyYAML (YAML 1.1) parses the bare key ``on`` as boolean True.
    on = doc.get("on", doc.get(True))
    assert set(on) == {"pull_request", "push"}
    assert on["push"]["branches"] == ["main"]
    assert doc["permissions"] == {"contents": "read"}
    assert {"backend", "dashboard", "mobile"} <= set(doc["jobs"])
    assert all("needs" not in job for job in doc["jobs"].values())
    uses = re.findall(r"uses:\s*(\S+)", text)
    assert uses and all(SHA_PIN.search(u) for u in uses), uses
    assert "secrets." not in text


def test_ios_nightly_runs_on_schedule_or_dispatch_only() -> None:
    text = (WORKFLOWS / "ios-nightly.yml").read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    on = doc.get("on", doc.get(True))
    assert set(on) == {"schedule", "workflow_dispatch"}
    uses = re.findall(r"uses:\s*(\S+)", text)
    assert all(SHA_PIN.search(u) for u in uses), uses

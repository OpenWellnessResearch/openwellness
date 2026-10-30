---
phase: 01-foundations-architecture-decisions
plan: 02
subsystem: infra
tags: [pydantic-settings, config, env-file, python]
requires: []
provides:
  - "openwellness_core.infrastructure.config.settings: ENV_FILE_VAR, resolve_env_file, OpenWellnessSettings, CouchbaseSettings, SyncGatewaySettings, MongoSettings, RedisSettings, PostgresSettings, AppConfig"
  - "One repo-root .env (OPENWELLNESS_ENV_FILE override) read by api and scheduler settings"
affects: [01-10 docs for .env location, postgres backend phases]
actuals:
  tokens: 9000
  tasks: 2
  commits: 3
plan_head_before: 5ee6076f30177e37bef165fc647f80a4d98c1842
plan_head_after: d70008d7fcc5cfece7474828fb38f05c68616bcf
tech-stack:
  added: [pydantic-settings (now a core dependency; already locked)]
  patterns: ["Settings subclasses declare only env_prefix; env_file merged from OpenWellnessSettings"]
key-files:
  created:
    - backend/core/src/openwellness_core/infrastructure/config/settings.py
    - backend/core/tests/conftest.py
    - backend/core/tests/test_settings.py
    - backend/api/tests/test_settings_env.py
  modified:
    - backend/core/pyproject.toml
    - backend/uv.lock
    - backend/api/src/openwellness_api/config.py
    - backend/scheduler/src/openwellness_scheduler/config.py
    - backend/api/tests/conftest.py
    - backend/scheduler/tests/conftest.py
key-decisions:
  - "Repo root is found via the docker-compose.yml marker; no marker found (container image) means no env file, compose-injected env vars apply"
  - "OPENWELLNESS_ENV_FILE is the override name; tests pin it to os.devnull"
  - "PostgresSettings.url defaults to empty: no default credentials"
requirements-completed: [FOUND-02, FOUND-03]
status: complete
---

# Phase 1 Plan 02: Single settings home and repo-root .env Summary

Datastore, Redis and Postgres settings now live once in core and every service settings class reads the one repo-root `.env` (or `OPENWELLNESS_ENV_FILE`), with precedence environment, then file, then defaults.

## What was done

- Task 1 (tracer): created `openwellness_core.infrastructure.config.settings`, added `pydantic-settings>=2.3` to core (lock gained only core's dependency metadata, no new package), thinned `openwellness_api.config` to re-exports plus API-only settings re-based on `OpenWellnessSettings`. A subprocess test proves `AppConfig` loads the override file from `backend/`.
- Task 2 (TDD): RED commit added core settings tests and api/scheduler tests; the two scheduler-facing tests failed on their planned assertions (`AppConfig` identity and `CELERY_BROKER_URL` from the file). GREEN rewired `openwellness_scheduler.config` to core and pinned `OPENWELLNESS_ENV_FILE=os.devnull` in the api, scheduler and (new) core conftests.

## TDD notes

- RED: the target tests failed with `AssertionError` on the planned behavior (not import or fixture errors). The core `test_settings.py` tests passed at RED because Task 1 had already delivered the module; only the scheduler tests were genuinely red. The `gsd_run check tdd-red-evidence` classifier was not run (plan `type: execute`, not `tdd`); semantic inspection was done by reading the pytest `E` lines.
- GREEN: scheduler config re-export plus conftest pins.
- Commits: `d49d19f` feat (Task 1), `17787cb` test (RED), `d70008d` feat (GREEN).

## Deviations from Plan

**1. [Rule 1 - Bug] Identity check moved to a subprocess**
- **Found during:** Task 2 GREEN
- **Issue:** Importing `openwellness_scheduler` in the api test process after the api container classes load raises `AttributeError: 'DependenciesContainer' object has no attribute '__self__'` (dependency-injector, order dependent; passes when the test file runs alone).
- **Fix:** `test_scheduler_and_api_share_one_app_config` runs the `A is S` comparison in a subprocess.
- **Files modified:** backend/api/tests/test_settings_env.py

**2. [Rule 3 - Blocking] Pyright errors in new core tests**
- **Issue:** pyright does not see pydantic-settings' `_env_file` init kwarg and flags TypedDict key access on `model_config`.
- **Fix:** one `_mongo()` helper with a narrow `# type: ignore[call-arg]`, plus `dict(model_config)` access. Pyright reports 0 errors.

## Known Stubs

None.

## Threat Flags

None. `.env` stays gitignored; tests never touch the repo-root `.env`.

## Verification

core 83 passed, api 190 passed, scheduler 4 passed; pyright 0 errors; lock diff vs 0007abe adds no `[[package]]` block.

## Self-Check: PASSED

Files and commits d49d19f, 17787cb, d70008d verified present on the branch.

---
phase: 01-foundations-architecture-decisions
plan: 10
subsystem: infra
tags: [env, docker-compose, docs, redis, celery]
requires: ["01-02"]
provides:
  - ".env.example with direct-run (localhost) Redis/Celery values and one-.env header"
  - "docker-compose.yml environment overrides for api and scheduler"
  - "backend/README.md Configuration section for the repo-root .env"
affects: []
actuals:
  tokens: 4000
  tasks: 2
  commits: 2
plan_head_before: 2b067ada42540a90777ab2023b04733373abc3fc
plan_head_after: 5cf008717935ec67be5c5452be322e39acf51965
key-files:
  modified:
    - .env.example
    - docker-compose.yml
    - backend/README.md
key-decisions:
  - "Compose environment overrides carry the redis service hostnames; .env keeps localhost so one file serves both paths"
requirements-completed: [FOUND-03]
status: complete
---

# Phase 1 Plan 10: One .env for direct runs and compose Summary

A single repo-root `.env` now works both for direct `uvicorn`/`celery` runs (localhost URLs) and under docker compose (api/scheduler `environment` overrides point at the compose `redis` service), documented in `.env.example` and `backend/README.md`.

## What was done

- Task 1 (tracer, `e0c1111`): rewrote the `.env.example` header (location, `OPENWELLNESS_ENV_FILE`, precedence), added `REDIS_URL`, switched Celery URLs to localhost, added a Mongo direct-run hint. Added `environment:` blocks to `api` and `scheduler` in `docker-compose.yml`. Verified by loading `.env.example` through the real `RedisSettings`/`CelerySettings` and parsing the compose file (`env-split-ok`, `env-example-ok`).
- Task 2 (`5cf0087`): rewrote README Configuration (repo-root location, override, precedence, compose overrides), added `REDIS_URL` and `POSTGRES_URL` rows, removed the two old under-backend references, and added the two migration notes with the old Celery lines literal (`docs-ok`).

## Deviations from Plan

None - plan executed exactly as written. Tracer gate: verify was automated-only and re-ran green.

## Known Stubs

None.

## Threat Flags

None. `.env` remains gitignored; header says never commit it (T-01-34).

## Self-Check: PASSED

Commits e0c1111 and 5cf0087 present; modified files exist.

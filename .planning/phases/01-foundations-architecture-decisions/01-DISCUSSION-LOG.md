# Phase 1: Foundations & Architecture Decisions - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-29
**Phase:** 01-foundations-architecture-decisions
**Areas discussed:** Owner & authz policy, Soft delete & retention, IDs/timestamps/tokens, CI & .env shape

---

## Owner & authz policy

| Option | Description | Selected |
|--------|-------------|----------|
| User id | Matches `users/{user}` routes and token `sub` | |
| Participant id | Data belongs to a study enrollment; contract change | |
| Confirm from legacy first | Planner investigates legacy docs/tests, ADR records finding | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Role gate only | Any coach reads any participant | |
| Assigned participants | Via `assigned_coach_id` | |
| Study membership | Coach sees participants in their studies | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Derive from participants | Studies where coach is assigned to ≥1 participant | |
| Study ids on coach role | `roles.coach.studies`, token claim, admin-managed | ✓ |
| New membership entity | StudyStaff table | |

| Option | Description | Selected |
|--------|-------------|----------|
| Admin global | Sees everything | ✓ |
| Admin study-scoped | Separate superuser role | |

| Option | Description | Selected |
|--------|-------------|----------|
| 404 owner, 403 role | Anti-enumeration | ✓ |
| 403 for both | Leaks existence | |

| Option | Description | Selected |
|--------|-------------|----------|
| Per resource × method | Mechanical for Phase 2 | ✓ |
| Per resource category | Shorter | |

**Notes:** Study-scoped coach overrides the research default (role gate in v1).

---

## Soft delete & retention

| Option | Description | Selected |
|--------|-------------|----------|
| Forever until purged | No timer | ✓ |
| Fixed window then purge | Beat job + setting | |

| Option | Description | Selected |
|--------|-------------|----------|
| Purge admin only | | ✓ |
| Owner and admin | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Hard delete row | | ✓ |
| Scrub + tombstone | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Archived removed from device | `deleted_at IS NULL` stream filter | ✓ |
| Synced with flag | Device keeps archived rows | |

---

## IDs, timestamps, tokens

User asked to compare UUIDv4 vs v7 before answering. Comparison covered stdlib availability (uuid7 only in Python 3.14), device-clock dependence for offline ids, B-tree insert locality (matters mainly for wearable tables), pagination still needing `created_at`, and minor creation-time leakage.

| Option | Description | Selected |
|--------|-------------|----------|
| Text UUIDv4 | Stdlib, v7 upgrade path noted | ✓ |
| Text UUIDv7 | Index locality, needs helper | |
| v7 for wearables only | Two generators | |

| Option | Description | Selected |
|--------|-------------|----------|
| double epoch seconds | Matches domain | ✓ |
| timestamptz | Idiomatic PG | |

| Option | Description | Selected |
|--------|-------------|----------|
| EdDSA + kid | | ✓ |
| RS256 + kid | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Short MADR in docs/adr/ | | ✓ |
| Single decisions doc | | |

---

## CI & .env shape

| Option | Description | Selected |
|--------|-------------|----------|
| JVM/Android host tests per PR | iOS nightly/manual | ✓ |
| Include iOS on macOS | ~10× cost | |

| Option | Description | Selected |
|--------|-------------|----------|
| Pyright errors fail, warnings don't | | ✓ |
| Warnings fail too | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Repo root .env | Compose already uses it | ✓ |
| backend/.env | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Real env > .env > defaults | | ✓ |
| .env overrides env | | |

---

## Claude's Discretion

- Env-file override variable name and repo-root resolution
- CI workflow layout and caching
- Exception mapping details for FOUND-06
- Port shapes for `RefreshSessionRepository` / `get_by_email`
- Exact coach-studies claim name

## Deferred Ideas

- Archive retention window / purge beat job
- StudyStaff membership entity
- iOS tests per PR
- UUIDv7

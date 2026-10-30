# 0002. Timestamp representation

- Status: Accepted
- Date: 2026-10-30
- Decisions: D-12

## Context

The domain already stores `created_at` and `updated_at` on `BaseOwnerEntity` as float epoch seconds (`time.time()`), next to int timezone-offset fields. The API converts to and from RFC 3339 at the wire boundary with `epoch_to_rfc3339` and `rfc3339_to_epoch` in `backend/api/src/openwellness_api/common/timestamps.py`. Some domain models instead declare `datetime` fields, and the refresh-session store (`auth/session_store.py`) keeps `datetime` values for expiry.

## Decision

- Every timestamp column in Postgres, including `created_at`, `updated_at`, `deleted_at` and the auth-table times, is `double precision` epoch seconds.
- The domain keeps float epochs.
- The wire stays RFC 3339 through `epoch_to_rfc3339` / `rfc3339_to_epoch`.
- Adapters convert the domain `datetime` fields listed below, and the refresh-session datetimes, to and from epoch seconds at the repository boundary.
- The tz-offset int fields stay as they are.

Domain fields typed `datetime` that adapters must convert:

| Model | Field | Type |
| ----- | ----- | ---- |
| `Admin` | `time_created` | `datetime` |
| `App` | `time_created` | `datetime` |
| `Device` | `time_created` | `datetime` |
| `Fitbit` | `time_created` | `datetime` |
| `Participant` | `time_created` | `datetime` |
| `Study` | `time_created` | `datetime` |
| `Study` | `time_updated` | `datetime` |
| `StudyMessage` | `time_created` | `datetime` |
| `User` | `registered_at` | `datetime` |
| `User` | `time_created` | `datetime` |

## Consequences

- No timezone ambiguity in storage: every value is seconds since the Unix epoch.
- Sub-microsecond precision is not guaranteed (a double holds about 15-16 significant digits).
- This is a one-way door: the column type spans about 37 tables, and PowerSync and the mobile client depend on it.

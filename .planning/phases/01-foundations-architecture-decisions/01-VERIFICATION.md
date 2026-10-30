---
phase: 01-foundations-architecture-decisions
verified: 2026-10-30T00:00:00Z
status: passed
score: 4/5 must-haves verified
covered_files: [".github/workflows/ci.yml", ".github/workflows/ios-nightly.yml", ".planning/phases/01-foundations-architecture-decisions/01-01-PLAN.md", ".planning/phases/01-foundations-architecture-decisions/01-01-SUMMARY.md", ".planning/phases/01-foundations-architecture-decisions/01-02-PLAN.md", ".planning/phases/01-foundations-architecture-decisions/01-02-SUMMARY.md", ".planning/phases/01-foundations-architecture-decisions/01-03-PLAN.md", ".planning/phases/01-foundations-architecture-decisions/01-03-SUMMARY.md", ".planning/phases/01-foundations-architecture-decisions/01-04-PLAN.md", ".planning/phases/01-foundations-architecture-decisions/01-04-SUMMARY.md", ".planning/phases/01-foundations-architecture-decisions/01-05-PLAN.md", ".planning/phases/01-foundations-architecture-decisions/01-05-SUMMARY.md", ".planning/phases/01-foundations-architecture-decisions/01-06-PLAN.md", ".planning/phases/01-foundations-architecture-decisions/01-06-SUMMARY.md", ".planning/phases/01-foundations-architecture-decisions/01-07-PLAN.md", ".planning/phases/01-foundations-architecture-decisions/01-07-SUMMARY.md", ".planning/phases/01-foundations-architecture-decisions/01-08-PLAN.md", ".planning/phases/01-foundations-architecture-decisions/01-08-SUMMARY.md", ".planning/phases/01-foundations-architecture-decisions/01-09-PLAN.md", ".planning/phases/01-foundations-architecture-decisions/01-09-SUMMARY.md", ".planning/phases/01-foundations-architecture-decisions/01-10-PLAN.md", ".planning/phases/01-foundations-architecture-decisions/01-10-SUMMARY.md", ".planning/phases/01-foundations-architecture-decisions/01-11-PLAN.md", ".planning/phases/01-foundations-architecture-decisions/01-11-SUMMARY.md", "backend/api/src/openwellness_api/auth/session_store.py", "backend/api/src/openwellness_api/errors/handlers.py", "backend/core/src/openwellness_core/adapters/mongo/repositories/mongo_base_repository.py", "backend/core/src/openwellness_core/infrastructure/config/settings.py", "docs/adr/0007-authorization-policy-table.md"]
covered_digest: "v4:sha256:200661f1dc30f4e9b86c671ce6cc8fcb9ac97e02d45f7cd13c47c5e19f148a53"
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:
  - truth: "Every pull request runs the core, api and scheduler suites, pyright, the dashboard checks and the mobile host tests, and a failing check shows on the PR (ROADMAP SC1)"
    test: "Open a PR from the phase branch; confirm the Backend, Dashboard and Mobile checks appear and go green. Then push a deliberately failing backend test commit and confirm the Backend check goes red and shows on the PR."
    expected: "Three checks on the PR; green on the clean commit, Backend red on the broken commit, Dashboard and Mobile unaffected (no needs: coupling)."
    why_human: "ci.yml exists and is correct on inspection, and every backend and dashboard command it runs exits 0 locally, but the workflow has never executed on GitHub (nothing pushed). The Mobile job (./gradlew testAndroidHostTest) has never run anywhere: no JDK or Android SDK on the planning machine. Plan 01-01's live-CI human check was deferred by the user."
human_verification:
  - test: "Live CI run on a PR (Plan 01-01 deferred check)"
    expected: "Backend, Dashboard and Mobile jobs all green on a clean PR; Backend red with the failure visible on the PR after a deliberately broken backend commit"
    why_human: "Needs a push to GitHub and a hosted runner. The Mobile job (./gradlew testAndroidHostTest, Corretto 21) has never been executed anywhere, so a first-run failure there is a real possibility."
---

# Phase 1: Foundations & Architecture Decisions Verification Report

**Phase Goal:** Contributors work on a trustworthy baseline: CI guards every PR, settings live in one place and load from `.env`, persistence flows only through datastore-neutral ports, and the cross-cutting decisions are written down before any Postgres schema exists
**Verified:** 2026-10-30
**Status:** human_needed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every PR runs core/api/scheduler suites, pyright, dashboard lint/typecheck/test/format and mobile host tests; a failing check shows on the PR | PRESENT_BEHAVIOR_UNVERIFIED | `.github/workflows/ci.yml` has three independent jobs (backend, dashboard, mobile), `on: pull_request` + `push: main`, no `paths` filters, no `needs:`, `if: !cancelled() && steps.<install>.outcome == 'success'` on each check, concurrency group keyed on PR number with cancel-in-progress, `permissions: contents: read`, no `secrets.` and no `pull_request_target` anywhere. `ios-nightly.yml` is schedule + workflow_dispatch only. Actions pinned by SHA. I ran every backend command locally: core 83 passed, api 227 passed, scheduler 4 passed, pyright 0 errors (12 warnings), N1QL lint exit 0; dashboard `npm run lint`, `typecheck` and `format:check` pass. Never executed on a hosted runner; Mobile job never run anywhere. Routed to human verification. |
| 2 | `uvicorn`/`celery` run directly get the same settings as under compose, from one documented `.env`; datastore and Redis settings defined once in `core` | VERIFIED | `core/.../infrastructure/config/settings.py` defines `CouchbaseSettings`, `SyncGatewaySettings`, `MongoSettings`, `RedisSettings`, `PostgresSettings` (empty-URL default, no creds), `AppConfig`, `resolve_env_file()` (cwd-independent, `OPENWELLNESS_ENV_FILE` override, repo-root `.env` found via `docker-compose.yml` marker). `api/config.py` and `scheduler/config.py` only import these (grep: no datastore or Redis class defined in either); scheduler `AppConfig` is the core class. Tests: `core/tests/test_settings.py` (precedence env > file > default, cwd independence, subclass config merge), `api/tests/test_settings_env.py` (subprocess runs from `backend/` and `backend/scheduler/` load the override file). Conftests in core, api and scheduler pin `OPENWELLNESS_ENV_FILE=os.devnull`. `.env.example` uses localhost for `REDIS_URL`/`CELERY_*`; `docker-compose.yml` overrides `REDIS_URL` (api) and `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` (scheduler) to `redis://redis:...`; `backend/README.md` documents location, override, precedence and the old-`.env` migration note. |
| 3 | OTP login, registration and refresh still work end to end after users-by-email and refresh sessions move behind ports; no domain entity imports `bson` or any datastore type | VERIFIED | Grep for `bson/pymongo/couchbase/redis/sqlalchemy/psycopg` and `ObjectId` under `core/.../domain` and `core/.../application`: zero hits. `grep bson\|pymongo` in `api/src` and `scheduler/src`: only a docstring mention. `Participant` ids are `str`; `MongoParticipantRepository._to_doc` owns ObjectId coercion (tests in `test_participant_ids.py` incl. on-disk ObjectId and empty-study refusal). `UserRepository.get_by_email` exists and `AuthService` uses it at service.py:254 and :417 (no `get_by_query`, no pymongo import in auth/). `RefreshSessionRepository` port + `MongoRefreshSessionRepository` (index and field names unchanged, collection injected); `RefreshSessionStore` takes `repo: RefreshSessionRepository`; `main.py` lifespan overrides `refresh_session_collection` with `AuthSettings.refresh_collection`, resolves the singleton, calls `ensure_indexes()`, and overrides `auth_container.refresh_session_repository`. Tests: `test_register_then_login_composes`, `test_refresh_rotation_and_reuse_revokes_family`, `test_revoke_single_then_refresh_401` in `test_auth_api.py`; `test_lifespan_wires_refresh_session_repository` and default/custom collection-name tests in `test_auth_container.py`; `test_refresh_session_repository.py`; `test_session_store.py`. All pass in the 227-test api run. |
| 4 | Malformed resource id returns 404; datastore outage returns 5xx logged through `logging` instead of an empty result | VERIFIED | `object_id_or_none` guards `get_by_id`, `save`, `delete`, `unarchive` and the device and participant lookups; `mongo_base_repository.py` has no broad `except` (only `DuplicateKeyError`). `errors/handlers.py` registers `exception_handler(Exception)`: `logger.error(..., type(exc).__name__, exc_info=exc)` and a generic `INTERNAL` 500 body (no driver text). `grep print(` over `core/src`, `api/src`, `scheduler/src`: none. Tests in `test_repository_errors.py` (malformed id 404 via real Mongo repo, unknown id 404, outage on get and list is a logged 500 not an empty list, save/delete malformed id 404, delete via API 404, duplicate email 409 without the email) pass. |
| 5 | ADRs record id format, timestamps, soft-delete, token format, `owner` semantics and the per-resource authorization policy table | VERIFIED | `docs/adr/` holds README index + ADRs 0001-0007, all Accepted, each with Status/Decisions/Context/Decision/Consequences; index check: 7 files, `bad []`, `missing []`. Content checks: 0001 UUIDv4/UUIDv7 upgrade path; 0002 `double precision` epoch seconds, RFC 3339 on wire, lists datetime fields; 0003 `deleted_at`, indefinite undelete, admin-only purge with no tombstone, archived rows leave sync; 0004 EdDSA/Ed25519 + `kid`, JWKS, opaque sha256 refresh, `aud=powersync`, HS256 retired, no participant study claim; 0005 has Evidence, Decision, Entity classification (all four data classes; the 29 owner-scoped modules plus conversation/study_settings are classified, the 7 modules not listed are top-level routes: admin, app, device, fitbit, study, study_message, user, confirmed by router paths) and records developer confirmation; 0006 `roles.coach.studies` -> `coach_studies` claim, admins global, 930 s staleness bound, `Admin.study_ids` not authoritative; 0007 policy table. I re-ran the 0007 gate against live `RESOURCE_MODULES`: `policy-ok 36` (36 rows, anonymous none everywhere, admin all seven everywhere, purge admin-only, vocabulary valid). Post-summary amendment a79bde7 (membership predicates `self-member-group`/`self-member-conversation`, `self-fitbit` with OAuth tokens nulled for non-admins) is internally consistent with the Rule table and Scope predicates sections and did not disturb the policy gate. |

**Score:** 4/5 truths verified (1 present, behavior-unverified: live CI)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `.github/workflows/ci.yml` | Per-PR backend, dashboard, mobile jobs containing `testAndroidHostTest` | VERIFIED (static) | Substantive and wired to `uv.lock` (`uv sync --frozen --extra dev`), `package-lock.json` (`npm ci`), `gradlew testAndroidHostTest`. Host-test targets exist in Gradle (`withHostTest` in core/data, core/domain, core/presentation, shared, feature/auth/data). Not executed on a runner. |
| `.github/workflows/ios-nightly.yml` | Nightly/manual iOS | VERIFIED | `schedule` + `workflow_dispatch`, no PR trigger. |
| `core/.../config/settings.py` | Single settings home | VERIFIED | See truth 2. |
| `core/tests/test_settings.py`, `api/tests/test_settings_env.py` | Resolution, precedence, subprocess tests | VERIFIED | Present, pass. |
| `mongo_base_repository.py` (`object_id_or_none`) | Guarded ids, no swallow | VERIFIED | See truth 4. |
| `errors/handlers.py` | Catch-all logged 500, 409 ALREADY_EXISTS | VERIFIED | Both present; `DuplicateEntityException` defined in application layer, adapter raises it. |
| `domain/models/participant.py` | Datastore-free Participant | VERIFIED | No driver imports. |
| `user_repository.py` (`get_by_email`), `refresh_session_repository.py`, `mongo_refresh_session_repository.py`, `session_store.py`, `repository_container.py` (`refresh_session = DISingleton`) | Ports and wiring | VERIFIED | All present and used. |
| `docs/adr/0001`-`0007` + README | ADR set | VERIFIED | See truth 5. |
| `.env.example`, `docker-compose.yml`, `backend/README.md` | One-.env docs | VERIFIED | See truth 2. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| api/scheduler `config.py` | core `settings.py` | import of `AppConfig`/`OpenWellnessSettings` | WIRED | Direct imports present. |
| `AuthService` | `UserRepository.get_by_email` | `_user_repo.get_by_email` | WIRED | service.py:254, :417. |
| Mongo repos | `object_id_or_none` | import from base | WIRED | Used in base, device, participant, refresh-session repos. |
| `main.py` lifespan | `AuthSettings.refresh_collection` -> `refresh_session` singleton -> `AuthContainer.refresh_session_repository` | provider overrides | WIRED | main.py:63-66; proven by lifespan test. |
| `RefreshSessionStore` | `RefreshSessionRepository` | constructor `repo` | WIRED | |
| ADR 0007 | `RESOURCE_MODULES` | one row per module | WIRED | gate prints `policy-ok 36`. |
| ADR 0007 | ADR 0005 | data class -> cell rule table | WIRED | |

### Data-Flow Trace (Level 4)

Not applicable: this phase renders no dynamic UI data. Settings values flow from env/file into pydantic classes consumed by the container (covered by the subprocess tests).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| core suite | `uv run --frozen pytest` in `backend/core` | 83 passed | PASS |
| api suite | same in `backend/api` | 227 passed | PASS |
| scheduler suite | same in `backend/scheduler` | 4 passed | PASS |
| pyright | `uv run --frozen pyright` in `backend` | 0 errors, 12 warnings | PASS |
| N1QL lint | `check_no_fstring_n1ql.py` | exit 0 | PASS |
| Dashboard | `npm run lint`, `typecheck`, `format:check` | all pass | PASS |
| Dashboard `npm test` | not rerun (local Node is 26; CI pins Node 22, where Node 25+ breaks jsdom localStorage) | SKIPPED | SKIP |
| ADR index + policy gate | scripted checks from plan 01-09 | `bad []`, `missing []`, `policy-ok 36` | PASS |
| Mobile host tests | `./gradlew testAndroidHostTest` | no JDK/Android SDK locally | SKIP |

### Probe Execution

SKIPPED: no probe scripts declared or present (`scripts/*/tests/probe-*.sh` absent).

### Requirements Coverage

All seven IDs appear in plan frontmatter and in REQUIREMENTS.md (traceability rows 124-130 map FOUND-01..07 to Phase 1). No orphaned requirements.

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| FOUND-01 | 01-01 | CI runs all suites, pyright, dashboard checks, mobile host tests on every PR | NEEDS HUMAN | Workflow correct and commands green locally; never run on GitHub; Mobile never run anywhere. REQUIREMENTS.md already marks it `[x] Complete`; that is premature until the live run happens. |
| FOUND-02 | 01-02 | Settings defined once in core, consumed by api and scheduler | SATISFIED | Truth 2. |
| FOUND-03 | 01-02, 01-10 | `.env` loaded when run directly and under compose, one documented location | SATISFIED | Truth 2; subprocess tests. |
| FOUND-04 | 01-04 | Domain entities carry no datastore types | SATISFIED | Truth 3; grep clean; Mongo adapter owns coercion. |
| FOUND-05 | 01-05, 01-06, 01-11 | Auth persistence behind ports | SATISFIED | Early tick at 01-06 is now accurate: 01-05 (users-by-email), 01-06 (port + adapter) and 01-11 (store over port, lifespan wiring, no pymongo in `api/src`) all landed. |
| FOUND-06 | 01-03, 01-05 | Repo errors not swallowed; malformed id 404; outage 5xx logged; no print | SATISFIED | Truth 4. |
| FOUND-07 | 01-07, 01-08, 01-09 | ADRs for id, timestamp, soft delete, token, owner, policy table | SATISFIED | Truth 5. Early tick at 01-07 was premature at the time (only 4 of 6 ADRs existed) but is accurate now that 0005-0007 exist and are Accepted. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `core/.../adapters/mongo/model/mongo_base_entity.py` | 68 | `except Exception` in `_to_objectid` serializer silently mints a fresh ObjectId for an unparseable id | Info | Pre-existing, intentional (domain default ids are uuid4 strings assigned on create). `save`/`delete`/`unarchive` now guard malformed ids before this serializer, so it cannot mask a malformed-id update. Revisit when Postgres adapters land (ADR 0001). |
| `api/.../auth/session_store.py` | 167 | `except Exception: ... clear_rotated; raise` | Info | Rollback then re-raise; not a swallow. |
| `api/.../main.py`, `scheduler/.../celery_app.py` | 75-96 | Broad `except` on startup ping/shutdown | Info | Documented best-effort resilience, `# pragma: no cover`. |
| `.planning/ROADMAP.md` | 15 | Phase 1 checkbox still `[ ]` while plans are 11/11 | Info | Bookkeeping; tick when the phase is closed. |

No `TBD`/`FIXME`/`XXX` markers in the phase's modified implementation files or ADRs. No `print()` in service source.

### Human Verification Required

#### 1. Live CI run on a PR (deferred Plan 01-01 check)

**Test:** Push the phase branch and open a PR. Confirm Backend, Dashboard and Mobile checks appear and all go green. Then push a commit with a deliberately failing backend test and confirm the Backend check goes red on the PR while the other two are unaffected.
**Expected:** Three independent checks; a red backend commit shows on the PR.
**Why human:** Needs a hosted runner. The Mobile job (`./gradlew testAndroidHostTest`, Corretto 21, Gradle host-test targets) has never run anywhere; a first-run failure there would not be a code gap in the workflow but would need fixing before "CI guards every PR" is true. The dashboard `npm test` was only validated locally under Node 22 via Docker per the plan; the first CI run is its confirmation on Linux.

### Gaps Summary

No code gaps. All backend, config, port-boundary and ADR deliverables exist, are substantive, wired and tested; the suites, pyright, N1QL lint, dashboard lint/typecheck/format and the ADR policy gate all pass on this checkout. The one open item is the deferred live-CI confirmation of ROADMAP criterion 1 (workflow correct on inspection, never executed; Mobile job never run anywhere), which is why the status is `human_needed` rather than `passed`. FOUND-01 is ticked Complete in REQUIREMENTS.md ahead of that confirmation; the caveat stands until the PR run is seen green. Security note: with no route authentication until Phase 2, the 409 on duplicate-email `POST /v1/users` and the anonymous `GET /v1/users` remain a known, accepted pre-Phase-2 window (recorded in ADR 0007); no production deployment docs have been added.

---

_Verified: 2026-10-30_
_Verifier: Claude (gsd-verifier)_

---
phase: "01"
slug: "foundations-architecture-decisions"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-30"
---

# Phase 01 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Produced by `/gsd-secure-phase 01` (State B: no SECURITY.md existed; all 11 plans carried a `<threat_model>` block). Verification depth is ASVS L1 (grep-level evidence that each mitigation or acceptance exists). Paths are repo-relative.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| PR author → CI runner | Untrusted PR code runs in GitHub Actions (plan 01-01) | Repo contents; no secrets exposed |
| Third-party actions → CI runner | `uses:` steps and package installs (01-01) | Build toolchain, lockfiles |
| Operator filesystem → process config | Repo-root `.env` and `OPENWELLNESS_ENV_FILE` (01-02, 01-10) | Datastore URLs, credentials, JWT secret |
| Compose file → container environment | Redis and Celery host overrides (01-10) | Service hostnames |
| Developer machine → test run | Conftests must not read a developer's `.env` (01-02) | Local credentials |
| HTTP client → API | Path ids, request bodies, `/v1/auth:*` (01-03, 01-04, 01-05, 01-06) | Participant ids, emails, OTP codes, refresh tokens |
| API → Mongo | Driver errors, reference ids, unique email index, CAS rotation (01-03, 01-04, 01-05, 01-06, 01-11) | Documents, error detail |
| Operator config → session storage | `API_AUTH_REFRESH_COLLECTION` (01-11) | Refresh session documents |
| Token claims → route and sync predicates | `{user}` path binding, coach study scope (01-08, 01-09) | Participant and study identifiers |
| Public repo docs → readers | ADRs 0001–0007 (01-07, 01-08, 01-09) | Design decisions; must carry no secrets |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-01-01 | Tampering / Elevation | `uses:` actions in ci.yml, ios-nightly.yml | high | mitigate | Every action pinned to a 40-hex SHA; top-level `permissions: contents: read` (`.github/workflows/ci.yml:10-11`, `ios-nightly.yml:9-10`); enforced by `backend/core/tests/test_ci_workflow.py` | closed |
| T-01-02 | Information disclosure | Fork PRs reading secrets | high | mitigate | `pull_request` trigger only; no `secrets.` reference in either workflow (`ci.yml:3-6`) | closed |
| T-01-03 | Tampering | Script injection via `github.event.*` in `run:` | medium | mitigate | Only `${{ }}` is the concurrency group key (`ci.yml:14`); none in `run:` | closed |
| T-01-04 | Information disclosure | Repo-root `.env` committed | high | mitigate | `.gitignore:47-50` ignores `.env` and `.env.*`, keeps `.env.example`; header warns never to commit | closed |
| T-01-05 | Tampering | `OPENWELLNESS_ENV_FILE` override | low | accept | Accepted in 01-02 plan; override at `backend/core/src/openwellness_core/infrastructure/config/settings.py:23` is an operator-only knob | closed |
| T-01-06 | Information disclosure / Tampering | Tests reading a developer's `.env` | medium | mitigate | All three `tests/conftest.py` pin `OPENWELLNESS_ENV_FILE` to `os.devnull` | closed |
| T-01-07 | Elevation | Default datastore credentials | medium | mitigate | Postgres `url` defaults to empty (`settings.py:85-94`); Couchbase defaults unchanged by design, boot guard deferred | closed |
| T-01-08 | Information disclosure | Catch-all 500 body | medium | mitigate | Uniform "Internal error." envelope (`backend/api/src/openwellness_api/errors/handlers.py:169-189`); `test_repository_errors.py:78-90` asserts no host detail leaks | closed |
| T-01-09 | Denial / Repudiation | Outages masked as 404 or empty lists | medium | mitigate | Mongo base repo catches only `DuplicateKeyError` (`mongo_base_repository.py:59, 98`); tests cover logged 500 on outage | closed |
| T-01-10 | Information disclosure | Server log content | low | mitigate | Logs exception type, method, path only (`handlers.py:178-185`); bodies and headers never logged | closed |
| T-01-11 | Tampering | Malformed ids reaching `ObjectId()` | medium | mitigate | `object_id_or_none` (`mongo_base_repository.py:20`) maps malformed ids to not-found; `test_repository_errors.py:116-136` | closed |
| T-01-12 | Tampering | Malformed reference ids written to Mongo | medium | mitigate | `mongo_participant_repository.py:55-70` refuses bad references on create; `test_participant_ids.py:72-89` | closed |
| T-01-13 | Information disclosure | Participant reachable under wrong study | medium | mitigate | `resources/participant.py:69-75` returns 404 when `study_id != study`; `test_participant_ids.py:64` | closed |
| T-01-14 | Information disclosure (enumeration) | `send_login_code`, `_eligible_registration_target` | high | mitigate | Constant lookup shape asserted by recording repo (`test_auth_service.py:659-671, 761`); `auth/service.py:254, 417` | closed |
| T-01-15 | Information disclosure | 409 body and duplicate-key message | medium | mitigate | Messages carry collection name only (`mongo_base_repository.py:53`, `handlers.py:101`); tests assert the email is absent | closed |
| T-01-16 | Spoofing | Duplicate users per email in legacy data | low | mitigate | More than one user per email is ineligible; sha256-keyed warning (`auth/service.py:276-290`) | closed |
| T-01-17 | Spoofing / Elevation | Refresh token reuse and rotation race | high | mitigate | Conditional `update_one` with `matched_count == 1` CAS (`mongo_refresh_session_repository.py:88-96`); `test_refresh_session_repository.py:103-125` | closed |
| T-01-18 | Information disclosure | Refresh token storage | high | mitigate | `RefreshSession` stores `token_hash` only (`application/repositories/refresh_session_repository.py:21-38`) | closed |
| T-01-19 | Denial | Logout caused by schema drift | medium | mitigate | Same 14 document keys and 4 index names as the old store (`test_refresh_session_repository.py:70-101`) | closed |
| T-01-20 | Information disclosure | ADR text leaking secrets | low | mitigate | ADR 0004 names env vars only (`docs/adr/0004-access-token-format.md:9`) | closed |
| T-01-21 | Elevation | Token design (ADR 0004) | medium | mitigate | `aud` claim and HS256 retirement recorded (`0004:19-27`); implementation is Phase 3 | closed |
| T-01-22 | Tampering | Purge semantics (ADR 0003) | medium | mitigate | Purge admin-only and one-way (`docs/adr/0003-soft-delete-archive-purge.md:16, 22`) | closed |
| T-01-23 | Elevation (IDOR) | Owner semantics feeding Phases 2 and 6 | high | mitigate | ADR 0005 accepted with file:line evidence (`0005:3, 16-28`); developer checkpoint recorded in `01-08-SUMMARY.md` | closed |
| T-01-24 | Information disclosure | `users/{user}` carrying two id spaces | high | mitigate | Binding claim stated per route family (`0005:44, 87`) | closed |
| T-01-25 | Elevation | Over-broad policy cells (anonymous, coach, purge) | high | mitigate | ADR 0007: anonymous is `none` on all 36 rows, purge admin-only (`0007:19, 24, 85+`); row coverage enforced by `backend/api/tests/test_adr_policy_table.py` | closed |
| T-01-26 | Elevation | Stale `coach_studies` claims | medium | mitigate | Bounded to 930 s; session revocation immediate (`docs/adr/0006-coach-study-scope.md:18, 25`) | closed |
| T-01-27 | Information disclosure | 403 vs 404 revealing existence | medium | mitigate | 404 for wrong owner or out of scope; 403 only for missing role (`0007:17-18`) | closed |
| T-01-28 | Elevation | `filter=` widening scope | high | mitigate | Scope applies before `filter=` (`0007:23`); hostile-filter test is a Phase 2 obligation | closed |
| T-01-29 | Elevation | Cell whose scope cannot be computed | high | mitigate | Self-study fails closed; device coach cell is `none` (`0007:47, 55, 62, 69`) | closed |
| T-01-30 | Tampering / Denial | Compose `environment` overriding Redis URLs | low | accept | Accepted in 01-10 plan; override comments in `docker-compose.yml:7, 25` and `.env.example:36-41` | closed |
| T-01-31 | Denial | Custom `API_AUTH_REFRESH_COLLECTION` ignored | medium | mitigate | Override applied before singleton resolves (`main.py:63`, `repository_container.py:332-340`); `test_auth_container.py:228-252` | closed |
| T-01-32 | Elevation / Tampering | Owner-scoped create/patch, coach cross-study writes | high | mitigate | Study-binding rule, immutable owner and study_id, fail-closed lookups (`0007:67, 73-80`) | closed |
| T-01-33 | Information disclosure (enumeration) | 409 on duplicate-email `POST /v1/users` | low | accept | Recorded as the pre-Phase-2 accepted gap (`0007:142`); route auth closes it | closed |
| T-01-34 | Information disclosure | Repo-root `.env` (restates T-01-04) | high | mitigate | As T-01-04 | closed |
| T-01-35 | Spoofing / Elevation | Refresh reuse and race (restates T-01-17) | high | mitigate | `session_store.py:137-150` revokes the family on reuse or lost CAS; 16 tests in `test_session_store.py` | closed |
| T-01-SC (01-01) | Tampering | Supply chain: npm, pip, Gradle installs in CI | high | mitigate | `uv sync --frozen` (`ci.yml:34`), `npm ci` (`ci.yml:75`), `distributionSha256Sum` in the Gradle wrapper properties | closed |
| T-01-SC (01-02 … 01-11) | Tampering | Supply chain: new packages per plan | low | accept | 01-02 added pydantic-settings, already locked (`backend/uv.lock`); the other nine plans added no packages | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

Register notes: ids T-01-01 through T-01-35 are each defined in exactly one plan with no collisions after the 01-10 and 01-11 renumber. `T-01-SC` is reused as a per-plan supply-chain row in all 11 plans; it is split into two rows above by disposition. T-01-34 and T-01-35 explicitly restate T-01-04 and T-01-17. No SUMMARY raised a new threat; every `## Threat Flags` section reads "None" or confirms the planned mitigation.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-01-01 | T-01-05 | `OPENWELLNESS_ENV_FILE` is an operator-controlled override; whoever can set process env already controls config | Plan 01-02 | 2026-10-30 |
| R-01-02 | T-01-30 | Compose overrides only the Redis and Celery hostnames, documented in the compose file and `.env.example` | Plan 01-10 | 2026-10-30 |
| R-01-03 | T-01-33 | Duplicate-email 409 is an email-existence oracle until route auth lands in Phase 2; recorded in ADR 0007 Consequences | Plan 01-05, ADR 0007 | 2026-10-30 |
| R-01-04 | T-01-SC (01-02 … 01-11) | One new locked dependency (pydantic-settings); remaining plans added none | Plans 01-02 … 01-11 | 2026-10-30 |

*Accepted risks do not resurface in future audit runs.*

Carried forward, not accepted here: T-01-21 (HS256 still issued until Phase 3), T-01-28 (hostile-filter test owed by Phase 2), and the Couchbase default credentials outside T-01-07's Postgres scope.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-30 | 46 | 46 | 0 | /gsd-secure-phase 01 (L1 grep-level, register extraction by read-only agent) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-30

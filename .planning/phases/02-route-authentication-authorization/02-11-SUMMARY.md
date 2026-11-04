---
phase: 02-route-authentication-authorization
plan: 11
subsystem: auth
tags: [kotlin, ktor, mobile, d-02, d-11, not-participant, bearer]
type: execute
status: complete

requires:
  - phase: 02-route-authentication-authorization
    provides: staff sign-in with OTP-issued tokens (02-01), so a coach can obtain a token and reach the participant app
provides:
  - AuthError.NotParticipant and string auth_error_not_participant, mapped in the exhaustive AuthErrorToUiText when
  - gate in OpenWellnessAuthRepository.persistVerified that refuses a null or blank participant before tokenStorage.saveTokens, on both verify paths, and revokes the just-issued refresh token best-effort
  - ResourceCallBearerTest proving the shared client sends Bearer on a non-auth path and nothing with no stored token
affects: [02-12, phase 8 mobile resource calls]

actuals:
  tokens: 3200
  tasks: 2
  commits: 3

commits: 3
plan_head_before: 3008e71a22d4c957d2643c6a88644b886e4a5d9c
plan_head_after: a1d4d4a1a37225a27d658abded113d6affafed5b

tech-stack:
  added: []
  patterns:
    - "UX-only client gate before the token save; the API stays the security boundary"

key-files:
  created:
    - frontend/mobile/feature/auth/data/src/androidHostTest/kotlin/edu/openwellness/mobile/feature/auth/data/ResourceCallBearerTest.kt
  modified:
    - frontend/mobile/feature/auth/domain/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/domain/AuthError.kt
    - frontend/mobile/feature/auth/data/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/data/OpenWellnessAuthRepository.kt
    - frontend/mobile/feature/auth/presentation/src/commonMain/kotlin/edu/openwellness/mobile/feature/auth/presentation/util/AuthErrorToUiText.kt
    - frontend/mobile/feature/auth/presentation/src/commonMain/composeResources/values/strings.xml
    - frontend/mobile/feature/auth/data/src/androidHostTest/kotlin/edu/openwellness/mobile/feature/auth/data/OpenWellnessAuthRepositoryTest.kt

key-decisions:
  - "The gate fires only on a null or blank participant in the server response, so a real participant is never locked out"
  - "The revoke result is discarded: a failed revoke must not change the refusal"
  - "D-11 mobile proof is the MockEngine test, a developer-accepted deviation (OQ5); no new client code"

requirements-completed: [AUTH-09]

coverage:
  - id: D1
    description: "A staff account verifying OTP in the app is refused with NotParticipant, no token reaches storage, on login, registration, and blank participant"
    requirement: AUTH-09
    verification:
      - kind: unit
        ref: "OpenWellnessAuthRepositoryTest#verifyLogin_nullParticipant_rejected_noTokensSaved"
        status: pass
      - kind: unit
        ref: "OpenWellnessAuthRepositoryTest#verifyRegistration_nullParticipant_rejected"
        status: pass
      - kind: unit
        ref: "OpenWellnessAuthRepositoryTest#verifyLogin_blankParticipant_rejected"
        status: pass
    human_judgment: false
  - id: D2
    description: "The just-issued refresh token is revoked after a refused sign-in"
    requirement: AUTH-09
    verification:
      - kind: unit
        ref: "OpenWellnessAuthRepositoryTest#verifyLogin_nullParticipant_attemptsRevoke"
        status: pass
    human_judgment: false
  - id: D3
    description: "A participant's sign-in is unchanged: tokens saved, session returned"
    requirement: AUTH-09
    verification:
      - kind: unit
        ref: "OpenWellnessAuthRepositoryTest#verifyLogin_onSuccess_returnsSession_savesTokens_andResolvesColonRoute"
        status: pass
    human_judgment: false
  - id: D4
    description: "The shared HttpClient attaches the stored access token preemptively on a non-auth path"
    requirement: AUTH-09
    verification:
      - kind: unit
        ref: "ResourceCallBearerTest#get_onResourcePath_attachesBearerPreemptively"
        status: pass
      - kind: unit
        ref: "ResourceCallBearerTest#get_withNoStoredToken_sendsNoAuthorizationHeader"
        status: pass
    human_judgment: false
  - id: D5
    description: "The refusal message reads clearly on a phone"
    verification: []
    human_judgment: true
    rationale: "Copy and on-device display are not asserted by any test; the D-13 UAT in plan 02-12 covers it"

duration: 12min
completed: 2026-11-04
---

# Phase 2 Plan 11: Mobile Participant Gate Summary

**The mobile repository now refuses any verified session without a participant (NotParticipant, no token saved, refresh token revoked), and a MockEngine test proves the shared client sends the bearer on a non-auth path.**

## Performance

- **Duration:** about 12 min
- **Completed:** 2026-11-04T23:58Z
- **Tasks:** 2
- **Files modified:** 6 (1 created)

## Accomplishments
- `persistVerified` checks `participant.isNullOrBlank()` after `toAuthSession()` and before `saveTokens`; both `verifyLoginCode` and `verifyRegistrationCode` route through it.
- On refusal it calls `remote.revokeCurrent(refreshToken)` and ignores the result, then returns `Result.Error(AuthError.NotParticipant)`. `LoginViewModel` needed no change: it passes any error to `toUiText()`.
- `ResourceCallBearerTest` asserts on the request the engine captured: `Authorization: Bearer access-1` on `users/p-1/weights`, absent with empty storage.

## Task Commits

1. **Task 1 (tracer, TDD): staff account refused before any token is saved**
   - RED `1afdd0b` (test): four failing tests plus the `NotParticipant` variant, string and `when` branch needed for them to compile
   - GREEN `b098026` (feat): the gate in `persistVerified`
2. **Task 2: bearer attached on a non-auth path** - `a1d4d4a` (test)

**Plan metadata:** the docs commit that follows this file.

## TDD Gate Compliance

- **RED:** `./gradlew testAndroidHostTest` exited 1 with 12 tests, 4 failed, all four being the new tests, on assertion errors (`OpenWellnessAuthRepositoryTest.kt` lines 195, 208, 225, 238). `gsd_run check tdd-red-evidence` on the unchanged JUnit XML returned `RED_EVIDENCE_OK` (`target_test_failed`, format junit). Semantic assessment: the target test compiled, executed, and failed because the unguarded code returned `Success` and saved tokens, which is the planned behavior gap, not a setup or compile fault.
- **GREEN:** same command exited 0, 12 tests, 0 failures.
- **REFACTOR:** none needed.
- The RED commit includes the `AuthError.NotParticipant` scaffolding. A test cannot reference a missing symbol without the whole run being a build failure (INVALID_RED), and the exhaustive `when` forced the UI branch and string with it.

## Decisions Made
- The gate keys on a null or blank participant only, matching the prohibition against locking out a real participant.
- Followed the plan's OQ5 deviation: D-11's mobile proof is a host test, not an app resource call (the app has none).

## Deviations from Plan

None - plan executed exactly as written.

The RED commit carrying the type scaffolding is a TDD-mechanics note (above), not a plan deviation.

## Issues Encountered
- A Task 2 build failed once because `FakeTokenStorage` was still `private` after a BSD `sed -i` call without a suffix argument silently did nothing; fixed with Edit and the rerun passed.

## Verification
- `./gradlew testAndroidHostTest --stacktrace` exit 0 after Task 1 GREEN and after Task 2 (run with the JBR `JAVA_HOME` and `ANDROID_HOME` as directed).
- `grep -c auth_error_not_participant strings.xml` = 1 (baseline 0).
- `isNullOrBlank` check precedes `tokenStorage.saveTokens` in `persistVerified`.
- `git diff --stat 583f04f HEAD -- frontend/dashboard` prints nothing.
- `ResourceCallBearerTest` report present with `tests="2" failures="0"`; no production Kotlin changed in Task 2.

## User Setup Required

None for this run: the plan's `user_setup` (JDK 21, SDK platform 36, `local.properties`) was declared satisfied by the caller, with Gradle provisioning Corretto 21 and Android Studio's JBR as `JAVA_HOME`. No `USER-SETUP.md` was generated and `local.properties` was not created.

## Threat Flags

None. T-02-29 and T-02-30 are mitigated and test-covered. No new network surface.

## Known Stubs

None.

## Next Phase Readiness
- Ready for 02-12. On-device behavior (message wording, no session restore) is for its UAT. The dashboard keeps its own gate and the same 30-day server-session residue for a refused staff sign-in, which D-02 leaves out of scope.

## Self-Check: PASSED

- FOUND: ResourceCallBearerTest.kt and the five modified files
- FOUND commits: 1afdd0b, b098026, a1d4d4a

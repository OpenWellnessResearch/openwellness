# Phase 2: Route Authentication & Authorization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-04
**Phase:** 2-Route Authentication & Authorization
**Areas discussed:** Staff sign-in, Denial edge cases, End-to-end proof, Policy wiring & audit

---

## Staff sign-in

| Option | Description | Selected |
|--------|-------------|----------|
| Backend + mobile gate | Backend accepts pid or coach/admin; dashboard unchanged; mobile rejects no-participant accounts | ✓ |
| Backend only | Same backend rule, no mobile change | |
| Backend enforces per client | Clients declare their app; spoofable, changes wire contract | |

**User's choice:** Backend + mobile gate
**Notes:** The first version of this question was rejected for clarification. The developer asked whether participant and staff auth differ, noting participants must not log in to the dashboard but must log in to the app. Answer: one backend, with only the dashboard distinguishing. The question was reframed around both clients.

| Option | Description | Selected |
|--------|-------------|----------|
| Waive it for staff | Coach/admin need is_active plus role | ✓ |
| Stamp it on admin create | Server writes verified_id on staff create | |
| Staff registration flow | New auth:* verb and client UI | |

**User's choice:** Waive it for staff

| Option | Description | Selected |
|--------|-------------|----------|
| Small dev seed script | Admin, coach, participant via ports; replaced in Phase 11 | ✓ |
| Manual datastore insert | UAT notes give documents to insert | |
| Pull bootstrap into Phase 2 | Build KIT-06 now | |

**User's choice:** Small dev seed script
**Notes:** Empty-study-list coach can log in and match nothing; confirmed at the area checkpoint.

---

## Denial edge cases

| Option | Description | Selected |
|--------|-------------|----------|
| Scope first, so 404 | Out of scope is 404 for any method | ✓ |
| Role first, so 403 | Check role cell before any record | |

**User's choice:** Scope first, so 404

| Option | Description | Selected |
|--------|-------------|----------|
| Union of cells | Allowed if any held role's cell and scope allow | ✓ |
| Most-privileged role only | Evaluate only the highest role | |
| Forbid dual roles | Refuse accounts holding both | |

**User's choice:** Union of cells

| Option | Description | Selected |
|--------|-------------|----------|
| 404 on no visible records | Filter by study_id; 404 if filtering removed all | ✓ |
| Always 200, filtered | Pure record filter; departs from criterion 3 wording | |
| 404 by current Participant study | Read Participant on each list | |

**User's choice:** 404 on no visible records
**Notes:** After the answer, Claude disclosed a leak the option's description had omitted: 404 vs empty 200 tells a coach whether an out-of-study id has records in range. The developer did not overrule it at the checkpoint, so it is recorded as an accepted risk.

| Option | Description | Selected |
|--------|-------------|----------|
| Off unless enabled | One setting, default off; .env.example enables locally | ✓ |
| Leave public | Listed as test exemptions | |
| Remove entirely | Off with no setting | |

**User's choice:** Off unless enabled
**Notes:** Claude first recommended leaving them public. The developer asked whether that adds unnecessary security risk. Claude revised the recommendation: instance identification and CDN-loaded scripts on the docs pages, with no benefit to either client.

---

## End-to-end proof

| Option | Description | Selected |
|--------|-------------|----------|
| Replace with a static check | Grep call sites; enforce in one step | ✓ |
| Run it as written | Ship would-be-401 logging first | |
| Also cover outside clients | Run against deployments with other callers | |

**User's choice:** Replace with a static check

| Option | Description | Selected |
|--------|-------------|----------|
| Auth flows + one real call | Auth flows plus one resource call per role | ✓ |
| Auth flows only | Sign-in, refresh, sign-out | |
| Add a real screen per client | New data view per client | |

**User's choice:** Auth flows + one real call

| Option | Description | Selected |
|--------|-------------|----------|
| CI test + one manual UAT | Pytest on fakes plus one UAT with real clients | ✓ |
| CI test only | Pytest on fakes | |
| Manual UAT only | Real clients, no regression guard | |

**User's choice:** CI test + one manual UAT

| Option | Description | Selected |
|--------|-------------|----------|
| Android and iOS simulator | Both, plus the dashboard | ✓ |
| Android only | Leans on nightly iOS CI | |
| Physical devices too | Needs Phase 8 configuration | |

**User's choice:** Android and iOS simulator

---

## Policy wiring & audit

| Option | Description | Selected |
|--------|-------------|----------|
| One central table | Single Python module laid out like the ADR | ✓ |
| ACCESS per module | Cells declared in each router | |
| Generic router factory | Replace 36 routers with one factory | |

**User's choice:** One central table

| Option | Description | Selected |
|--------|-------------|----------|
| Test parses the ADR | Assert every cell matches the Python table | ✓ |
| Runtime reads the ADR | API loads policy from markdown | |
| Manual review only | Hand-written tests for selected cells | |

**User's choice:** Test parses the ADR

| Option | Description | Selected |
|--------|-------------|----------|
| Always sub | One id space for every caller | ✓ |
| Participant if present, else sub | Matches owner for participant writes | |

**User's choice:** Always sub

---

## Claude's Discretion

Docs setting name, seed script location, the mobile gate's error, how deny-by-default attaches at the router, test-token mechanics, and where scope filtering lives.

## Deferred Ideas

Trusted-proxy `X-Forwarded-For` handling (Phase 12), redacted structured logging (backlog), `kid`/JWKS groundwork (Phase 3), real bootstrap CLI (Phase 11), physical-device UAT (after Phase 8).

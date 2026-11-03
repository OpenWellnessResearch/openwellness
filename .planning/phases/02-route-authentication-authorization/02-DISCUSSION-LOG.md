# Phase 2: Route Authentication & Authorization - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-03
**Phase:** 02-route-authentication-authorization
**Areas discussed:** Policy engine shape, Scope filtering for lists, Rollout and flag removal, First admin and bootstrap

---

## Policy engine shape

**Q1. Where should the deny-by-default 401 and the per-method policy check live?**

| Option | Description | Selected |
|--------|-------------|----------|
| One shared policy dependency, declared per route | `authorize(resource, method)` factory backed by one Python policy module; attached per route; enumeration test proves coverage | ✓ |
| Router-level gate plus per-route policy | v1.py adds an auth dependency per included router; policy declared separately | |
| Hand-written guards per router | Inline role and scope checks in each of 36 modules | |

**Q2. What is the runtime source of truth for the policy table?**

| Option | Description | Selected |
|--------|-------------|----------|
| Python policy module plus conformance test | Typed table in code; test parses ADR 0007 markdown and asserts cell-for-cell equality | ✓ |
| Parse the ADR markdown at import time | Runtime reads docs/adr/0007 | |
| Decorators on each route, ADR checked by review only | No central table | |

**Notes:** The user asked for a reminder of what ADR 0007 is and how the question relates before choosing; the explanation covered the 36-row table, scope predicates, write rules and denial codes.

**Q3. How does each route identify its resource and method?**

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit per route | `authorize("weight", "patch")` on every route | ✓ |
| Inferred from HTTP method and path | Derived from verb and path shape with overrides for custom methods | |
| You decide | Planner's choice | |

**Q4. Where do owner and study scope predicates run?**

| Option | Description | Selected |
|--------|-------------|----------|
| Role check in the dependency, scope check in the handler | Dependency returns the scope rule; handler applies `check_scope` after its fetch | ✓ |
| Everything in the dependency | Dependency fetches the record itself | |
| You decide | Planner's choice | |

---

## Scope filtering for lists

**Q1. Where does coach-study and self-owner filtering of list results happen?**

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory post-filter at the API layer for Phase 2 | Filter in Python before pagination and filter=; no adapter changes | ✓ |
| New port methods now | list-by-study-ids and membership queries in Couchbase and Mongo | |
| Hybrid | Port methods only where study_id queries already exist | |

**Q2. How are the membership-scoped lists served?**

| Option | Description | Selected |
|--------|-------------|----------|
| Post-filter existing owner-scoped lists, same as other rows | participant_ids and channels predicates in Python | ✓ |
| Dedicated membership port methods | list_by_member, list_by_channels | |
| Defer membership lists to Phase 6 | list returns 403 until sync phase | |

**Q3. How should filter= treat a clause on a scope field?**

| Option | Description | Selected |
|--------|-------------|----------|
| Reject with 400 | owner and study_id removed from allowed_fields | ✓ |
| Accept and intersect | AND with the scope rule | |
| Accept for admins only | Role-dependent allowed fields | |

**Q4. Where in the list pipeline does the scope filter sit, and does admin bypass it?**

| Option | Description | Selected |
|--------|-------------|----------|
| Scope filter first, then filter=, then paginate; admin passes everything | Stable page tokens; admin scope is a no-op | ✓ |
| Paginate first, then scope | Short pages, token leakage | |
| You decide | Planner's choice | |

---

## Rollout and flag removal

**Q1. How should enforcement land given no client calls a data route today?**

| Option | Description | Selected |
|--------|-------------|----------|
| Enforce directly, skip the logging pass | One change; delete enforce_principal | ✓ |
| Keep a temporary log-only toggle, remove it at phase end | API_AUTH_LOG_ONLY then delete | |
| Run the logging pass as a throwaway branch | Observe on an unmerged branch | |

**Q2. What happens to get_principal, require_principal and the X-Principal-Id header?**

| Option | Description | Selected |
|--------|-------------|----------|
| One strict dependency, header parameter deleted | `current_principal` raises 401; header never read | ✓ |
| Keep get_principal name, make it strict | Same behavior, no import change | |
| Keep the header, ignore it unless authenticated | Debug-only hook | |

**Notes:** The user asked for more on what a principal is; the explanation covered the dataclass, the two dependencies, the legacy header, and that `Principal.id` stays the token `sub` for audit stamping.

**Q3. How should tests authenticate?**

| Option | Description | Selected |
|--------|-------------|----------|
| Mint real tokens per role in conftest | Real token service, test secret, admin/coach/participant fixtures | ✓ |
| Override the principal dependency in tests | Canned Principal via dependency_overrides | |
| You decide | Planner's choice | |

**Q4. How should policy coverage be tested?**

| Option | Description | Selected |
|--------|-------------|----------|
| Generated matrix test from the policy module | Case per (resource, caller, method) plus the 401 route walk; per-resource fixture table | ✓ |
| Enumeration test plus hand-written tests for a sample of resources | Five representative resources | |
| You decide | Planner's choice | |

**Notes:** The user asked for more detail; the explanation contrasted the one-test 401 walk with the thousand-cell matrix, and the ~36-entry fixture table versus 5 representative resources.

---

## First admin and bootstrap

**Q1. How should staff login work, given login currently requires a participant id?**

| Option | Description | Selected |
|--------|-------------|----------|
| Login requires an active, verified user with at least one role | Drop the participant-id requirement; claims minted per role present | ✓ |
| Separate staff login endpoint | sendStaffLoginCode / verifyStaffLoginCode | |
| You decide | Planner's choice | |

**Q2. How is the first admin created?**

| Option | Description | Selected |
|--------|-------------|----------|
| Small CLI command in the api package | `python -m openwellness_api.bootstrap --email ...` through the UserRepository port | ✓ |
| Env var allowlist granted at login | API_AUTH_BOOTSTRAP_ADMIN_EMAILS | |
| Defer to Phase 10, edit the database by hand for now | Manual Mongo update | |

**Q3. How do admins assign a coach to studies?**

| Option | Description | Selected |
|--------|-------------|----------|
| PATCH /v1/users/{user} with roles, admin-only, roles stripped for everyone else | Existing route; schema refuses roles from non-admins | ✓ |
| Dedicated custom method users/{user}:setCoachStudies | Narrow admin verb | |
| You decide | Planner's choice | |

**Q4. How is AUTH-09 proven?**

| Option | Description | Selected |
|--------|-------------|----------|
| Automated API flow tests plus a manual UAT checkpoint for the real clients | Full flow over fakes; dashboard and mobile login recorded as UAT | ✓ |
| Add one data screen to each client in this phase | Participant list and weights screen | |
| Automated API tests only | Skip the manual run | |

---

## Claude's Discretion

- Module and function names for the policy module, strict dependency, scope helper and bootstrap CLI.
- Placement of the Fitbit token redaction.
- How the `self-study` predicate reads the Participant record per request.
- 403 envelope details; shape of the matrix fixture table; whether `coach_studies` is empty or absent for non-coaches.

## Deferred Ideas

- Port-level scope queries (Phase 4).
- Client data screens exercising bearer-carrying calls (mobile and dashboard phases).
- `users/{user}:setCoachStudies` custom method; separate staff login endpoint; log-only toggle (all rejected).
- Postgres row-level security (v2 AUTHZ-02).
- `X-Forwarded-For` trust and dashboard refresh token storage (deployment and dashboard phases).

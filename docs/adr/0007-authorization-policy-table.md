# 0007. Authorization policy table

- Status: Accepted
- Date: 2026-10-30
- Decisions: D-04, D-05, D-06, D-08
- Amended: 2026-10-30 at the phase 1 review: membership predicates for `conversation` and `participant_group`, and participant-self get on the participant's own `fitbit` (developer answers; legacy Sync Gateway routing recorded in ADR 0005)

## Context

Phase 2 enforces deny-by-default access on every `/v1` route, and Phase 6 sync streams must agree with it. Owner binding that checks only the token, not the relationship between caller and record, is the IDOR described in research Pitfall 2. This ADR is the one written policy both phases implement. It sets the answer per resource module and method (D-06), and for every allowed cell it names a scope predicate that can be computed from signed claims (ADR 0004 and 0006) plus stored record fields (ADR 0005). `RESOURCE_MODULES` has 36 modules, and each exposes the same seven standard operations: get, list, create, patch, delete (archive), undelete and purge. Two modules also expose a custom method, listed in the Custom methods table below.

## Decision

Denials (D-05):

- Anonymous gets 401.
- Authenticated but missing the role gets 403.
- Wrong owner, or a record or study outside the caller's scope, gets 404, so existence is not revealed.
- Deny by default: a method not listed in a cell is denied.

Scope rules:

- Scope (owner binding per ADR 0005, coach study filter per ADR 0006) is applied before any user-supplied filter= expression and can never be widened by it. This is the scope before filter= rule, and Phase 2 adds a hostile-filter test for it.
- The admin column is global (D-04). It needs only `roles` holding admin and uses no scope predicate. It is the only column that holds purge (D-08), the hard delete of research data.
- Purge is never granted to participant-self or coach. They may archive and undelete where their cell says so.

Rule table, used for every `users/{user}/...` row, `conversation` and `study_settings`. It maps the ADR 0005 data class to the participant-self and coach cells:

| Data class | participant-self | coach | admin |
| --- | --- | --- | --- |
| `participant-data` | get, list, create, patch, delete, undelete | get, list | all seven |
| `server-ingested` | get, list | get, list | all seven |
| `study-content` | get, list | get, list, create, patch, delete, undelete | all seven |
| `coach-authored` | get, list | get, list, create, patch, delete, undelete | all seven |

The self predicate for a row follows the `owner holds` value in ADR 0005: an owner holding a participant id uses `self-owner` (a user id would also use it, bound to sub), and an owner holding a study id (`study_settings`) uses `self-study`. Every coach cell uses `coach-study`.

Exception, membership rows. ADR 0005 marks `owner holds` as `not routing-relevant (membership)` for `conversation` and `participant_group`: they are multi-participant documents, and access is by membership, not by owner. Membership is stored: `ParticipantGroup.participant_ids` lists the member participant ids, and a conversation reaches its members through the group's routing channel `participantGroup:{group id}` in `Conversation.channels` (the legacy Sync Gateway rule, ADR 0005). So for these two rows only:

- participant-self is get, list (the `study-content` read cells), scoped by `self-member-group` on `participant_group` and `self-member-conversation` on `conversation`, never by owner. Participants do not create, patch, delete or undelete either row (developer decision 2026-10-30; participant writes go through `post`).
- The coach cell still follows `study-content`, scoped by the record's `study_id` alone. No owner is resolved, because the owner carries no meaning.

The rest of the rows are fixed (least privilege; an ADR amendment widens a cell when a client needs it):

- `admin`, `app`: participant-self none, coach none.
- `fitbit`: participant-self get on the participant's own row (`self-fitbit`; the mobile app reads it); coach none. Fitbit holds the account's OAuth `access_token` and `refresh_token`: every non-admin response returns both fields as null (the fields are already optional, so the /v1 shape is unchanged).
- `device`: participant-self get, list (`self-device`); coach none, because Device stores no study id.
- `study`: participant-self get (`self-study`); coach get, list (`coach-study`, studies in coach_studies).
- `user`: participant-self get (`self-user`); coach none.
- `participant`: participant-self get (`self-participant`); coach get, list, patch (`coach-study`, the {study} segment).
- `study_message`: participant-self get, list (`self-study`, the {study} segment); coach all six non-purge methods (`coach-study`).

## Scope predicates

Each predicate uses only the signed claims sub, participant, coach_studies and roles, plus at least one stored field. A caller missing the claim a predicate needs matches nothing (404).

| Predicate | Claims | Stored fields | Rule |
| --- | --- | --- | --- |
| `self-user` | sub | the {user} segment of `/v1/users/{user}` (User.id) | The {user} segment equals sub. |
| `self-owner` | sub, participant | record.owner; the {user} segment on users/{user}/... routes | record.owner equals the bound claim, the one matching the `owner holds` value of ADR 0005 (participant id binds participant, user id binds sub); list queries filter on owner. On users/{user}/... routes the {user} segment must also equal that claim. On a route with no {user} segment the record.owner rule alone applies. The membership rows conversation and participant_group are exempt (ADR 0005). Every create and patch on these rows also follows the `study-binding` write rule. |
| `self-participant` | participant | Participant.id | Participant.id equals the participant claim. |
| `self-study` | participant | Participant.study_id of the Participant record whose id is the participant claim; the target's study id (the {study} segment, Study.id, or the record's study binding) | The target study id equals that Participant.study_id. The server reads the Participant record on each request. There is no study claim (ADR 0004), so a participant moved to another study is re-scoped on the next request with no token staleness. A caller with no participant claim, no Participant record, an archived record or an empty study_id matches nothing (fail closed, 404). |
| `self-device` | participant | Device.participant_id | Device.participant_id equals the participant claim. |
| `self-fitbit` | participant | Fitbit.participant_id | Fitbit.participant_id equals the participant claim. |
| `self-member-group` | participant | ParticipantGroup.participant_ids; the {user} segment of `/v1/users/{user}/participantGroups` | The {user} segment equals the participant claim, and the group's participant_ids contains it; list returns exactly the groups whose participant_ids contains the claim, not the groups the segment owns. An archived group matches nothing. |
| `self-member-conversation` | participant | Conversation.channels; ParticipantGroup.participant_ids | Conversation.channels contains `participantGroup:{g.id}` for some non-archived group g whose participant_ids contains the participant claim; list filters on that set of channels. A conversation on no member group's channel matches nothing. |
| `coach-study` | roles, coach_studies | the record's study id (BaseOwnerEntity.study_id on owner-scoped rows; the {study} segment on studies/{study}/... rows, where the stored study binding must equal the segment as the routers already check; Study.id on the study row); record.owner; Participant.study_id | roles holds coach and that study id is in coach_studies; an empty study id never matches. Coach write check (D-02, closes the cross-study write): on owner-scoped rows whose owner holds a participant id (every users/{user}/... row except participant_group), every coach create, patch, delete and undelete also resolves record.owner (the {user} segment on create) to its Participant record and requires that Participant.study_id is in coach_studies; an owner with no Participant record, more than one, an archived one, or an empty study_id fails closed (404). On create, the `study-binding` write rule also sets study_id from the owner and refuses a differing supplied one. So a coach in study A cannot create or edit a record for a participant in study B, even by sending study_id A. conversation and participant_group have no owner to resolve; their record study_id alone must be in coach_studies, on create as supplied and on every other method as stored. |

Device stores no study id, so no coach predicate is computable for it and its coach cell is none. Widening it later needs an ADR amendment that records the derivation through Device.participant_id to Participant.study_id.

## Write rules

The `study-binding` write rule is caller-independent (D-02, AUTH-05). It closes the participant-self cross-study create as well as the coach one: create takes `study_id` from the request body and conversation create takes both owner and study_id from the body, so without it a participant in study B could file a record under study A that coach-study reads would then show to the coaches of A.

- Scope: every create and patch on an owner-scoped row, meaning every users/{user}/... row, conversation and study_settings (the BaseOwnerEntity rows), whichever column the caller is in: participant-self, coach or admin.
- Owner: the {user} segment on users/{user}/... creates, the {study} segment on study_settings creates, the request's owner value on segment-less creates, and record.owner on every other method.
- Owner's study, from the `owner holds` value ADR 0005 records for the entity: for a participant id, Participant.study_id of the Participant whose id equals the owner; for a user id, Participant.study_id of the single Participant whose user_id equals the owner; for a study id, the owner itself.
- Create: the server writes study_id from the owner's study and never takes it from the request body. A non-empty caller-supplied study_id that differs from it is refused with 404. An owner with more than one Participant, or an archived one, fails the create closed (404). An owner with no Participant record, or one with an empty study_id, also fails the create closed (404) for every caller (participant-self, coach and admin alike), so no owner-scoped record is ever written without a study; this does not arise where `owner holds` a study id, because the owner value is the study.
- Patch: owner and study_id are immutable for every caller, admin included, so no write moves a record into or out of a study.
- Exception, membership rows: for conversation and participant_group the owner holds nothing routing-relevant (ADR 0005), so there is no owner's study to derive. Only coach and admin can create them (participant-self is read-only). The supplied study_id must be non-empty, and for a coach it must be in coach_studies, else 404. owner and study_id are immutable on patch as everywhere else.
- Effect: a participant in study B cannot create a record carrying study_id A.

## Policy table

Cells are a comma-separated subset of get, list, create, patch, delete, undelete, purge, or none. The Scope column names the predicate behind each non-none participant-self and coach cell.

| Resource module | Route | Scope | anonymous | participant-self | coach (in-study) | admin |
| --- | --- | --- | --- | --- | --- | --- |
| `actigraph_record` | `/v1/users/{user}/actigraphRecords` | `self-owner`; `coach-study` | none | get, list | get, list | get, list, create, patch, delete, undelete, purge |
| `admin` | `/v1/admins` | none | none | none | none | get, list, create, patch, delete, undelete, purge |
| `app` | `/v1/apps` | none | none | none | none | get, list, create, patch, delete, undelete, purge |
| `asset` | `/v1/users/{user}/assets` | `self-owner`; `coach-study` | none | get, list, create, patch, delete, undelete | get, list | get, list, create, patch, delete, undelete, purge |
| `card` | `/v1/users/{user}/cards` | `self-owner`; `coach-study` | none | get, list, create, patch, delete, undelete | get, list | get, list, create, patch, delete, undelete, purge |
| `condition` | `/v1/users/{user}/conditions` | `self-owner`; `coach-study` | none | get, list | get, list, create, patch, delete, undelete | get, list, create, patch, delete, undelete, purge |
| `conversation` | `/v1/conversations` | `self-member-conversation`; `coach-study` | none | get, list | get, list, create, patch, delete, undelete | get, list, create, patch, delete, undelete, purge |
| `daily_state` | `/v1/users/{user}/dailyStates` | `self-owner`; `coach-study` | none | get, list, create, patch, delete, undelete | get, list | get, list, create, patch, delete, undelete, purge |
| `device` | `/v1/devices` | `self-device` | none | get, list | none | get, list, create, patch, delete, undelete, purge |
| `fitbit` | `/v1/fitbits` | `self-fitbit` | none | get | none | get, list, create, patch, delete, undelete, purge |
| `fitbit_heart_record` | `/v1/users/{user}/fitbitHeartRecords` | `self-owner`; `coach-study` | none | get, list | get, list | get, list, create, patch, delete, undelete, purge |
| `fitbit_record` | `/v1/users/{user}/fitbitRecords` | `self-owner`; `coach-study` | none | get, list | get, list | get, list, create, patch, delete, undelete, purge |
| `fitbit_sleep` | `/v1/users/{user}/fitbitSleeps` | `self-owner`; `coach-study` | none | get, list | get, list | get, list, create, patch, delete, undelete, purge |
| `fitbit_sleep_session` | `/v1/users/{user}/fitbitSleepSessions` | `self-owner`; `coach-study` | none | get, list | get, list | get, list, create, patch, delete, undelete, purge |
| `fitbit_weight` | `/v1/users/{user}/fitbitWeights` | `self-owner`; `coach-study` | none | get, list | get, list | get, list, create, patch, delete, undelete, purge |
| `goal` | `/v1/users/{user}/goals` | `self-owner`; `coach-study` | none | get, list, create, patch, delete, undelete | get, list | get, list, create, patch, delete, undelete, purge |
| `job_rule` | `/v1/users/{user}/jobRules` | `self-owner`; `coach-study` | none | get, list | get, list, create, patch, delete, undelete | get, list, create, patch, delete, undelete, purge |
| `message` | `/v1/users/{user}/messages` | `self-owner`; `coach-study` | none | get, list | get, list, create, patch, delete, undelete | get, list, create, patch, delete, undelete, purge |
| `message_draft` | `/v1/users/{user}/messageDrafts` | `self-owner`; `coach-study` | none | get, list | get, list, create, patch, delete, undelete | get, list, create, patch, delete, undelete, purge |
| `meta_data` | `/v1/users/{user}/metaData` | `self-owner`; `coach-study` | none | get, list, create, patch, delete, undelete | get, list | get, list, create, patch, delete, undelete, purge |
| `participant` | `/v1/studies/{study}/participants` | `self-participant`; `coach-study` | none | get | get, list, patch | get, list, create, patch, delete, undelete, purge |
| `participant_group` | `/v1/users/{user}/participantGroups` | `self-member-group`; `coach-study` | none | get, list | get, list, create, patch, delete, undelete | get, list, create, patch, delete, undelete, purge |
| `physical_activity` | `/v1/users/{user}/physicalActivities` | `self-owner`; `coach-study` | none | get, list, create, patch, delete, undelete | get, list | get, list, create, patch, delete, undelete, purge |
| `post` | `/v1/users/{user}/posts` | `self-owner`; `coach-study` | none | get, list, create, patch, delete, undelete | get, list | get, list, create, patch, delete, undelete, purge |
| `session` | `/v1/users/{user}/sessions` | `self-owner`; `coach-study` | none | get, list, create, patch, delete, undelete | get, list | get, list, create, patch, delete, undelete, purge |
| `shared_goal_progress` | `/v1/users/{user}/sharedGoalProgress` | `self-owner`; `coach-study` | none | get, list | get, list | get, list, create, patch, delete, undelete, purge |
| `study` | `/v1/studies` | `self-study`; `coach-study` | none | get | get, list | get, list, create, patch, delete, undelete, purge |
| `study_message` | `/v1/studies/{study}/studyMessages` | `self-study`; `coach-study` | none | get, list | get, list, create, patch, delete, undelete | get, list, create, patch, delete, undelete, purge |
| `study_settings` | `/v1/studies/{study}/studySettings` | `self-study`; `coach-study` | none | get, list | get, list, create, patch, delete, undelete | get, list, create, patch, delete, undelete, purge |
| `survey_result` | `/v1/users/{user}/surveyResults` | `self-owner`; `coach-study` | none | get, list, create, patch, delete, undelete | get, list | get, list, create, patch, delete, undelete, purge |
| `user` | `/v1/users` | `self-user` | none | get | none | get, list, create, patch, delete, undelete, purge |
| `user_food` | `/v1/users/{user}/userFoods` | `self-owner`; `coach-study` | none | get, list, create, patch, delete, undelete | get, list | get, list, create, patch, delete, undelete, purge |
| `user_settings` | `/v1/users/{user}/userSettings` | `self-owner`; `coach-study` | none | get, list | get, list, create, patch, delete, undelete | get, list, create, patch, delete, undelete, purge |
| `user_sleep` | `/v1/users/{user}/userSleeps` | `self-owner`; `coach-study` | none | get, list, create, patch, delete, undelete | get, list | get, list, create, patch, delete, undelete, purge |
| `user_stress` | `/v1/users/{user}/userStresses` | `self-owner`; `coach-study` | none | get, list, create, patch, delete, undelete | get, list | get, list, create, patch, delete, undelete, purge |
| `weight` | `/v1/users/{user}/weights` | `self-owner`; `coach-study` | none | get, list, create, patch, delete, undelete | get, list | get, list, create, patch, delete, undelete, purge |

## Custom methods

Two live routes sit outside the seven standard operations and have their own cells. The route-enumeration test treats them as policy rows too, so a route with no cell here or in the Policy table is denied (deny by default).

| Method | Route | Scope | anonymous | participant-self | coach (in-study) | admin |
| --- | --- | --- | --- | --- | --- | --- |
| `study:lookup` | `POST /v1/studies:lookup` | `self-study`; `coach-study` | none | lookup | lookup | lookup |
| `conversation:search` | `POST /v1/conversations:search` | `self-member-conversation`; `coach-study` | none | search | search | search |

- `study:lookup` finds a study by name. A study outside the caller's scope answers 404, the same as a missing name, so existence is not revealed.
- `conversation:search` takes caller-chosen `channels`, `kind` and `week` filters. The scope predicate (membership for participant-self, `coach-study` for coach) is applied to the candidate set before those filters, so a filter can never widen the result to conversations the caller cannot get. The Phase 2 hostile-filter test covers this route as well.
- Phase 2 adds a test that diffs the live app routes against the Policy and Custom methods tables, so a new route cannot ship without a cell.

## Unauthenticated endpoints

| Endpoint | Why anonymous |
| --- | --- |
| `/v1/auth:*` | Login, refresh and logout are how a token is obtained; responses are anti-enumeration. |
| `/healthz` | Liveness probe; returns no data. |

These are the only anonymous surface. Every other `/v1` route answers 401 without a verified token.

## Consequences

- The Phase 2 route-enumeration 401 test checks this table, and the Phase 2 policy tests are generated from the Policy table rows. Phase 6 stream predicates must agree with the participant-self and coach columns.
- Mass-assignment caveat (Phase 2 field allowlist): neither self patch nor coach patch may change owner, study_id, user_id, roles or audit fields on any row, so no write moves a record, or a Participant, into or out of a study the caller holds.
- Owner-scoped data cannot be written for an owner until that owner is assigned to a study (decided by the developer at planning time, 2026-10-30).
- participant-self reads `conversation` and `participant_group` by membership (`self-member-conversation`, `self-member-group`). Phase 6 streams for these rows must key on the same membership, not on owner.
- `fitbit` OAuth tokens never leave the server for a non-admin caller; the Phase 2 response filter nulls `access_token` and `refresh_token`.
- POST /v1/users answers a duplicate email with 409 ALREADY_EXISTS (plan 01-05), which tells the caller that the email is registered. The user row grants create to admin only, so after Phase 2 only admins see it. Before Phase 2 every /v1 route is anonymous; that window is a known, accepted gap, and no production deployment docs ship before route auth (PROJECT.md constraint).
- Costly to reverse: Phase 2 route guards and tests, plus the Phase 6 stream policy, encode every cell, so changing one later is a coordinated code and test change, not a migration.

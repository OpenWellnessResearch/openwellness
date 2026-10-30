# 0005. Owner semantics

- Status: Accepted
- Date: 2026-10-30
- Decisions: D-01
- Confirmed: 2026-10-30 at the phase 1 checkpoint (option-participant)

## Context

Every record that extends `BaseOwnerEntity` carries an `owner` string. The API stamps it from the `{user}` path segment on `users/{user}/...` routes and later filters and 404s on it. Phase 2 binds a token claim to that segment, and Phase 6 sync-stream predicates key on the same column. Two id spaces exist in the system: `User.id` (the token `sub`) and `Participant.id` (the token `participant` claim, minted from `roles.participant.pid`). The path segment is named `users/{user}`, which suggests a user id, but the domain docstring and the server-side ingestion code suggest a participant id.

This is a one-way door. Once Postgres rows (Phases 4 and 5) and PowerSync stream predicates (Phase 6) key on `owner`, changing it needs a data migration of every owner-scoped row plus a stream rewrite. A wrong binding in Phase 2 is an IDOR on participant health data.

## Evidence

- `backend/core/src/openwellness_core/adapters/mongo/model/mongo_base_owner_entity.py:3` says the Mongo owner base is unused: every `BaseOwnerEntity` subclass persists to Couchbase. Reading: no second store can disagree about `owner`.
- `backend/core/src/openwellness_core/domain/models/base_owner_entity.py:16` says the base is for "entities owned by a participant within a study". Reading: the intended owner is a participant.
- `backend/core/src/openwellness_core/domain/models/base_owner_entity.py:33` defaults `updated_by` to `owner`. Reading: `updated_by` is a person-like id, so the owner is the acting person for self-written records.
- `backend/core/src/openwellness_core/adapters/couchbase/repositories/cb_fitbit_record_repository.py:36` builds a server-ingested record with `owner=pid`, where `pid` is the argument of `create_from_notification(pid, ...)` at line 28. Reading: the only place in the code base that assigns `owner` without a URL is a participant id.
- `backend/core/src/openwellness_core/domain/models/fitbit_sleep_session.py:51` builds `self.id = f"{self.owner}-{self.log_id}"`. Reading: the id embeds the owner, which only makes sense for a stable participant-level key.
- `backend/api/src/openwellness_api/auth/service.py:153` (`_participant_pid`) reads `roles.participant.pid`; `backend/api/src/openwellness_api/auth/token_service.py:78` mints it as the `participant` claim, separate from `sub`. Reading: the token carries both ids, so Phase 2 can bind either.
- `backend/api/src/openwellness_api/common/handlers.py:136` stamps `payload[parent_field] = parent_id` from the path, and `:155` compares `getattr(entity, parent_field)` with the path id (404 on mismatch). Reading: the API copies the `{user}` segment verbatim into `owner`; nothing translates a user id to a participant id.
- `backend/api/src/openwellness_api/resources/weight.py:51` and `:64` apply that pattern to `users/{user}/weights`, the reference for the other owner-scoped routers. Reading: whatever the client puts in `{user}` becomes `owner`, so legacy clients must already send the participant id for the data to line up with ingestion.
- `backend/api/tests/test_weights_owner_crud.py:16` asserts `owner == "user-1"` after creating under `/v1/users/user-1/weights`. Reading: a permissive-mode fixture; it only proves the copy rule, not which id space production uses.
- `backend/core/tests/test_smoke.py:72` and `:82` build owner-scoped entities with `owner="p1"`. Reading: the fixtures name the owner like a participant ("p"), not a user.
- `backend/core/src/openwellness_core/domain/models/fitbit.py:14` and `:17` hold `participant_id` and a separate `owner_id`; `backend/core/src/openwellness_core/domain/models/device.py:15` holds `participant_id`; `backend/core/src/openwellness_core/domain/models/participant.py:28` holds `user_id`. Reading: where the code needs the user it spells it out as `user_id`, so a bare `owner` is the other id.
- `backend/api/src/openwellness_api/resources/study_settings.py:51` and `:62` call `check_parent(entity, parent_id=study, ...)` and `stamp_audit(..., parent_id=study, ...)` with the default `parent_field="owner"`. Reading: `StudySettings.owner` holds a study id, not a person. This is the one code-confirmed per-entity exception.
- `backend/core/tests/test_repositories_queries.py:282` and `:350` only assert that `owner` is passed as a query parameter. Reading: no test pins the id space.
- Developer testimony about the legacy Couchbase deployment (phase 1 checkpoint, 2026-10-30), which supplies the data-level confirmation the code could not: "when couchbase was used, 'owner' was typically equivalent to the participant id. this made routing the document via sync gateway easier because the sync function always assigned the document to the 'owner' channel. conversation and participant group were different, since the same document could be synced to 2 or more participants. for those document types, owner didn't really matter". Reading: `owner` is the participant id and was the Sync Gateway channel key (owner to channel); `conversation` and `participant_group` are multi-participant documents where `owner` carries no routing meaning.

No sample of real legacy Couchbase documents was inspected. The testimony above is the data-level confirmation; the code and tests are consistent with it.

## Decision

`owner` holds the participant id (`Participant.id`). This is derived from the legacy Sync Gateway channel rule (`owner` to channel), under which a document synced to the participant whose id it carried. It is decided for every record in the classification table below, with these exceptions:

- `study_settings`: `owner` holds a study id.
- `conversation` and `participant_group`: multi-participant documents, synced to two or more participants. `owner` is not meaningful for routing; access is by membership, not by `owner`.

Binding rules:

- On `users/{user}/...` routes, Phase 2 requires the `{user}` segment to equal the token `participant` claim. A token without a `participant` claim (a coach or admin acting for themselves) gets no self access to these routes; access for other roles comes from ADR 0007.
- On the top-level `users/{user}` resource (the `User` entity, keyed by user id), `{user}` binds to the token `sub`.
- The AIP path stays as is. The `/v1` wire contract is frozen, so the same `users/{user}` segment carries a participant id on owner-scoped sub-resources and a user id on the User resource. This is documented here, not fixed.
- Phase 6 predicate: a stream row is visible when `owner` equals the `participant` claim of the PowerSync token. This predicate applies to the single-participant rows only; it must not be applied to `conversation` or `participant_group`.
- `study_settings` is exempt from the participant binding. Its `owner` is the `{study}` path segment, and ADR 0007 scopes it by study, not by participant.
- `conversation` and `participant_group` are exempt from the owner binding and from the owner-keyed Phase 6 predicate. Their access rule is membership-based and is not decided here (see Consequences).

## Entity classification

Data classes: `participant-data` (records participants create about themselves), `server-ingested` (written by server integrations such as Fitbit and ActiGraph, read-only to clients), `study-content` (authored by study staff for a study's participants), `coach-authored` (per-participant records coaches write). ADR 0007 derives each row's self-scope predicate from `owner holds`. One row per module whose router prefix starts with `/users/{user}/`, plus conversation and study_settings. The `owner holds` value `not routing-relevant (membership)` marks the two multi-participant types.

| Resource module | Domain class | owner holds | Data class | Evidence |
| --- | --- | --- | --- | --- |
| `actigraph_record` | `ActigraphRecord` | participant id | server-ingested | `domain/models/actigraph_record.py:11` "Activity data from an Actigraph device" |
| `asset` | `Asset` | participant id | participant-data | `domain/models/asset.py:14`; accepted as drafted |
| `card` | `Card` | participant id | participant-data | `domain/models/card.py:14`; accepted as drafted |
| `condition` | `Condition` | participant id | coach-authored | `domain/models/condition/base.py:9` "Study-specific conditions of a participant"; accepted as drafted |
| `conversation` | `Conversation` | not routing-relevant (membership) | study-content | `domain/models/conversation.py:16` "collection of shared Posts"; developer testimony: multi-participant, synced to 2+ participants, owner did not matter |
| `daily_state` | `DailyState` | participant id | participant-data | `cb_daily_state_repository.py:50` owner-scoped date query |
| `fitbit_heart_record` | `FitbitHeartRecord` | participant id | server-ingested | `cb_fitbit_heart_record_repository.py:78` owner query; Fitbit integration |
| `fitbit_record` | `FitbitRecord` | participant id | server-ingested | `cb_fitbit_record_repository.py:36` `owner=pid` |
| `fitbit_sleep` | `FitbitSleep` | participant id | server-ingested | `cb_fitbit_sleep_repository.py:77` owner query; Fitbit integration |
| `fitbit_sleep_session` | `FitbitSleepSession` | participant id | server-ingested | `domain/models/fitbit_sleep_session.py:51` id built from owner |
| `fitbit_weight` | `FitbitWeight` | participant id | server-ingested | `cb_fitbit_weight_repository.py:40` owner query; Fitbit integration |
| `goal` | `Goal` | participant id | participant-data | `domain/models/goal/base.py:10`; accepted as drafted |
| `job_rule` | `JobRule` | participant id | coach-authored | `domain/models/job_rule.py:11` "Constraints for scheduling a job"; accepted as drafted |
| `message` | `Message` | participant id | coach-authored | `domain/models/message.py:14` "push notification that was sent to a participant"; accepted as drafted |
| `message_draft` | `MessageDraft` | participant id | coach-authored | `domain/models/message_draft.py:10` "Basis of a push notification"; accepted as drafted |
| `meta_data` | `MetaData` | participant id | participant-data | `domain/models/meta_data.py:10` "Study-specific metadata for a related document"; accepted as drafted |
| `participant_group` | `ParticipantGroup` | not routing-relevant (membership) | study-content | `cb_participant_group_repository.py:41` owner passed in by caller; developer testimony: multi-participant, owner did not matter |
| `physical_activity` | `PhysicalActivity` | participant id | participant-data | `cb_physical_activity_repository.py:39` owner query |
| `post` | `Post` | participant id | participant-data | `domain/models/post.py:10` "message shared among 2 or more users"; accepted as drafted |
| `session` | `Session` | participant id | participant-data | `cb_session_repository.py:77` owner clause |
| `shared_goal_progress` | `SharedGoalProgress` | participant id | server-ingested | `cb_shared_goal_progress_repository.py:35` created with `owner`, `study_id` by caller; accepted as drafted |
| `study_settings` | `StudySettings` | study id | study-content | `resources/study_settings.py:51` and `:62` stamp and check `owner` against `{study}` |
| `survey_result` | `SurveyResult` | participant id | participant-data | `cb_survey_result_repository.py:74` owner query |
| `user_food` | `UserFood` | participant id | participant-data | `cb_user_food_repository.py:43` owner query |
| `user_settings` | `UserSettings` | participant id | coach-authored | `domain/models/user_settings.py:13` "Settings for a study participant"; accepted as drafted |
| `user_sleep` | `UserSleep` | participant id | participant-data | `cb_user_sleep_repository.py:37` owner query |
| `user_stress` | `UserStress` | participant id | participant-data | `cb_user_stress_repository.py:38` owner query |
| `weight` | `Weight` | participant id | participant-data | `resources/weight.py:51` and `:64` owner-scoped reference router |

## Consequences

- Phase 2 binds the `participant` claim to `{user}` on `users/{user}/...` and `sub` on `users/{user}`. The two bindings must be separate dependencies, so neither can be applied to the wrong route family by assumption.
- Phase 4 and 5 schemas store `owner` as the participant id (a text or uuid key per ADR 0001), and `study_settings` stores a study id in that column or, better, a `study_id` column.
- Phase 6 stream predicates compare `owner` with the `participant` claim of the PowerSync token for the single-participant rows.
- Open point for Phase 6 (not decided here): `conversation` and `participant_group` are multi-participant documents, so Phase 6 must not key their streams on `owner`. They need a membership-based rule (for example, a stream keyed on a membership table or member-id list). Phase 2 and ADR 0007 must likewise not apply the owner binding to these two types.
- The `users/{user}` name stays misleading on owner-scoped routes. API docs must say that the segment holds a participant id there.
- If a data sample later shows user ids for some entities, those entities become documented exceptions in a superseding ADR before any Postgres row is written.
- Rows marked `accepted as drafted` were classified from code evidence and were not corrected by the developer at the checkpoint; ADR 0007 inherits the table as confirmed.

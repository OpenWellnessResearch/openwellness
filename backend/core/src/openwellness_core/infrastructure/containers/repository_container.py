"""Repository providers wired against the canonical drivers.

Each provider follows the underlying adapter ``__init__`` signature exactly
— including the per-adapter quirks where the driver kwarg is variously
named ``repo``, ``mongo_repo`` or ``db``, and where a handful of repos
hard-code the entity class instead of accepting ``entity_type=``.
"""

from ...adapters.couchbase.repositories.cb_actigraph_record_repository import (
    CBActigraphRecordRepository,
)
from ...adapters.couchbase.repositories.cb_asset_repository import (
    CBAssetRepository,
)
from ...adapters.couchbase.repositories.cb_card_repository import (
    CBCardRepository,
)
from ...adapters.couchbase.repositories.cb_condition_repository import (
    CBConditionRepository,
)
from ...adapters.couchbase.repositories.cb_conversation_repository import (
    CBConversationRepository,
)
from ...adapters.couchbase.repositories.cb_daily_state_repository import (
    CBDailyStateRepository,
)
from ...adapters.couchbase.repositories.cb_fitbit_heart_record_repository import (
    CBFitbitHeartRecordRepository,
)
from ...adapters.couchbase.repositories.cb_fitbit_record_repository import (
    CBFitbitRecordRepository,
)
from ...adapters.couchbase.repositories.cb_fitbit_sleep_repository import (
    CBFitbitSleepRepository,
)
from ...adapters.couchbase.repositories.cb_fitbit_sleep_session_repository import (
    CBFitbitSleepSessionRepository,
)
from ...adapters.couchbase.repositories.cb_fitbit_weight_repository import (
    CBFitbitWeightRepository,
)
from ...adapters.couchbase.repositories.cb_goal_repository import (
    CBGoalRepository,
)
from ...adapters.couchbase.repositories.cb_job_rule_repository import (
    CBJobRuleRepository,
)
from ...adapters.couchbase.repositories.cb_message_draft_repository import (
    CBMessageDraftRepository,
)
from ...adapters.couchbase.repositories.cb_message_repository import (
    CBMessageRepository,
)
from ...adapters.couchbase.repositories.cb_meta_data_repository import (
    CBMetaDataRepository,
)
from ...adapters.couchbase.repositories.cb_participant_group_repository import (
    CBParticipantGroupRepository,
)
from ...adapters.couchbase.repositories.cb_physical_activity_repository import (
    CBPhysicalActivityRepository,
)
from ...adapters.couchbase.repositories.cb_post_repository import (
    CBPostRepository,
)
from ...adapters.couchbase.repositories.cb_session_repository import (
    CBSessionRepository,
)
from ...adapters.couchbase.repositories.cb_shared_goal_progress_repository import (
    CBSharedGoalProgressRepository,
)
from ...adapters.couchbase.repositories.cb_study_settings_repository import (
    CBStudySettingsRepository,
)
from ...adapters.couchbase.repositories.cb_survey_result_repository import (
    CBSurveyResultRepository,
)
from ...adapters.couchbase.repositories.cb_user_food_repository import (
    CBUserFoodRepository,
)
from ...adapters.couchbase.repositories.cb_user_settings_repository import (
    CBUserSettingsRepository,
)
from ...adapters.couchbase.repositories.cb_user_sleep_repository import (
    CBUserSleepRepository,
)
from ...adapters.couchbase.repositories.cb_user_stress_repository import (
    CBUserStressRepository,
)
from ...adapters.couchbase.repositories.cb_weight_repository import (
    CBWeightRepository,
)
from ...adapters.mongo.repositories.mongo_admin_repository import (
    MongoAdminRepository,
)
from ...adapters.mongo.repositories.mongo_app_repository import (
    MongoAppRepository,
)
from ...adapters.mongo.repositories.mongo_device_repository import (
    MongoDeviceRepository,
)
from ...adapters.mongo.repositories.mongo_fitbit_repository import (
    MongoFitbitRepository,
)
from ...adapters.mongo.repositories.mongo_participant_repository import (
    MongoParticipantRepository,
)
from ...adapters.mongo.repositories.mongo_study_message_repository import (
    MongoStudyMessageRepository,
)
from ...adapters.mongo.repositories.mongo_study_repository import (
    MongoStudyRepository,
)
from ...adapters.mongo.repositories.mongo_user_repository import (
    MongoUserRepository,
)
from ..config.app_config import AppConfigInterface
from ..drivers.cb_entity_repository import CBEntityRepository
from ..drivers.mdb_collection_repository import MDBCollectionRepository
from .entity_container import EntityContainer
from .providers import (
    DeclarativeContainer,
    DIContainer,
    DIDependency,
    DIFactory,
)


class RepositoryContainer(DeclarativeContainer):
    """Per-interface adapter providers."""

    app_config = DIDependency(instance_of=AppConfigInterface)
    entities = DIContainer(EntityContainer)

    # Drivers. ``CBEntityRepository.__new__`` enforces single-instance, so
    # using ``DIFactory`` here is still effectively singleton.
    entity_repository = DIFactory(CBEntityRepository, config=app_config)
    collection_repository = DIFactory(MDBCollectionRepository, config=app_config)

    # Couchbase-backed repositories
    actigraph_record = DIFactory(
        CBActigraphRecordRepository,
        repo=entity_repository,
        entity_type=entities.actigraph_record,
    )
    asset = DIFactory(
        CBAssetRepository,
        repo=entity_repository,
        entity_type=entities.asset,
    )
    card = DIFactory(
        CBCardRepository,
        repo=entity_repository,
        entity_type=entities.card,
    )
    condition = DIFactory(
        CBConditionRepository,
        repo=entity_repository,
        entity_type=entities.condition,
    )
    conversation = DIFactory(
        CBConversationRepository,
        repo=entity_repository,
        entity_type=entities.conversation,
    )
    daily_state = DIFactory(
        CBDailyStateRepository,
        repo=entity_repository,
        entity_type=entities.daily_state,
    )
    fitbit_heart_record = DIFactory(
        CBFitbitHeartRecordRepository,
        repo=entity_repository,
        entity_type=entities.fitbit_heart_record,
    )
    fitbit_record = DIFactory(
        CBFitbitRecordRepository,
        repo=entity_repository,
        entity_type=entities.fitbit_record,
    )
    fitbit_sleep = DIFactory(
        CBFitbitSleepRepository,
        repo=entity_repository,
        entity_type=entities.fitbit_sleep,
    )
    fitbit_sleep_session = DIFactory(
        CBFitbitSleepSessionRepository,
        repo=entity_repository,
        entity_type=entities.fitbit_sleep_session,
    )
    fitbit_weight = DIFactory(
        CBFitbitWeightRepository,
        repo=entity_repository,
        entity_type=entities.fitbit_weight,
    )
    goal = DIFactory(
        CBGoalRepository,
        repo=entity_repository,
        entity_type=entities.goal,
    )
    job_rule = DIFactory(
        CBJobRuleRepository,
        repo=entity_repository,
        entity_type=entities.job_rule,
    )
    # MessageDraft adapter hard-codes the entity (no ``entity_type`` kwarg).
    message_draft = DIFactory(
        CBMessageDraftRepository,
        repo=entity_repository,
    )
    message = DIFactory(
        CBMessageRepository,
        repo=entity_repository,
        entity_type=entities.message,
    )
    meta_data = DIFactory(
        CBMetaDataRepository,
        repo=entity_repository,
        entity_type=entities.meta_data,
    )
    participant_group = DIFactory(
        CBParticipantGroupRepository,
        repo=entity_repository,
        entity_type=entities.participant_group,
    )
    # PhysicalActivity adapter hard-codes the entity (no ``entity_type`` kwarg).
    physical_activity = DIFactory(
        CBPhysicalActivityRepository,
        repo=entity_repository,
    )
    post = DIFactory(
        CBPostRepository,
        repo=entity_repository,
        entity_type=entities.post,
    )
    session = DIFactory(
        CBSessionRepository,
        repo=entity_repository,
        entity_type=entities.session,
    )
    shared_goal_progress = DIFactory(
        CBSharedGoalProgressRepository,
        repo=entity_repository,
        entity_type=entities.shared_goal_progress,
    )
    study_settings = DIFactory(
        CBStudySettingsRepository,
        repo=entity_repository,
        entity_type=entities.study_settings,
    )
    survey_result = DIFactory(
        CBSurveyResultRepository,
        repo=entity_repository,
        entity_type=entities.survey_result,
    )
    user_food = DIFactory(
        CBUserFoodRepository,
        repo=entity_repository,
        entity_type=entities.user_food,
    )
    user_settings = DIFactory(
        CBUserSettingsRepository,
        repo=entity_repository,
        entity_type=entities.user_settings,
    )
    user_sleep = DIFactory(
        CBUserSleepRepository,
        repo=entity_repository,
        entity_type=entities.user_sleep,
    )
    user_stress = DIFactory(
        CBUserStressRepository,
        repo=entity_repository,
        entity_type=entities.user_stress,
    )
    weight = DIFactory(
        CBWeightRepository,
        repo=entity_repository,
        entity_type=entities.weight,
    )

    # Mongo-backed repositories
    # Admin adapter accepts ``db=`` and hard-codes the entity.
    admin = DIFactory(
        MongoAdminRepository,
        db=collection_repository,
    )
    # App adapter accepts ``mongo_repo=`` and hard-codes the entity.
    app = DIFactory(
        MongoAppRepository,
        mongo_repo=collection_repository,
    )
    device = DIFactory(
        MongoDeviceRepository,
        mongo_repo=collection_repository,
        entity_type=entities.device,
    )
    fitbit = DIFactory(
        MongoFitbitRepository,
        mongo_repo=collection_repository,
        entity_type=entities.fitbit,
    )
    participant = DIFactory(
        MongoParticipantRepository,
        mongo_repo=collection_repository,
        entity_type=entities.participant,
    )
    study_message = DIFactory(
        MongoStudyMessageRepository,
        mongo_repo=collection_repository,
        entity_type=entities.study_message,
    )
    # Study adapter accepts ``mongo_repo=`` and hard-codes the entity.
    study = DIFactory(
        MongoStudyRepository,
        mongo_repo=collection_repository,
    )
    # User adapter accepts ``repo=`` (not ``mongo_repo=``).
    user = DIFactory(
        MongoUserRepository,
        repo=collection_repository,
        entity_type=entities.user,
    )

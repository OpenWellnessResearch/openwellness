"""Domain-entity providers.

One ``DIObject`` per domain class used as a default ``entity_type=`` in an
adapter ``__init__``. Per-study customizations override the entity here
(e.g. ``container.entities.job_rule.override(DIObject(F4TJobRule))``)
without redeclaring the repository graph.
"""

from ...domain.models.actigraph_record import ActigraphRecord
from ...domain.models.asset import Asset
from ...domain.models.card import Card
from ...domain.models.condition import Condition
from ...domain.models.conversation import Conversation
from ...domain.models.daily_state import DailyState
from ...domain.models.device import Device
from ...domain.models.fitbit import Fitbit
from ...domain.models.fitbit_heart_record import FitbitHeartRecord
from ...domain.models.fitbit_record import FitbitRecord
from ...domain.models.fitbit_sleep import FitbitSleep
from ...domain.models.fitbit_sleep_session import FitbitSleepSession
from ...domain.models.fitbit_weight import FitbitWeight
from ...domain.models.goal import Goal
from ...domain.models.job_rule import JobRule
from ...domain.models.message import Message
from ...domain.models.meta_data import MetaData
from ...domain.models.participant import Participant
from ...domain.models.participant_group import ParticipantGroup
from ...domain.models.post import Post
from ...domain.models.session import Session
from ...domain.models.shared_goal_progress import SharedGoalProgress
from ...domain.models.study_message import StudyMessage
from ...domain.models.study_settings import StudySettings
from ...domain.models.survey_result import SurveyResult
from ...domain.models.user import User
from ...domain.models.user_food import UserFood
from ...domain.models.user_settings import UserSettings
from ...domain.models.user_sleep import UserSleep
from ...domain.models.user_stress import UserStress
from ...domain.models.weight import Weight
from .providers import DeclarativeContainer, DIObject


class EntityContainer(DeclarativeContainer):
    """Per-domain ``DIObject`` providers consumed by ``RepositoryContainer``."""

    # Couchbase-backed entities
    actigraph_record = DIObject(ActigraphRecord)
    asset = DIObject(Asset)
    card = DIObject(Card)
    condition = DIObject(Condition)
    conversation = DIObject(Conversation)
    daily_state = DIObject(DailyState)
    fitbit_heart_record = DIObject(FitbitHeartRecord)
    fitbit_record = DIObject(FitbitRecord)
    fitbit_sleep = DIObject(FitbitSleep)
    fitbit_sleep_session = DIObject(FitbitSleepSession)
    fitbit_weight = DIObject(FitbitWeight)
    goal = DIObject(Goal)
    job_rule = DIObject(JobRule)
    message = DIObject(Message)
    meta_data = DIObject(MetaData)
    participant_group = DIObject(ParticipantGroup)
    post = DIObject(Post)
    session = DIObject(Session)
    shared_goal_progress = DIObject(SharedGoalProgress)
    study_settings = DIObject(StudySettings)
    survey_result = DIObject(SurveyResult)
    user_food = DIObject(UserFood)
    user_settings = DIObject(UserSettings)
    user_sleep = DIObject(UserSleep)
    user_stress = DIObject(UserStress)
    weight = DIObject(Weight)

    # Mongo-backed entities
    device = DIObject(Device)
    fitbit = DIObject(Fitbit)
    participant = DIObject(Participant)
    study_message = DIObject(StudyMessage)
    user = DIObject(User)

"""In-memory fakes + dependency overrides for the API tests.

The aim is to exercise the routers and the factories without hitting
Couchbase or Mongo. Each fake repo implements just enough of the public
methods that the API surface calls into.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

# Tests must never read a developer's real `.env` (it may point at live datastores).
os.environ["OPENWELLNESS_ENV_FILE"] = os.devnull
# Ensure config loads with safe defaults before the app imports.
os.environ.setdefault("COUCHBASE_URL", "couchbase://stub")
os.environ.setdefault("MONGO_URL", "mongodb://stub")
# Safe ≥32-char auth secrets so any accidental real-lifespan import (boot guard)
# passes; the test app fixture builds its own AuthContainer regardless.
os.environ.setdefault("API_AUTH_JWT_SECRET", "test-secret-" * 4)
os.environ.setdefault("API_AUTH_CODE_PEPPER", "test-pepper-" * 4)

import pytest
from dependency_injector import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openwellness_core.application.repositories import (
    ConditionRepository,
    ConversationRepository,
    GoalRepository,
    MessageRepository,
    ParticipantRepository,
    StudyRepository,
    UserRepository,
    WeightRepository,
)
from openwellness_core.domain.exceptions.domain_exception import (
    EntityNotFoundException,
)
from openwellness_core.domain.models.conversation import Conversation
from openwellness_core.domain.models.participant import Participant
from openwellness_core.domain.models.study import Study
from openwellness_core.domain.models.user import User


class InMemoryBaseRepo:
    """Dict-backed implementation of ``BaseCrudRepository``."""

    def __init__(self) -> None:
        self.store: dict[str, Any] = {}
        self.archived: dict[str, Any] = {}

    def create(self, entity: Any) -> Any:
        if not getattr(entity, "id", None):
            entity.id = str(uuid4())
        self.store[entity.id] = entity
        return entity

    def get_by_id(self, entity_id: str) -> Any | None:
        return self.store.get(entity_id)

    def get_by_query(self, query: Any) -> list[Any]:
        return list(self.store.values())

    def list_all(self) -> list[Any]:
        return list(self.store.values())

    def execute_query(self, query: Any) -> Any:
        return self.store.values()

    def save(self, entity: Any) -> Any:
        self.store[entity.id] = entity
        return entity

    def delete(self, entity_id: str) -> None:
        self.store.pop(entity_id, None)

    def archive(self, entity_id: str) -> None:
        entity = self.store.get(entity_id)
        if entity is None:
            raise EntityNotFoundException(f"{entity_id} not found")
        self.archived[entity_id] = entity

    def unarchive(self, entity_id: str) -> None:
        self.archived.pop(entity_id, None)


class InMemoryOwnerRepo(InMemoryBaseRepo):
    """Adds owner-aware queries on top of the base in-memory repo."""

    def get_for_owner(self, owner_id: str, arg: Any) -> Any | None:
        return next(
            (e for e in self.store.values() if getattr(e, "owner", None) == owner_id),
            None,
        )

    def get_for_owner_between(
        self, owner_id: str, start: Any, end: Any
    ) -> list[Any]:
        return [
            e
            for e in self.store.values()
            if getattr(e, "owner", None) == owner_id
        ]


class FakeUserRepo(InMemoryBaseRepo, UserRepository):
    def get_by_email(self, email: str) -> list[Any]:
        return [
            u for u in self.store.values() if getattr(u, "email", None) == email
        ]


class FakeStudyRepo(InMemoryBaseRepo, StudyRepository):
    def get_by_name(self, name: str) -> Any | None:
        return next(
            (s for s in self.store.values() if getattr(s, "name", None) == name),
            None,
        )


class FakeWeightRepo(InMemoryOwnerRepo, WeightRepository):  # type: ignore[misc]
    pass


class FakeGoalRepo(InMemoryOwnerRepo, GoalRepository):  # type: ignore[misc]
    def get_all_for_owner(self, owner_id: str, arg: Any) -> list[Any]:
        return self.get_for_owner_between(owner_id, None, None)

    def get_all_for_owner_by_kind(
        self, owner_id: str, arg: Any, kind: Any | None = None
    ) -> list[Any]:
        items = self.get_for_owner_between(owner_id, None, None)
        if kind is None:
            return items
        return [e for e in items if int(getattr(e, "kind", -1)) == int(kind)]

    def get_all_for_owner_between(
        self, owner_id: str, start: Any, end: Any
    ) -> list[Any]:
        return self.get_for_owner_between(owner_id, start, end)

    def get_all_for_owner_by_kind_between(
        self, owner_id: str, start: Any, end: Any, kind: Any | None = None
    ) -> list[Any]:
        items = self.get_for_owner_between(owner_id, start, end)
        if kind is None:
            return items
        return [e for e in items if int(getattr(e, "kind", -1)) == int(kind)]

    def get_for_owner_by_kind(
        self, owner_id: str, arg: Any, kind: Any | None = None
    ) -> Any | None:
        items = self.get_all_for_owner_by_kind(owner_id, arg, kind)
        return items[0] if items else None

    def get_for_owner_by_kind_between(
        self, owner_id: str, start: Any, end: Any, kind: Any | None = None
    ) -> list[Any]:
        return self.get_all_for_owner_by_kind_between(owner_id, start, end, kind)


class FakeConditionRepo(InMemoryOwnerRepo, ConditionRepository):  # type: ignore[misc]
    pass


class FakeMessageRepo(InMemoryBaseRepo, MessageRepository):
    def get_for_owner_between(
        self,
        owner: str,
        start: Any,
        end: Any,
        subtype: int | None = None,
        condition: int | None = None,
    ) -> list[Any]:
        out = [
            e
            for e in self.store.values()
            if getattr(e, "owner", None) == owner
        ]
        if subtype is not None:
            out = [e for e in out if getattr(e, "subtype", None) == subtype]
        if condition is not None:
            out = [e for e in out if getattr(e, "condition", None) == condition]
        return out


class FakeConversationRepo(InMemoryBaseRepo, ConversationRepository):
    def get_for_filters(self, filters: list[Conversation.Filter]) -> list[Any]:
        out = list(self.store.values())
        for f in filters:
            if f.type is Conversation.Filter.Type.KIND:
                out = [c for c in out if c.kind == int(f.val)]
            # CHANNELS / WEEK aren't on the in-memory shape; ignored.
        return out


class FakeParticipantRepo(InMemoryBaseRepo, ParticipantRepository):
    def get_by_study_id(self, study_id: str) -> list[Any]:
        return [
            p
            for p in self.store.values()
            if str(getattr(p, "study_id", "")) == study_id
        ]

    def get_by_num_study_id(self, num: str, study_id: str) -> Any | None:
        return next(
            (
                p
                for p in self.store.values()
                if str(getattr(p, "study_id", "")) == study_id
                and getattr(p, "participant_number", "") == num
            ),
            None,
        )


def make_fakes() -> dict[type, Any]:
    """Mapping from interface type to in-memory fake."""
    return {
        UserRepository: FakeUserRepo(),
        StudyRepository: FakeStudyRepo(),
        WeightRepository: FakeWeightRepo(),
        GoalRepository: FakeGoalRepo(),
        ConditionRepository: FakeConditionRepo(),
        MessageRepository: FakeMessageRepo(),
        ConversationRepository: FakeConversationRepo(),
        ParticipantRepository: FakeParticipantRepo(),
    }


@pytest.fixture
def fakes() -> dict[type, Any]:
    return make_fakes()


# Interface → ``RepositoryContainer`` provider name. The test fakes are
# keyed by interface; routes resolve through the container, so we need a
# mapping from the test-side interface to the container's provider name.
_IFACE_TO_PROVIDER: dict[type, str] = {
    UserRepository: "user",
    StudyRepository: "study",
    WeightRepository: "weight",
    GoalRepository: "goal",
    ConditionRepository: "condition",
    MessageRepository: "message",
    ConversationRepository: "conversation",
    ParticipantRepository: "participant",
}

from openwellness_api.resources import RESOURCE_MODULES

_WIRED_MODULES = [mod.__name__ for mod in RESOURCE_MODULES]
# Each module name is also its ``RepositoryContainer`` provider name.
_RESOURCE_NAMES = {mod.__name__.rsplit(".", 1)[-1] for mod in RESOURCE_MODULES}


@pytest.fixture
def fake_email_sender():
    """Function-scoped in-memory OTP email recorder.

    The same instance is attached to the ``app`` fixture's auth container, so a
    test can read ``fake_email_sender.sent`` / ``last_code(...)`` to recover a
    code that the send path delivered.
    """
    from openwellness_api.auth.email_sender import FakeEmailSender

    return FakeEmailSender()


def build_test_app(fakes: dict[type, Any], email_sender: Any) -> FastAPI:
    """App with fakes wired through an ``ApplicationContainer`` instance.

    We bypass the real lifespan (no Couchbase/Mongo connection), build a
    container, override each fake's provider with ``providers.Object(fake)``,
    and wire the resource modules so ``@inject`` markers see the overrides. Every
    other resource provider gets a fresh ``InMemoryOwnerRepo`` so any router can
    run. An ``AuthContainer`` is also built and attached with real collaborators
    backed by fakeredis/mongomock + a real clock, so the auth router works
    end-to-end. Callers unwire with ``app.state.container.unwire()``.
    """
    import fakeredis
    import mongomock

    from openwellness_api.auth.otp_store import RedisOtpStore
    from openwellness_core.adapters.mongo.repositories.mongo_refresh_session_repository import (
        MongoRefreshSessionRepository,
    )

    from openwellness_api.auth.session_store import RefreshSessionStore
    from openwellness_api.auth.token_service import JwtTokenService
    from openwellness_api.config import APISettings, AuthSettings
    from openwellness_api.container import ApplicationContainer
    from openwellness_api.deps.auth_container import AuthContainer, default_clock
    from openwellness_api.main import create_app

    instance = create_app(lifespan=None, settings=APISettings(enable_docs=False))

    container = ApplicationContainer()
    named = {_IFACE_TO_PROVIDER[iface] for iface in fakes}
    for iface, fake in fakes.items():
        getattr(container.repositories, _IFACE_TO_PROVIDER[iface]).override(
            providers.Object(fake)
        )
    for name in _RESOURCE_NAMES - named:
        getattr(container.repositories, name).override(
            providers.Object(InMemoryOwnerRepo())
        )
    container.wire(modules=_WIRED_MODULES)
    instance.state.container = container

    # --- Auth container with test fakes (isolated per app). --- #
    # One shared AuthSettings instance so token_service/otp_store agree on the
    # secrets/TTLs. The real clock keeps issued access tokens valid (PyJWT
    # validates ``exp`` against wall-clock time).
    auth_settings = AuthSettings()
    auth_container = AuthContainer()
    auth_container.auth_settings.override(providers.Object(auth_settings))
    auth_container.token_service.override(
        providers.Object(
            JwtTokenService(settings=auth_settings, clock=default_clock)
        )
    )
    auth_container.otp_store.override(
        providers.Object(
            RedisOtpStore(
                redis=fakeredis.FakeRedis(decode_responses=True),
                settings=auth_settings,
                clock=default_clock,
            )
        )
    )
    refresh_adapter = MongoRefreshSessionRepository(
        collection=mongomock.MongoClient()["testdb"]["auth_refresh_sessions"]
    )
    refresh_adapter.ensure_indexes()
    session_store = RefreshSessionStore(repo=refresh_adapter, clock=default_clock)
    auth_container.session_store.override(providers.Object(session_store))
    auth_container.email_sender.override(providers.Object(email_sender))
    instance.state.auth_container = auth_container
    return instance


@pytest.fixture(scope="session")
def app_builder():
    """The app factory, for tests that want a module-scoped app (building is ~0.35 s)."""
    return build_test_app


@pytest.fixture
def app(fakes: dict[type, Any], fake_email_sender):
    instance = build_test_app(fakes, fake_email_sender)
    yield instance
    instance.state.container.unwire()


@pytest.fixture
def seed_accounts(fakes: dict[type, Any]) -> dict[str, Any]:
    """Opt-in seed of pre-provisioned auth accounts into the fake repos.

    NOT applied by default — only tests that request this fixture get the seeded
    accounts, so existing CRUD tests (which assert on user lists) are unaffected.

    Seeds:
      * a VERIFIED, login-ready user (alice) + matching participant, and
      * an UNVERIFIED registration target (bob) + matching participant.
    """
    user_repo = fakes[UserRepository]
    participant_repo = fakes[ParticipantRepository]

    login_user_id = str(uuid4())
    pid_a = str(uuid4())
    alice = User(
        id=login_user_id,
        email="alice@example.com",
        is_active=True,
        username="alice",
        verified_id="marker",
        roles={"participant": {"pid": pid_a}},
    )
    participant_a = Participant(
        id=pid_a,
        user_id=login_user_id,
        is_active=True,
        participant_number="A-1",
    )

    reg_user_id = str(uuid4())
    pid_b = str(uuid4())
    bob = User(
        id=reg_user_id,
        email="bob@example.com",
        is_active=True,
        username="bob",
        verified_id=None,
        roles={"participant": {"pid": pid_b}},
    )
    participant_b = Participant(
        id=pid_b,
        user_id=reg_user_id,
        is_active=False,
        participant_number="B-1",
    )

    user_repo.store[alice.id] = alice
    user_repo.store[bob.id] = bob
    participant_repo.store[participant_a.id] = participant_a
    participant_repo.store[participant_b.id] = participant_b

    return {
        "login_email": "alice@example.com",
        "login_user_id": login_user_id,
        "login_pid": pid_a,
        "reg_email": "bob@example.com",
        "reg_user_id": reg_user_id,
        "reg_pid": pid_b,
    }


TEST_ADMIN_ID = "test-admin"


def token_for(
    app: FastAPI,
    *,
    user_id: str,
    participant: str | None = None,
    roles: Sequence[str] = (),
    coach_studies: Sequence[str] = (),
) -> str:
    """Mint through the app's own token service so the floor really verifies it."""
    return app.state.auth_container.token_service().mint_access(
        user_id=user_id,
        participant=participant,
        roles=roles,
        coach_studies=coach_studies,
    )


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Admin-authenticated: the CRUD suites test CRUD, not authorization."""
    token = token_for(app, user_id=TEST_ADMIN_ID, roles=["admin"])
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture
def anon_client(app: FastAPI) -> TestClient:
    return TestClient(app)


# --------------------------------------------------------------------------- #
# The authorization world: two studies, participants in each, and one caller of
# every class the policy matrix distinguishes.
# --------------------------------------------------------------------------- #

STUDY_A = "study-a"
STUDY_B = "study-b"


@dataclass
class World:
    """Ids and ready-made auth headers for each caller class."""

    study_a: str = STUDY_A
    study_b: str = STUDY_B
    p_a: str = "p-a"
    p_b: str = "p-b"
    p_d: str = "p-d"
    headers: dict[str, dict[str, str]] = field(default_factory=dict)

    def client(self, app: FastAPI, caller: str) -> TestClient:
        return TestClient(app, headers=self.headers[caller])


def reset_fakes(app: FastAPI) -> None:
    """Empty every resource fake so one module-scoped app serves many tests."""
    for name in _RESOURCE_NAMES:
        repo = getattr(app.state.container.repositories, name)()
        repo.store.clear()
        repo.archived.clear()


def seed_world(app: FastAPI) -> World:
    """Store the studies, participants and users, and mint every caller's token."""
    repos = app.state.container.repositories
    for study_id in (STUDY_A, STUDY_B):
        repos.study().store[study_id] = Study(
            id=study_id, app_id="app", name=study_id, time_created=datetime.now()
        )
    people = (
        ("u-a", "p-a", STUDY_A),
        ("u-b", "p-b", STUDY_B),
        ("u-d", "p-d", STUDY_B),
    )
    for user_id, pid, study_id in people:
        roles: dict[str, Any] = {"participant": {"pid": pid}}
        if user_id == "u-d":
            roles["coach"] = {"studies": [STUDY_A]}
        repos.user().store[user_id] = User(
            id=user_id,
            email=f"{user_id}@example.com",
            is_active=True,
            username=user_id,
            verified_id="marker",
            roles=roles,
        )
        repos.participant().store[pid] = Participant(
            id=pid, user_id=user_id, study_id=study_id, is_active=True
        )
    # Coaches can sign in through the real OTP flow against these records.
    for user_id, email, studies in (
        ("u-ci", "coach-in@example.com", [STUDY_A]),
        ("u-co", "coach-other@example.com", [STUDY_B]),
    ):
        repos.user().store[user_id] = User(
            id=user_id,
            email=email,
            is_active=True,
            username=user_id,
            roles={"coach": {"studies": studies}},
        )

    def mint(user_id: str, **kw: Any) -> dict[str, str]:
        return {"Authorization": f"Bearer {token_for(app, user_id=user_id, **kw)}"}

    return World(
        headers={
            "owner_self": mint("u-a", participant="p-a", roles=["participant"]),
            "owner_other": mint("u-b", participant="p-b", roles=["participant"]),
            "coach_in": mint("u-ci", roles=["coach"], coach_studies=[STUDY_A]),
            "coach_other": mint("u-co", roles=["coach"], coach_studies=[STUDY_B]),
            "coach_empty": mint("u-ce", roles=["coach"]),
            "coach_both": mint(
                "u-cb", roles=["coach"], coach_studies=[STUDY_A, STUDY_B]
            ),
            "dual": mint(
                "u-d",
                participant="p-d",
                roles=["participant", "coach"],
                coach_studies=[STUDY_A],
            ),
            "admin": mint(TEST_ADMIN_ID, roles=["admin"]),
            "no_role": mint("u-n"),
        }
    )


@pytest.fixture
def world(app: FastAPI) -> World:
    return seed_world(app)

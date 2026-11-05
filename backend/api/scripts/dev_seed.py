"""Dev seed: one admin, one coach, one participant and the study linking them.

For local development and the Phase 2 manual UAT only. It is NOT for production
and is excluded from the API image (``backend/.dockerignore``); Phase 11's
bootstrap replaces it. It exposes no endpoint and holds no secret: the
``example.com`` mailboxes cannot receive an OTP on a real SMTP server, so a
seeded account can only be signed in to through a local mail sink.

Idempotent: every record is looked up through its port first and created only
when missing, so re-running it changes nothing.

Run: ``cd backend/api && uv run --frozen python scripts/dev_seed.py``
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from openwellness_core.application.repositories import (
    ParticipantRepository,
    StudyRepository,
    UserRepository,
)
from openwellness_core.domain.models.participant import Participant
from openwellness_core.domain.models.study import Study
from openwellness_core.domain.models.user import User

ADMIN_EMAIL = "dev-admin@example.com"
COACH_EMAIL = "dev-coach@example.com"
PARTICIPANT_EMAIL = "dev-participant@example.com"
STUDY_NAME = "Dev Study"
PARTICIPANT_NUMBER = "DEV-1"


@dataclass(frozen=True)
class SeedResult:
    admin_email: str
    coach_email: str
    participant_email: str
    study_id: str
    participant_id: str


def _user(users: UserRepository, email: str, **fields: object) -> User:
    found = users.get_by_email(email)
    if found:
        return found[0]
    return users.create(
        User(email=email, is_active=True, username=email.split("@")[0], **fields)
    )


def seed_dev_data(
    *,
    users: UserRepository,
    studies: StudyRepository,
    participants: ParticipantRepository,
) -> SeedResult:
    # The Mongo adapter ignores a caller-chosen id, so every id below is read
    # back from the entity the port returns, in dependency order.
    study = studies.get_by_name(STUDY_NAME) or studies.create(
        Study(app_id="dev", name=STUDY_NAME, time_created=datetime.now())
    )
    _user(users, ADMIN_EMAIL, roles={"admin": {}})
    _user(users, COACH_EMAIL, roles={"coach": {"studies": [study.id]}})
    person = _user(users, PARTICIPANT_EMAIL, verified_id="dev-seed")
    participant = participants.get_by_num_study_id(
        PARTICIPANT_NUMBER, study.id
    ) or participants.create(
        Participant(
            user_id=person.id,
            study_id=study.id,
            participant_number=PARTICIPANT_NUMBER,
            is_active=True,
        )
    )
    # Checked on every run so a half-finished earlier run is completed.
    if person.roles.get("participant", {}).get("pid") != participant.id:
        person.roles = {"participant": {"pid": participant.id}}
        users.save(person)
    return SeedResult(
        admin_email=ADMIN_EMAIL,
        coach_email=COACH_EMAIL,
        participant_email=PARTICIPANT_EMAIL,
        study_id=study.id,
        participant_id=participant.id,
    )


def main() -> None:
    from dependency_injector import providers

    from openwellness_api.config import AppConfig
    from openwellness_api.container import ApplicationContainer

    # Mongo only: user, study and participant need no Couchbase connection.
    container = ApplicationContainer()
    container.app_config.override(providers.Object(AppConfig()))
    repos = container.repositories
    result = seed_dev_data(
        users=repos.user(), studies=repos.study(), participants=repos.participant()
    )
    print(f"admin:       {result.admin_email}")
    print(f"coach:       {result.coach_email}")
    print(f"participant: {result.participant_email}")
    print(f"study id:    {result.study_id}")
    print(f"participant id: {result.participant_id}")


if __name__ == "__main__":
    main()

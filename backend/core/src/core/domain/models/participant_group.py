"""ParticipantGroup domain model."""

from dataclasses import dataclass, field

from .base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class ParticipantGroup(BaseOwnerEntity):
    """A collection of Participants in a study.

    Participants who belong to a ParticipantGroup receive all documents that
    belong to the corresponding routing channel. The routing channel itself
    is derived at the persistence layer (see `CBParticipantGroup`) from this
    entity's `id`.
    """

    participant_ids: list[str]
    pid_to_mid: dict

    info: dict = field(default_factory=dict)

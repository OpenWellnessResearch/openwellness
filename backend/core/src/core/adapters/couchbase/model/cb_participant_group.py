"""Couchbase persistence for ParticipantGroup."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .cb_base_owner_entity import CBBaseOwnerEntity


class CBParticipantGroup(CBBaseOwnerEntity):
    """Persistence for ParticipantGroup.

    Derives the routing channel from the entity id during `from_domain`,
    eliminating the legacy two-save pattern (`save → mutate channels → save`).
    """

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    type: ClassVar[str] = "ParticipantGroup"

    participant_ids: list[str] | None = Field(alias="participantIds", default=None)
    pid_to_mid: dict | None = Field(alias="pidToMid", default=None)
    info: dict | None = None

    @classmethod
    def from_domain(cls, entity: Any, archived: bool = False) -> "CBParticipantGroup":
        instance = super().from_domain(entity, archived=archived)
        assert isinstance(instance, CBParticipantGroup)
        if entity.id:
            instance.channels = [f"participantGroup:{entity.id}"]
        return instance

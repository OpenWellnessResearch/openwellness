"""Base Condition domain entity."""

from dataclasses import dataclass, field

from ..base_owner_entity import BaseOwnerEntity


@dataclass(kw_only=True)
class Condition(BaseOwnerEntity):
    """Study-specific conditions of a participant."""

    app_group: int | None = field(default=None)
    app_group_note: str | None = field(default=None)
    week: int | None = field(default=None)

    def __post_init__(self) -> None:
        super().__post_init__()

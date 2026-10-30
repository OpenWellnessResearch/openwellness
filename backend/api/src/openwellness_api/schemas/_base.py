"""Shared Pydantic v2 schema base.

Three responsibilities:

1. ``SCHEMA_CONFIG`` — the canonical ``ConfigDict`` used by every wire
   schema. Sets up camelCase aliasing per AIP-140, ``populate_by_name``
   so server-side code can keep using snake_case, and ``extra="ignore"``
   so unknown fields from older clients don't 400.
2. ``ResourceBase`` — the AIP-148 standard-field set: ``name``,
   ``createTime``, ``updateTime``. Every response model inherits from
   this; ``name`` is computed by ``serialize_one`` and injected into the
   serialization dict before validation.
3. ``ArrowField`` — type adapter reused by schemas whose domain field
   types don't round-trip through Pydantic by default.
"""

from __future__ import annotations

from typing import Annotated, Any

import arrow
from arrow import Arrow
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer
from pydantic.alias_generators import to_camel


SCHEMA_CONFIG = ConfigDict(
    populate_by_name=True,
    alias_generator=to_camel,
    arbitrary_types_allowed=True,
    extra="ignore",
)


def _to_arrow(v: Any) -> Arrow:
    if isinstance(v, Arrow):
        return v
    if v is None:
        raise ValueError("expected Arrow-compatible value, got None")
    return arrow.get(v)


def _from_arrow(a: Arrow) -> str:
    return a.isoformat()


ArrowField = Annotated[
    Arrow,
    BeforeValidator(_to_arrow),
    PlainSerializer(_from_arrow, return_type=str, when_used="json"),
]


class ResourceBase(BaseModel):
    """AIP-148 standard fields shared by every response resource.

    ``name`` is the full resource path (e.g. ``"users/abc/weights/xyz"``).
    ``create_time`` / ``update_time`` are RFC-3339 strings; they alias to
    ``createTime`` / ``updateTime`` on the wire.
    """

    model_config = SCHEMA_CONFIG

    name: str
    create_time: str | None = Field(default=None, alias="createTime")
    update_time: str | None = Field(default=None, alias="updateTime")

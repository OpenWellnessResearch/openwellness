"""Mongo persistence for App."""

from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from .mongo_base_entity import MongoBaseEntity


class MongoApp(MongoBaseEntity):
    """Persistence for App."""

    model_config = ConfigDict(
        populate_by_name=True, extra="ignore", arbitrary_types_allowed=True
    )

    collection: ClassVar[str] = "apps"

    name: Any = None
    time_created: Any = Field(alias="timeCreated", default=None)
    android_package_name: Any = Field(alias="androidPackageName", default=None)
    app_store_id: Any = Field(alias="appStoreId", default=None)
    ios_bundle_id: Any = Field(alias="iosBundleId", default=None)
    one_signal_app_id: Any = Field(alias="oneSignalAppId", default=None)

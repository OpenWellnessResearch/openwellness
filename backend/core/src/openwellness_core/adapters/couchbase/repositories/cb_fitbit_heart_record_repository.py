"""Couchbase repository for FitbitHeartRecord."""

from collections import defaultdict
from typing import DefaultDict, Generic

from ....application.repositories.fitbit_heart_record_repository import (
    FitbitHeartRecordRepository,
    SomeFitbitHeartRecord,
)
from ....domain.models.fitbit_heart_record import FitbitHeartRecord
from ....infrastructure.interfaces.entity_repository import EntityRepository
from ..model.cb_fitbit import CBFitbitHeartRecord
from ._query_helpers import bucket_ident
from .cb_base_repository import CBBaseRepository


class CBFitbitHeartRecordRepository(
    FitbitHeartRecordRepository,
    CBBaseRepository[SomeFitbitHeartRecord, CBFitbitHeartRecord],
    Generic[SomeFitbitHeartRecord],
):
    """Couchbase repository for the FitbitHeartRecord entity."""

    def __init__(
        self,
        repo: EntityRepository,
        entity_type: type[SomeFitbitHeartRecord] = FitbitHeartRecord,
        persistence_type: type[CBFitbitHeartRecord] = CBFitbitHeartRecord,
    ) -> None:
        super().__init__(repo, entity_type, persistence_type)
        self.entity_type = entity_type

    def create_from_raw(self, data: dict) -> SomeFitbitHeartRecord:
        cleaned_data = self._clean_data(data)
        return self.init_entity_valid_fields(cleaned_data)

    def update_from_raw(
        self, record: SomeFitbitHeartRecord, data: dict
    ) -> SomeFitbitHeartRecord:
        cleaned_data = self._clean_data(data)
        return self.update_entity_valid_fields(record, cleaned_data)

    def get_for_owner(self, owner_id: str, arg: str) -> SomeFitbitHeartRecord | None:
        q, params = self._build_get_query(owner_id, arg)
        items = self.repo.get_by_query(q, params)
        if not items:
            return None
        if len(items) > 1:
            heart_records = [self.init_entity_valid_fields(item) for item in items]
            return self._attempt_dedupe(heart_records)
        return self.init_entity_valid_fields(items[0])

    def get_for_owner_between(
        self, owner_id: str, start: str, end: str
    ) -> list[SomeFitbitHeartRecord]:
        q, params = self._build_get_between_query(owner_id, start, end)
        items = self.repo.get_by_query(q, params)
        heart_records = [self.init_entity_valid_fields(item) for item in items]
        date_records: DefaultDict[str, list[SomeFitbitHeartRecord]] = defaultdict(list)
        for record in heart_records:
            date_records[record.fitbit_date].append(record)
        deduplicated_records = []
        for records in date_records.values():
            if len(records) > 1:
                deduplicated_records.append(self._attempt_dedupe(records))
            else:
                deduplicated_records.append(records[0])
        return deduplicated_records

    def _build_get_between_query(
        self, owner_id: str, start: str, end: str
    ) -> tuple[str, dict]:
        b = bucket_ident(self.repo.bucket)
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND owner = $owner "
            f"AND fitbitDate BETWEEN $start AND $end "
            f"ORDER BY fitbitDate, createdAt DESC"
        )
        params = {
            "type": CBFitbitHeartRecord.type,
            "owner": owner_id,
            "start": start,
            "end": end,
        }
        return q, params

    def _build_get_query(
        self, owner_id: str, arg: str
    ) -> tuple[str, dict]:
        b = bucket_ident(self.repo.bucket)
        q = (
            f"SELECT {b}.*, meta().id, meta().xattrs._sync.rev as _rev "
            f"FROM {b} "
            f"WHERE type = $type "
            f"AND owner = $owner "
            f"AND fitbitDate = $fitbitDate "
            f"ORDER BY fitbitDate, createdAt DESC"
        )
        params = {
            "type": CBFitbitHeartRecord.type,
            "owner": owner_id,
            "fitbitDate": arg,
        }
        return q, params

    def _clean_data(self, data: dict) -> dict:
        hr_zones = [
            FitbitHeartRecord.HRZone(x) for x in data.get("heartRateZones", [])
        ]
        cleaned_data = data.copy()
        for zone in hr_zones:
            cleaned_data[zone.attribute_name] = zone.__dict__
        del cleaned_data["heartRateZones"]
        cleaned_data["type"] = CBFitbitHeartRecord.type
        return cleaned_data

    def _attempt_dedupe(
        self, records: list[SomeFitbitHeartRecord]
    ) -> SomeFitbitHeartRecord:
        created_at_diffs = [
            records[i + 1].created_at - records[i].created_at
            for i in range(len(records) - 1)
        ]
        if all(diff < 1 for diff in created_at_diffs):
            for record in records[1:]:
                self.repo.delete(record.id)
            return records[0]
        raise ValueError(
            "Records were not created within 1 second of each other, cannot deduplicate."
        )

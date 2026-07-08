import asyncio
import csv
import math
import os
import queue
from typing import Any

from zsim.define import ANOMALY_MAPPING, DEBUG

result_queue: queue.Queue[dict[str, Any]] = queue.Queue()

_BASE_FIELDNAMES = [
    "tick",
    "skill_tag",
    "element_type",
    "dmg_expect",
    "dmg_crit",
    "stun",
    "buildup",
    "is_anomaly",
    "is_disorder",
    "UUID",
    "crit_rate",
    "crit_dmg",
]


class DamageRecordBuffer:
    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []
        self._fieldnames = list(_BASE_FIELDNAMES)
        self._seen_fieldnames = set(self._fieldnames)

    @property
    def records(self) -> list[dict[str, Any]]:
        return self._records

    @property
    def fieldnames(self) -> list[str]:
        return self._fieldnames

    def add(self, record: dict[str, Any]) -> None:
        self._records.append(record)
        for key in record:
            if key not in self._seen_fieldnames:
                self._seen_fieldnames.add(key)
                self._fieldnames.append(key)

    def flush(self, report_file_path: str) -> None:
        if not self._records:
            return
        _write_damage_csv(report_file_path, self._records, self._fieldnames)


def report_dmg_result(**kwargs: Any) -> None:
    if not DEBUG:
        return
    record = dict(kwargs)
    skill_tag = record.get("skill_tag")
    is_anomaly = bool(record.get("is_anomaly", False))
    is_disorder = bool(record.get("is_disorder", False))

    if is_anomaly and skill_tag is None:
        skill_tag = ANOMALY_MAPPING.get(record.get("element_type"), skill_tag)
    assert skill_tag is not None, "技能标签不能为空！"
    if is_disorder and "紊乱" not in str(skill_tag):
        skill_tag = f"{skill_tag}紊乱"

    record["skill_tag"] = skill_tag
    record["UUID"] = str(record.get("UUID", ""))
    if record.get("dmg_crit") is None:
        record["dmg_crit"] = math.nan
    result_queue.put(record)


def _write_damage_csv(
    report_file_path: str, records: list[dict[str, Any]], fieldnames: list[str]
) -> None:
    os.makedirs(os.path.dirname(report_file_path), exist_ok=True)

    with open(report_file_path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)


async def async_result_writer(result_id: str) -> None:
    report_file_path = f"{result_id}/damage.csv"
    buffer = DamageRecordBuffer()

    try:
        while True:
            try:
                record = result_queue.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.01)
                continue

            buffer.add(record)
            result_queue.task_done()
    finally:
        await asyncio.to_thread(buffer.flush, report_file_path)

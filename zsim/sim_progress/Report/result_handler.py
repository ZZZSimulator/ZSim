import asyncio
import os
import queue
import uuid

import aiofiles
import numpy as np
import polars as pl

from zsim.define import ANOMALY_MAPPING, ElementType

result_queue: queue.Queue = queue.Queue()


def report_dmg_result(
    tick: int,
    element_type: ElementType | int,
    skill_tag: str | None = None,
    dmg_expect: float | np.float64 = 0,
    dmg_crit: float | np.float64 | None = None,
    UUID: str | uuid.UUID = "",
    is_anomaly: bool = False,
    is_disorder: bool = False,
    **kwargs,
):
    if is_anomaly and skill_tag is None:
        skill_tag = ANOMALY_MAPPING.get(element_type, skill_tag)
    assert skill_tag is not None, "技能标签不能为空！"
    if is_disorder and "紊乱" not in skill_tag:
        skill_tag += "紊乱"
    if dmg_crit is None:
        dmg_crit = np.nan
    result_dict = {
        "tick": tick,
        "element_type": element_type,
        "is_anomaly": is_anomaly,
        "skill_tag": skill_tag,
        "dmg_expect": dmg_expect,
        "dmg_crit": dmg_crit,
        "UUID": str(UUID),
    }
    result_dict.update(kwargs)
    result_queue.put(result_dict)


async def async_result_writer(result_id: str):
    result_path = f"{result_id}/damage.csv"
    os.makedirs(os.path.dirname(result_path), exist_ok=True)
    new_file = not os.path.exists(result_path)

    buffer = []
    max_buffer_size = 100

    while True:
        try:
            result_dict = result_queue.get_nowait()
            buffer.append(result_dict)

            if len(buffer) >= max_buffer_size or result_queue.empty():
                if buffer:
                    result_df = pl.DataFrame(buffer)
                    csv_data = result_df.write_csv(
                        include_header=new_file, separator=","
                    )
                    mode = "w" if new_file else "a"
                    async with aiofiles.open(
                        result_path, mode, encoding="utf-8-sig"
                    ) as file:
                        await file.write(csv_data)

                    new_file = False
                    buffer.clear()

            result_queue.task_done()
        except queue.Empty:
            if buffer:
                result_df = pl.DataFrame(buffer)
                csv_data = result_df.write_csv(include_header=new_file, separator=",")
                mode = "w" if new_file else "a"
                async with aiofiles.open(
                    result_path, mode, encoding="utf-8-sig"
                ) as file:
                    await file.write(csv_data)

                new_file = False
                buffer.clear()

            await asyncio.sleep(0.01)

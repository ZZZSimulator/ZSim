import os
from collections import defaultdict

import polars as pl

from zsim.define import DEBUG, DEBUG_LEVEL

buffered_data: dict[str, dict[int, dict[str, int]]] = defaultdict(
    lambda: defaultdict(lambda: defaultdict(int))
)


def report_buff_to_queue(
    character_name: str, time_tick, buff_name: str, buff_count, all_match: bool, level=4
):
    if DEBUG and DEBUG_LEVEL <= level:
        if all_match:
            # 由于Buff的log录入总是在下个tick的开头，所以这里的time_tick要-1
            buffered_data[character_name][time_tick - 1][buff_name] += buff_count


def dump_buff_csv(result_id: str):
    for char_name, char_data in buffered_data.items():
        if not char_data:
            continue

        rows = [{"time_tick": tick, **buffs} for tick, buffs in char_data.items()]

        if not rows:
            continue

        buff_report_file_path = f"{result_id}/buff_log/{char_name}.csv"
        os.makedirs(os.path.dirname(buff_report_file_path), exist_ok=True)

        df = pl.DataFrame(rows)
        # Sort columns: time_tick first, then buff names alphabetically for deterministic output.
        buff_columns = sorted([col for col in df.columns if col != "time_tick"])
        df = df.sort("time_tick").select(["time_tick"] + buff_columns)

        df.write_csv(buff_report_file_path, include_bom=True)

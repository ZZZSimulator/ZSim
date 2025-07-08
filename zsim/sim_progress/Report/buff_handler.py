import os
from collections import defaultdict

import pandas as pd

from zsim.define import DEBUG, DEBUG_LEVEL

buffered_data: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))


def report_buff_to_queue(
    character_name: str, time_tick, buff_name: str, buff_count, all_match: bool, level=4
):
    if DEBUG and DEBUG_LEVEL <= level:
        if all_match:
            # 由于Buff的log录入总是在下个tick的开头，所以这里的time_tick要-1
            buffered_data[character_name][time_tick - 1][buff_name] += buff_count


# TODO：切换为 polars
def dump_buff_csv(result_id: str):
    for char_name in buffered_data:
        if char_name not in buffered_data:
            raise ValueError("你tmd函数写错了！")
        buff_report_file_path = f"{result_id}/buff_log/{char_name}.csv"
        os.makedirs(os.path.dirname(buff_report_file_path), exist_ok=True)
        df = pd.DataFrame.from_dict(
            buffered_data[char_name], orient="index"
        ).reset_index()
        df.rename(columns={"index": "time_tick"}, inplace=True)
        df = df.sort_values(by="time_tick")
        df.to_csv(buff_report_file_path, index=False, encoding="utf-8-sig")

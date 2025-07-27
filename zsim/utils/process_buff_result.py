import json
import os
import asyncio
import aiofiles
import aiofiles.os
from typing import Any

import polars as pl
from zsim.define import results_dir


def _prepare_buff_timeline_data(df: pl.DataFrame) -> list[dict[str, Any]]:
    """将包含时间序列BUFF数据的Polars DataFrame转换为适用于Plotly时间线的格式。

    Args:
        df (pl.DataFrame): 输入的Polars DataFrame，应包含 'time_tick' 列，
                           其余列为各个BUFF的状态，列名为BUFF名称。
                           单元格中的值代表该BUFF在对应time_tick的状态值，
                           null 值表示BUFF在该tick不生效。

    Returns:
        list[dict[str, Any]]: 转换后的数据列表，每个字典代表一个BUFF生效的时间段，
                              包含 'Task' (BUFF名称), 'Start' (开始tick),
                              'Finish' (结束tick), 'Value' (BUFF值)。
    """
    timeline_data: list[dict[str, Any]] = []
    buff_columns = [col for col in df.columns if col != "time_tick"]

    for buff_name in buff_columns:
        # 将空值填充为0.0并筛选出来
        buff_df = df.select(["time_tick", buff_name]).with_columns(pl.col(buff_name).fill_null(0.0))

        if buff_df.height == 0:
            continue

        # 尝试将 BUFF 值列转换为数值类型，无法转换的设为 null
        buff_df = buff_df.with_columns(pl.col(buff_name).cast(pl.Float32, strict=False))

        # 计算值变化的点
        buff_df = buff_df.with_columns(pl.col(buff_name).diff().alias("value_diff"))

        # 标记每个连续段的开始
        # 条件：第一行，或者值发生变化
        buff_df = buff_df.with_columns(
            ((pl.arange(0, pl.count()) == 0) | (pl.col("value_diff") != 0)).alias("is_start")
        )

        # 为每个连续段分配一个ID
        # 将布尔值转换为整数，以便进行累加
        buff_df = buff_df.with_columns(
            pl.col("is_start").cast(pl.Int32).cum_sum().alias("group_id")
        )

        # 按段聚合，找到起始tick、结束tick和对应的值
        grouped = buff_df.group_by("group_id").agg(
            pl.first("time_tick").alias("Start"),
            pl.last("time_tick").alias("last_valid_tick"),
            pl.first(buff_name).alias("Value"),
        )

        # 计算结束 tick (Finish)
        # 使用当前段的最后一个有效tick作为结束点
        grouped = grouped.with_columns(pl.col("last_valid_tick").alias("Finish"))

        # 转换结果为字典列表
        for row in grouped.select(["Start", "Finish", "Value"]).iter_rows(named=True):
            # 过滤掉 Value 为 null 的行
            if row["Value"]:
                timeline_data.append(
                    {
                        "Task": buff_name,
                        "Start": int(row["Start"]),
                        "Finish": int(row["Finish"]),
                        "Value": row["Value"],
                    }
                )

    return timeline_data


def _load_cached_buff_data(rid: int | str) -> dict[str, list[dict[str, Any]]] | None:
    """尝试从JSON缓存文件加载BUFF时间线数据。"""
    buff_log_path = os.path.join(results_dir, str(rid), "buff_log")
    json_file_path = os.path.join(buff_log_path, "buff_timeline_data.json")

    if os.path.exists(json_file_path):
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # 加载失败，将视为缓存不存在
            return None
    return None


async def prepare_buff_data_and_cache(
    rid: int | str,
) -> dict[str, list[dict[str, Any]]] | None:
    """异步处理BUFF日志CSV文件，生成时间线数据，并缓存到JSON文件。

    此函数不处理UI反馈，仅负责数据处理和文件操作。

    Args:
        rid (int | str): 运行ID。

    Returns:
        dict[str, list[dict[str, Any]]] | None: 处理后的BUFF时间线数据字典，
                                                如果处理失败或无CSV文件则返回None。
                                                如果找到CSV但处理后无数据，返回空字典 {}。
    """
    buff_log_path = os.path.join(results_dir, str(rid), "buff_log")
    json_file_path = os.path.join(buff_log_path, "buff_timeline_data.json")

    if not await aiofiles.os.path.exists(buff_log_path):
        # 日志目录不存在，无法处理
        return None

    try:
        all_files = await aiofiles.os.listdir(buff_log_path)
        csv_files = [f for f in all_files if f.endswith(".csv")]
    except FileNotFoundError:
        # listdir 可能在目录刚创建时失败，或者权限问题
        return None
    except Exception as e:
        print(f"列出目录 {buff_log_path} 时发生错误: {e}")
        return None

    if not csv_files:
        # 没有CSV文件，无需处理，但也无需创建JSON。返回空字典表示成功但无数据。
        return {}

    all_buff_data: dict[str, list[dict[str, Any]]] = {}
    processed_csv_files: list[str] = []
    tasks = []

    async def process_csv(filename: str):
        nonlocal all_buff_data, processed_csv_files
        csv_file_path = os.path.join(buff_log_path, filename)
        try:
            # 使用 asyncio.to_thread 在单独的线程中运行同步的 polars 操作
            # 注意：Polars 的 read_csv 默认是多线程的，但为了与 aiofiles 配合，仍使用 to_thread
            df = await asyncio.to_thread(pl.read_csv, csv_file_path)
            file_key = filename.replace(".csv", "")
            # _prepare_buff_timeline_data 本身是同步的，可以在这里直接调用
            buff_data = _prepare_buff_timeline_data(df)
            all_buff_data[file_key] = buff_data
            processed_csv_files.append(csv_file_path)
        except Exception as e:
            print(f"处理文件 {csv_file_path} 时发生错误: {e}")
            # 可以选择在这里标记错误，或者让 gather 捕获
            raise  # 重新抛出异常，让 gather 知道有错误

    # 为每个CSV文件创建一个处理任务
    for filename in csv_files:
        tasks.append(process_csv(filename))

    # 并发执行所有CSV处理任务
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 检查是否有处理错误
    has_processing_error = any(isinstance(res, Exception) for res in results)

    if has_processing_error:
        print("处理CSV文件时至少发生一个错误。")
        return None

    # 如果没有处理错误或者决定即使有错误也要继续
    if all_buff_data:  # 确保有数据才写入
        try:
            # 异步写入JSON缓存文件
            async with aiofiles.open(json_file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(all_buff_data, indent=4, ensure_ascii=False))
        except Exception as e:
            print(f"写入JSON文件 {json_file_path} 时发生错误: {e}")
            has_processing_error = True  # 标记写入错误

    # 异步删除原始CSV文件
    if processed_csv_files:
        delete_tasks = [aiofiles.os.remove(csv_path) for csv_path in processed_csv_files]
        delete_results = await asyncio.gather(*delete_tasks, return_exceptions=True)
        for i, res in enumerate(delete_results):
            if isinstance(res, Exception):
                print(f"删除文件 {processed_csv_files[i]} 时发生错误: {res}")
                # 删除失败通常不认为是关键错误，只打印日志

    # 如果在处理或写入JSON时发生错误，返回None
    if has_processing_error:
        return None

    return all_buff_data

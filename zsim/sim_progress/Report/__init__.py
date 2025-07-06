import asyncio
import json
import os
import threading
from datetime import datetime
from typing import TYPE_CHECKING

from .buff_handler import dump_buff_csv, report_buff_to_queue  # noqa: F401
from .log_handler import async_log_writer, log_queue, report_to_log  # noqa: F401
from .result_handler import (  # noqa: F401
    async_result_writer,
    report_dmg_result,
    result_queue,
)

__result_id: str | None = None
__event_loop = None  # 存储事件循环的引用


if TYPE_CHECKING:
    from zsim.simulator.dataclasses import SimCfg


def regen_result_id(sim_cfg: "SimCfg | None") -> None:
    """
    根据运行模式生成结果ID并处理相关文件。

    如果 `parallel_config` 不为 None（并行模式），则结果ID由 `run_turn_uuid`, `sc_name` 和 `sc_value` 组合而成，
    格式为 "./results/{run_turn_uuid}/{sc_name}_{sc_value}"。
    此模式下会创建对应的结果目录，并将 `parallel_config` 对象序列化为 JSON 文件（parallel_config.json）保存在该目录中。

    如果 `parallel_config` 为 None（普通模式），则从ID缓存文件中读取现有ID，
    找到最大的有效ID，生成一个新的递增ID，并将新ID和时间戳写入缓存文件。
    结果ID格式为 "./results/{current_id}"。

    Args:
        parallel_config: 并行配置对象，或 None。

    Returns:
        None. 全局变量 `__result_id` 会被更新。
    """
    global __result_id

    if sim_cfg is not None:
        # 并行模式：func + 配置列表作为id
        if sim_cfg.func == "attr_curve":
            __result_id = f"./results/{sim_cfg.run_turn_uuid}/{sim_cfg.func}_{sim_cfg.sc_name}_{sim_cfg.sc_value}"
        elif sim_cfg.func == "weapon":
            __result_id = f"./results/{sim_cfg.run_turn_uuid}/{sim_cfg.func}_{sim_cfg.weapon_name}_{sim_cfg.weapon_level}"
        # 创建结果目录
        os.makedirs(__result_id, exist_ok=True)
        # 将 parallel_config 保存为 JSON 文件
        config_path = os.path.join(__result_id, "sub.parallel_config.json")
        try:
            # 尝试将 dataclass 对象转换为字典以便序列化
            config_dict = sim_cfg.model_dump()
            # 更换角色相对位置为角色名
            index = config_dict["adjust_char"]
            from zsim.define import saved_char_config

            config_dict["adjust_char"] = saved_char_config["name_box"][index - 1]
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=4, ensure_ascii=False)
        except TypeError as e:
            # 如果转换或序列化失败，记录错误日志
            raise TypeError(f"无法将 parallel_config 转换为字典: {e}") from e
    else:
        # 普通模式：从文件生成数字 ID
        from zsim.define import NORMAL_MODE_ID_JSON

        cache_path = NORMAL_MODE_ID_JSON

        # 检查缓存文件是否存在，如果不存在则创建
        if not os.path.exists(cache_path):
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump({}, f, indent=4)
        # 读取缓存文件
        with open(cache_path, "r+") as f:
            try:
                id_cache_dict = json.load(f)
            except json.decoder.JSONDecodeError:
                id_cache_dict = {}

            valid_ids = []
            # 筛选出有效的整数ID
            for key in id_cache_dict.keys():
                try:
                    valid_ids.append(int(key))
                except ValueError:
                    continue

            # 确定新的ID
            if valid_ids:
                current_id = max(valid_ids) + 1
            else:
                current_id = 0

            # 将新ID和当前时间戳添加到缓存字典中
            id_cache_dict[str(current_id)] = datetime.now().strftime("%Y-%m-%d_%H%M")

            f.seek(0)
            # 将更新后的缓存字典写回文件
            json.dump(id_cache_dict, f, indent=4)
            # 截断文件到当前写入位置
            f.truncate()
            # 更新全局结果ID
            __result_id = f"./results/{current_id}"


def start_async_tasks():
    """启动异步任务处理日志和结果写入"""
    global __event_loop

    # 如果已有事件循环在运行，则不再创建新的
    if __event_loop is not None:
        return

    # 创建新的事件循环
    __event_loop = asyncio.new_event_loop()

    # 在新线程中运行事件循环
    def run_event_loop():
        asyncio.set_event_loop(__event_loop)
        __event_loop.create_task(async_log_writer(__result_id))
        __event_loop.create_task(async_result_writer(__result_id))
        __event_loop.run_forever()

    loop_thread = threading.Thread(target=run_event_loop, daemon=True)
    loop_thread.start()


def start_report_threads(sim_cfg):
    """用于在开始模拟时启动线程以处理日志和结果写入。"""
    regen_result_id(sim_cfg)
    start_async_tasks()


def stop_report_threads():
    dump_buff_csv(__result_id)
    log_queue.join()
    result_queue.join()

import asyncio
import json
import logging
import os
import threading
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime
from typing import TYPE_CHECKING

from zsim.define import NORMAL_MODE_ID_JSON

from .buff_handler import dump_buff_csv, report_buff_to_queue
from .log_handler import async_log_writer, log_queue, report_to_log
from .result_handler import (
    async_result_writer,
    report_dmg_result,
    result_queue,
)

__all__ = [
    "report_buff_to_queue",
    "report_to_log",
    "report_dmg_result",
    "start_report_threads",
    "stop_report_threads",
]

__result_id: str = "Unknown"
__event_loop: asyncio.AbstractEventLoop | None = None  # 存储事件循环的引用
__loop_thread: threading.Thread | None = None
__writer_tasks: set[asyncio.Task[None]] = set()
__lifecycle_lock = threading.RLock()
__active_report_sessions = 0


if TYPE_CHECKING:
    from zsim.models.session.session_run import ExecAttrCurveCfg, ExecWeaponCfg


def regen_result_id(sim_cfg: "ExecAttrCurveCfg | ExecWeaponCfg | None", *, session_id=None) -> None:
    """
    根据运行模式生成结果ID并处理相关文件。

    如果 `sim_cfg` 不为 None（并行模式），则结果ID由 `run_turn_uuid`, `sc_name` 和 `sc_value` 组合而成，
    格式为 "./results/{run_turn_uuid}/{sc_name}_{sc_value}"。
    此模式下会创建对应的结果目录，并将 `parallel_config` 对象序列化为 JSON 文件（parallel_config.json）保存在该目录中。

    如果 `sim_cfg` 为 None（普通模式），则从ID缓存文件中读取现有ID，
    找到最大的有效ID，生成一个新的递增ID，并将新ID和时间戳写入缓存文件。
    结果ID格式为 "./results/{current_id}"。

    Args:
        sim_cfg: 并行配置对象，或 None。
        session_id: 会话ID，在API启动的普通模式下用作传递本次运行的id。

    Returns:
        None. 全局变量 `__result_id` 会被更新。
    """
    global __result_id

    if sim_cfg is not None:
        # 并行模式：session_id(API模式)/随机生成的uuid(WebUI模式) + 配置列表作为id
        if sim_cfg.func == "attr_curve":
            __result_id = f"./results/{sim_cfg.run_turn_uuid}/{sim_cfg.func}_{sim_cfg.sc_name}_{sim_cfg.sc_value}"  # type: ignore
        elif sim_cfg.func == "weapon":
            __result_id = f"./results/{sim_cfg.run_turn_uuid}/{sim_cfg.func}_{sim_cfg.weapon_name}_{sim_cfg.weapon_level}"  # type: ignore
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
    elif session_id is not None:
        # API启动的普通模式：使用session_id作为id
        cache_path = NORMAL_MODE_ID_JSON
        # 检查缓存文件是否存在，如果不存在则创建
        if not os.path.exists(cache_path):
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump({}, f, indent=4)
        with open(cache_path, "r+", encoding="utf-8") as f:
            id_cache_dict = json.load(f)
            if session_id in id_cache_dict.keys():
                logging.warning(f"session_id {session_id} 已存在，将使用该id")
            else:
                id_cache_dict[session_id] = datetime.now().strftime("%Y-%m-%d_%H%M")
            f.seek(0)
            json.dump(id_cache_dict, f, indent=4)
            f.truncate()
        __result_id = f"./results/{session_id}"
    else:
        # CLI或WebUI启动的普通模式：使用缓存文件中的最大ID+1作为id
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
    global __loop_thread

    with __lifecycle_lock:
        # 在新线程中运行事件循环
        def run_event_loop(ready_event: threading.Event):
            global __event_loop, __writer_tasks

            loop = asyncio.new_event_loop()
            __event_loop = loop
            asyncio.set_event_loop(loop)
            __writer_tasks = {
                loop.create_task(async_log_writer(__result_id)),
                loop.create_task(async_result_writer(__result_id)),
            }
            ready_event.set()
            try:
                loop.run_forever()
            finally:
                pending_tasks = [task for task in __writer_tasks if not task.done()]
                for task in pending_tasks:
                    task.cancel()
                if pending_tasks:
                    loop.run_until_complete(
                        asyncio.gather(*pending_tasks, return_exceptions=True)
                    )
                loop.run_until_complete(loop.shutdown_asyncgens())
                asyncio.set_event_loop(None)
                loop.close()
                __writer_tasks = set()
                if __event_loop is loop:
                    __event_loop = None

        # 如果已有事件循环在运行，则不再创建新的
        if __event_loop is not None and __event_loop.is_running():
            return
        if __loop_thread is not None and __loop_thread.is_alive():
            return

        ready_event = threading.Event()
        __loop_thread = threading.Thread(target=run_event_loop, args=(ready_event,), daemon=True)
        __loop_thread.start()
        ready_event.wait(timeout=1.0)


async def _cancel_writer_tasks() -> None:
    tasks = [task for task in __writer_tasks if not task.done()]
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def _stop_async_tasks(timeout: float = 2.0) -> None:
    global __active_report_sessions, __event_loop, __loop_thread, __writer_tasks

    with __lifecycle_lock:
        __active_report_sessions = 0
        loop = __event_loop
        loop_thread = __loop_thread
        if loop is None:
            if loop_thread is not None and not loop_thread.is_alive():
                __loop_thread = None
            return

        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(_cancel_writer_tasks(), loop)
            try:
                future.result(timeout=timeout)
            except (FutureTimeoutError, RuntimeError):
                pass
            if loop.is_running():
                loop.call_soon_threadsafe(loop.stop)
        elif not loop.is_closed():
            loop.close()

        if loop_thread is not None and loop_thread.is_alive():
            loop_thread.join(timeout=timeout)

        if loop_thread is None or not loop_thread.is_alive():
            __loop_thread = None
        if __event_loop is loop and not loop.is_running():
            __event_loop = None
            __writer_tasks = set()


def start_report_threads(sim_cfg, *, session_id=None):
    """用于在开始模拟时启动线程以处理日志和结果写入。"""
    global __active_report_sessions

    with __lifecycle_lock:
        regen_result_id(sim_cfg, session_id=session_id)
        start_async_tasks()
        __active_report_sessions += 1


def stop_report_threads():
    global __active_report_sessions

    with __lifecycle_lock:
        dump_buff_csv(__result_id)
        log_queue.join()
        result_queue.join()
        if __active_report_sessions > 1:
            __active_report_sessions -= 1
            return
        __active_report_sessions = 0
        _stop_async_tasks()

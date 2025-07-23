import asyncio
import logging
import threading
from concurrent.futures import ProcessPoolExecutor
from typing import TYPE_CHECKING, Any, Iterator

from zsim.api_src.services.database.session_db import get_session_db
from zsim.lib_webui.constants import stats_trans_mapping
from zsim.models.session.session_create import Session
from zsim.models.session.session_result import SessionResult
from zsim.models.session.session_run import (
    CommonCfg,
    ExecAttrCurveCfg,
    ExecWeaponCfg,
    ParallelCfg,
    SessionRun,
)
from zsim.models.session.session_run import (
    SimulationConfig as SimCfg,
)
from zsim.simulator import Simulator

from zsim.simulator.simulator_class import Confirmation

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class SimController:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SimController, cls).__new__(cls)
        return cls._instance

    """
    模拟控制器，负责管理和执行模拟任务。

    该类提供异步队列管理、进程池执行和并行参数生成功能。
    """

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        """初始化模拟控制器"""
        self._executor: ProcessPoolExecutor | None = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running_tasks: set[asyncio.Future[Any]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def executor(self) -> ProcessPoolExecutor:
        """获取进程池执行器，延迟初始化。"""
        with self._lock:
            if self._executor is None:
                self._executor = ProcessPoolExecutor()
        return self._executor

    def __del__(self):
        """析构函数，确保资源清理。"""
        self._shutdown_executor()

    def _shutdown_executor(self):
        """关闭进程池执行器。"""
        if self._executor is not None:
            try:
                self._executor.shutdown(wait=True)
                logger.info("进程池已关闭")
            except Exception as e:
                logger.error(f"关闭进程池时发生错误: {e}")
            finally:
                self._executor = None

    async def put_into_queue(
        self, session_id: str, common_cfg: CommonCfg, sim_cfg: SimCfg | None
    ) -> None:
        """
        将模拟任务放入队列。

        Args:
            common_cfg: 通用配置对象
            sim_cfg: 模拟配置对象，可以为None
        """
        await self._queue.put((session_id, common_cfg, sim_cfg))

    async def get_from_queue(self) -> tuple[str, CommonCfg, SimCfg | None]:
        """
        从队列中获取模拟任务。

        Returns:
            包含通用配置和模拟配置的元组
        """
        return await self._queue.get()

    async def execute_simulation(self) -> None:
        """
        执行模拟任务的主循环。

        从队列中持续获取任务并在进程池中执行，包含错误处理和资源管理。
        """
        event_loop = asyncio.get_event_loop()
        db = await get_session_db()

        while True:
            try:
                session_id, common_cfg, sim_cfg = await self.get_from_queue()
                session = await db.get_session(session_id)
                if not session or not session.session_run:
                    logger.error(f"无法获取会话 {session_id} 或其运行配置")
                    continue

                stop_tick = (
                    sim_cfg.stop_tick
                    if sim_cfg and sim_cfg.stop_tick is not None
                    else session.session_run.stop_tick
                )
                if stop_tick is None:
                    logger.warning(f"会话 {session_id} 未设置 stop_tick，使用默认值 3600")
                    stop_tick = 3600

                def run_simulator(
                    _common_cfg: CommonCfg, _sim_cfg: SimCfg | None, _stop_tick: int
                ) -> "Confirmation":
                    simulator = Simulator()
                    return simulator.api_run_simulator(_common_cfg, _sim_cfg, _stop_tick)

                # 创建模拟器实例并提交任务
                future: asyncio.Future["Confirmation"] = event_loop.run_in_executor(
                    self.executor, run_simulator, common_cfg, sim_cfg, stop_tick
                )
                self._running_tasks.add(future)
                future.add_done_callback(lambda f: self._task_done_callback(f, session_id))
                # 让出控制权给其他协程
                await asyncio.sleep(0)

            except Exception as e:
                logger.error(f"执行模拟任务时发生错误: {e}", exc_info=True)
                await asyncio.sleep(1)  # 错误后短暂延迟

    def _task_done_callback(self, future: asyncio.Future["Confirmation"], session_id: str) -> None:
        """
        任务完成时的回调函数。

        Args:
            future: 完成的Future对象
        """
        self._running_tasks.discard(future)

        asyncio.run_coroutine_threadsafe(
            self._update_session_status(future, session_id), asyncio.get_running_loop()
        )

    async def _update_session_status(
        self, future: asyncio.Future["Confirmation"], session_id: str
    ) -> None:
        db = await get_session_db()
        session = await db.get_session(session_id)
        if not session:
            logger.error(f"会话 {session_id} 未找到，无法更新状态")
            return

        try:
            result = future.result()
            logger.info(f"模拟任务 {session_id} 完成")
            session.status = "completed"

            # 处理模拟结果确认信息
            if isinstance(result, dict) and "run_turn_uuid" in result:
                await self._process_simulation_result(result)
                try:
                    session.session_result = [SessionResult(**result)]
                except Exception as e:
                    logger.error(f"TODO: 模拟任务 {session_id} 结果处理: {repr(e)}", exc_info=True)
        except Exception as e:
            logger.error(f"模拟任务 {session_id} 执行失败: {e}", exc_info=True)
            session.status = "failed"

        await db.update_session(session)

    async def _process_simulation_result(self, confirmation: "Confirmation") -> Any:
        """
        处理模拟结果确认信息的函数stub。

        Args:
            confirmation: 包含运行确认信息的字典
                - run_turn_uuid: 运行轮次的UUID
                - status: 运行状态
                - timestamp: 完成时间戳
                - sim_cfg: 模拟配置（包含并行配置信息）
        """

        logger.info(
            f"开始处理模拟结果: run_turn_uuid={confirmation.run_turn_uuid}, status={confirmation.status}"
        )

        # TODO: 实现结果处理逻辑
        # 1. 根据run_turn_uuid获取对应的会话和任务信息
        # 2. 合并并行运行的结果（如果是并行模式）
        # 3. 更新会话状态和结果数据
        # 4. 触发后续处理流程

        logger.info(f"模拟结果处理完成: run_turn_uuid={confirmation.run_turn_uuid}")

    async def shutdown(self) -> None:
        """优雅关闭控制器，等待所有任务完成并清理资源。"""
        logger.info("开始关闭模拟控制器...")

        # 等待所有运行中的任务完成
        if self._running_tasks:
            logger.info(f"等待 {len(self._running_tasks)} 个任务完成...")
            await asyncio.gather(*list(self._running_tasks), return_exceptions=True)

        # 关闭进程池
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            logger.info("进程池已关闭")

        logger.info("模拟控制器已关闭")

    def generate_parallel_args(
        self,
        session: Session,
        session_run_config: SessionRun,
    ) -> Iterator[SimCfg]:
        """
        生成用于并行模拟的参数。WebUI版本有一个类似方法，但是他们的数据结构并不相同。

        Args:
            session: 会话配置
            session_run_config: 会话运行配置

        Yields:
            SimCfg: 为每个模拟任务生成的参数对象

        Raises:
            ValueError: 当模式不是parallel或func类型未知时
        """
        mode = session_run_config.mode
        session_id = session.session_id

        if mode != "parallel":
            logger.warning(f"会话模式不是parallel，当前模式: {mode}")
            return

        stop_tick = session_run_config.stop_tick
        if stop_tick is None:
            logger.error("并行模式下 stop_tick 不能为空")
            raise ValueError("并行模式下 stop_tick 不能为空")
        parallel_cfg = session_run_config.parallel_config

        if parallel_cfg is None:
            logger.error("并行配置为空")
            raise ValueError("并行配置不能为空")

        # 根据启用的标志确定功能
        func = parallel_cfg.func
        func_cfg = parallel_cfg.func_config

        if func == "attr_curve" and isinstance(func_cfg, ParallelCfg.AttrCurveConfig):
            yield from self._generate_attr_curve_args(func_cfg, parallel_cfg, stop_tick, session_id)
        elif func == "weapon" and isinstance(func_cfg, ParallelCfg.WeaponConfig):
            yield from self._generate_weapon_args(func_cfg, parallel_cfg, stop_tick, session_id)
        else:
            error_msg = f"未知的func类型: {func}, 完整配置: {parallel_cfg}"
            logger.error(error_msg)
            raise ValueError(error_msg)

    @staticmethod
    def _generate_attr_curve_args(
        func_cfg: ParallelCfg.AttrCurveConfig,
        parallel_cfg: ParallelCfg,
        stop_tick: int,
        session_id: str,
    ) -> Iterator[ExecAttrCurveCfg]:
        """
        生成属性曲线参数。

        Args:
            func_cfg: 属性曲线配置
            parallel_cfg: 并行配置
            stop_tick: 停止帧数
            session_id: 会话ID

        Yields:
            ExecAttrCurveCfg: 单个子进程在属性收益曲线模式下的执行配置
        """
        sc_list = func_cfg.sc_list
        sc_range_start, sc_range_end = func_cfg.sc_range
        remove_equip_list = func_cfg.remove_equip_list

        for sc_name in sc_list:
            if sc_name not in stats_trans_mapping:
                logger.warning(f"未知的属性名称: {sc_name}，跳过")
                continue

            for sc_value in range(sc_range_start, sc_range_end + 1):
                args = ExecAttrCurveCfg(
                    stop_tick=stop_tick,
                    mode="parallel",
                    func="attr_curve",
                    adjust_char=parallel_cfg.adjust_char,
                    sc_name=stats_trans_mapping[sc_name],
                    sc_value=sc_value,
                    run_turn_uuid=session_id,
                    remove_equip=sc_name in remove_equip_list,
                )
                yield args

    @staticmethod
    def _generate_weapon_args(
        func_cfg: ParallelCfg.WeaponConfig,
        parallel_cfg: ParallelCfg,
        stop_tick: int,
        session_id: str,
    ) -> Iterator[ExecWeaponCfg]:
        """
        生成武器参数。

        Args:
            func_cfg: 武器配置
            parallel_cfg: 并行配置
            stop_tick: 停止帧数
            session_id: 会话ID

        Yields:
            ExecWeaponCfg: 单个子进程在武器伤害期望模式的执行配置
        """
        weapon_list: list[ParallelCfg.WeaponConfig.SingleWeapon] = func_cfg.weapon_list

        for weapon in weapon_list:
            args = ExecWeaponCfg(
                stop_tick=stop_tick,
                mode="parallel",
                func="weapon",
                adjust_char=parallel_cfg.adjust_char,
                weapon_name=weapon.name,
                weapon_level=weapon.level,
                run_turn_uuid=session_id,
            )
            yield args

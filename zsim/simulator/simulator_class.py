import math
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from zsim.define import config
from zsim.sim_progress.Character.skill_class import Skill
from zsim.sim_progress.Character.wakeup import (
    CharacterResourceThresholds,
    CharacterResourceWakeupSource,
)
from zsim.sim_progress.data_struct import ActionStack, Decibelmanager, ListenerManger, SPUpdateData
from zsim.sim_progress.data_struct.schedule_dispatch import create_schedule_dispatch_port
from zsim.sim_progress.Enemy import Enemy
from zsim.sim_progress.Load import DamageEventJudge, SkillEventSplit
from zsim.sim_progress.Preload import PreloadClass
from zsim.sim_progress.Preload.wakeup import PreloadWakeupSource
from zsim.sim_progress.RandomNumberGenerator import RNG
from zsim.sim_progress.Report import start_report_threads, stop_report_threads
from zsim.sim_progress.ScheduledEvent import ScheduledEvent as ScE
from zsim.sim_progress.ScheduledEvent.buff_runtime import (
    BuffRuntimeFacade,
    BuffRuntimeState,
    BuffTimeRelatedWakeupSource,
)
from zsim.sim_progress.SimulationEngine import (
    FixedTickWakeupSource,
    PlannedEventQueueWakeupSource,
    SimulationClock,
    StopTickWakeupSource,
    WakeupSource,
)
from zsim.simulator.dataclasses import (
    CharacterData,
    GlobalStats,
    InitData,
    LoadData,
    ScheduleData,
    SimCfg,
)

if TYPE_CHECKING:
    from zsim.models.session.session_run import CommonCfg


@dataclass(frozen=True, slots=True)
class EnemyStunWakeupSource:
    enemy: Enemy
    name: str = "enemy-stun"

    def next_wakeup_tick(self, current_tick: int) -> int | None:
        enemy_dynamic = getattr(self.enemy, "dynamic", None)
        if getattr(enemy_dynamic, "stun", False):
            return current_tick + 1
        return None


@dataclass(frozen=True, slots=True)
class LoadMissionWakeupSource:
    load_mission_dict: dict
    name: str = "load-mission"

    def next_wakeup_tick(self, current_tick: int) -> int | None:
        candidates: list[int] = []
        for mission in self.load_mission_dict.values():
            mission_dict = getattr(mission, "mission_dict", None)
            if isinstance(mission_dict, dict):
                for mission_tick in mission_dict:
                    wakeup_tick = math.ceil(float(mission_tick))
                    if wakeup_tick > current_tick:
                        candidates.append(wakeup_tick)
                    elif mission_tick > current_tick - 1:
                        candidates.append(current_tick + 1)
            mission_end_tick = getattr(mission, "mission_end_tick", None)
            if mission_end_tick is not None:
                cleanup_tick = int(mission_end_tick) + 1
                if cleanup_tick > current_tick:
                    candidates.append(cleanup_tick)
        if not candidates:
            return None
        return min(candidates)


@dataclass(frozen=True, slots=True)
class EnemySpecialStateWakeupSource:
    enemy: Enemy
    name: str = "enemy-special-state"

    def next_wakeup_tick(self, current_tick: int) -> int | None:
        manager = getattr(self.enemy, "special_state_manager", None)
        observers = getattr(manager, "observers", None)
        if not isinstance(observers, dict):
            return None
        candidates: list[int] = []
        seen_state_ids: set[int] = set()
        for states in observers.values():
            for state in states:
                state_id = id(state)
                if state_id in seen_state_ids:
                    continue
                seen_state_ids.add(state_id)
                next_wakeup_tick = getattr(state, "next_wakeup_tick", None)
                if not callable(next_wakeup_tick):
                    continue
                tick = next_wakeup_tick(current_tick)
                if tick is not None and tick > current_tick:
                    candidates.append(int(tick))
        return min(candidates) if candidates else None


class Confirmation(BaseModel):
    session_id: str
    status: str
    timestamp: int
    sim_cfg: SimCfg | None = None


class Simulator:
    """模拟器类。

    ## 模拟器的初始状态，包括但不限于：

    ### 常规变量

    - 模拟器时间刻度（tick）每秒为60ticks
    - 暴击种子（crit_seed）为RNG模块使用，未来接入随机功能时用于复现测试
    - 初始化数据（init_data）包含数据库读到的大部分数据
    - 角色数据（char_data）包含角色的实例

    ### 参与tick逻辑的内部对象

    - 加载数据（load_data）
    - 调度数据（schedule_data）
    - 全局统计数据（global_stats）
    - 技能列表（skills）
    - 预加载类（preload）
    - 游戏状态（game_state）包含前面的大多数数据
    - 喧响管理器（decibel_manager）
    - 监听器管理器（listener_manager）

    ### 其他实例

    - 随机数生成器实例（rng_instance）
    - 并行模式标志（in_parallel_mode）
    - 模拟配置，用于控制并行模式下，模拟器作为子进程的参数（sim_cfg）
    """

    tick: int
    crit_seed: int
    init_data: InitData
    enemy: Enemy
    char_data: CharacterData
    load_data: LoadData
    schedule_data: ScheduleData
    global_stats: GlobalStats
    buff_runtime_state: BuffRuntimeState
    skills: list[Skill]
    preload: PreloadClass
    game_state: dict[str, Any]
    decibel_manager: Decibelmanager
    listener_manager: ListenerManger
    rng_instance: RNG
    in_parallel_mode: bool
    sim_cfg: SimCfg | None
    use_indexed_buff_load_loop: bool
    _buff_runtime_rebuild_counts: dict[str, int] | None
    _apl_resource_threshold_cache_key: tuple[Any, ...] | None
    _apl_resource_threshold_cache: dict[int, CharacterResourceThresholds] | None

    def __init__(self, *, use_indexed_buff_load_loop: bool = False) -> None:
        self.use_indexed_buff_load_loop = use_indexed_buff_load_loop
        self._buff_runtime_rebuild_counts = None
        self._apl_resource_threshold_cache_key = None
        self._apl_resource_threshold_cache = None

    def _apply_indexed_buff_load_loop_option(self, use_indexed_buff_load_loop: bool | None) -> None:
        if use_indexed_buff_load_loop is not None:
            self.use_indexed_buff_load_loop = use_indexed_buff_load_loop

    def enable_buff_runtime_rebuild_counting(self) -> None:
        self._buff_runtime_rebuild_counts = {}

    def get_buff_runtime_rebuild_counts(self) -> dict[str, int] | None:
        counts = getattr(self, "_buff_runtime_rebuild_counts", None)
        if counts is None:
            return None
        return dict(counts)

    def _record_buff_runtime_rebuild_count(self, counter_name: str) -> None:
        counts = getattr(self, "_buff_runtime_rebuild_counts", None)
        if counts is None:
            return
        counts[counter_name] = counts.get(counter_name, 0) + 1

    def cli_init_simulator(self, sim_cfg: SimCfg | None):
        """CLI和WebUI的旧方法，重置模拟器实例为初始状态。"""
        self.__detect_parallel_mode(sim_cfg)
        self.init_data = InitData(common_cfg=None, sim_cfg=sim_cfg)
        self.enemy = Enemy(
            index_id=config.enemy.index_id,
            adjustment_id=config.enemy.adjust_id,
            difficulty=config.enemy.difficulty,
            sim_instance=self,
        )
        self.__init_data_struct(sim_cfg)
        start_report_threads(sim_cfg)  # 启动线程以处理日志和结果写入

    def api_init_simulator(self, common_cfg: "CommonCfg", sim_cfg: SimCfg | None):
        """api初始化模拟器实例的接口。"""
        self.__detect_parallel_mode(sim_cfg)
        self.init_data = InitData(common_cfg=common_cfg, sim_cfg=sim_cfg)
        self.enemy = Enemy(
            index_id=common_cfg.enemy_config.index_id,
            adjustment_id=int(common_cfg.enemy_config.adjustment_id),
            difficulty=common_cfg.enemy_config.difficulty,
            sim_instance=self,
        )
        self.__init_data_struct(sim_cfg, api_apl_path=common_cfg.apl_path)
        start_report_threads(
            sim_cfg, session_id=common_cfg.session_id
        )  # 启动线程以处理日志和结果写入

    def api_run_simulator(
        self,
        common_cfg: "CommonCfg",
        sim_cfg: SimCfg | None,
        stop_tick: int | None = None,
        *,
        use_indexed_buff_load_loop: bool | None = None,
        rng_seed: int | None = None,
    ) -> Confirmation:
        """api运行模拟器实例的接口。

        Args:
            common_cfg: 通用配置对象，包含角色和敌人配置
            sim_cfg: 模拟配置对象，包含模拟的详细参数
            stop_tick: 停止模拟的帧数，默认为10800帧（3分钟）
            use_indexed_buff_load_loop: 显式请求索引化 BuffLoadLoop 的开关。
            rng_seed: 可选随机种子；主要供一致性检测使用，普通运行默认不固定随机数。

        Returns:
            包含运行确认信息的字典
        """
        if stop_tick is None:
            stop_tick = 10800
        self._apply_indexed_buff_load_loop_option(use_indexed_buff_load_loop)
        self.api_init_simulator(common_cfg, sim_cfg)
        if rng_seed is not None:
            self.rng_instance.reseed(rng_seed)
        self.main_loop(stop_tick=stop_tick, sim_cfg=sim_cfg, use_api=True)

        # 返回确认信息
        confirmation = Confirmation(
            session_id=common_cfg.session_id,
            status="completed",
            timestamp=int(time.time()),
            sim_cfg=sim_cfg,
        )

        return confirmation

    def __detect_parallel_mode(self, sim_cfg):
        if sim_cfg is not None:
            self.in_parallel_mode = True
            self.sim_cfg = sim_cfg
        else:
            self.in_parallel_mode = False
            self.sim_cfg = None

    def __init_data_struct(self, sim_cfg, *, api_apl_path: str | None = None):
        self.tick = 0
        self.crit_seed = 0
        self.char_data = CharacterData(self.init_data, sim_cfg, sim_instance=self)
        self.load_data = LoadData(
            name_box=self.init_data.name_box,
            Judge_list_set=self.init_data.Judge_list_set,
            weapon_dict=self.init_data.weapon_dict,
            cinema_dict=self.init_data.cinema_dict,
            action_stack=ActionStack(),
            char_obj_dict=self.char_data.char_obj_dict,
            sim_instance=self,
        )
        self.schedule_data = ScheduleData(
            enemy=self.enemy,
            char_obj_list=self.char_data.char_obj_list,
            sim_instance=self,
        )
        if self.schedule_data.enemy.sim_instance is None:
            self.schedule_data.enemy.sim_instance = self
        self.global_stats = GlobalStats(name_box=self.init_data.name_box, sim_instance=self)
        self.buff_runtime_state = BuffRuntimeState(
            template_registry=self.load_data.exist_buff_dict,
            pending_queue=self.load_data.LOADING_BUFF_DICT,
            active_store=self.global_stats.DYNAMIC_BUFF_DICT,
            enemy_mirror=self.schedule_data.enemy.dynamic.dynamic_debuff_list,
        )
        skills = [char.skill_object for char in self.char_data.char_obj_list]
        self.preload = PreloadClass(
            skills,
            load_data=self.load_data,
            apl_path=config.database.apl_file_path if api_apl_path is None else api_apl_path,
            sim_instance=self,
        )
        self.game_state: dict[str, Any] = {
            "tick": self.tick,
            "init_data": self.init_data,
            "char_data": self.char_data,
            "load_data": self.load_data,
            "schedule_data": self.schedule_data,
            "global_stats": self.global_stats,
            "buff_runtime_state": self.buff_runtime_state,
            "preload": self.preload,
        }
        self.decibel_manager = Decibelmanager(self)
        self.listener_manager = ListenerManger(self)
        self.rng_instance = RNG(sim_instance=self)
        # 监听器的初始化需要整个Simulator实例，因此在这里进行初始化
        self.load_data.buff_0_manager.initialize_buff_listener()

    def _create_buff_runtime_facade(self) -> BuffRuntimeFacade:
        self._record_buff_runtime_rebuild_count("default_buff_runtime_facade")
        return self.buff_runtime_state.create_facade()

    def _main_loop_wakeup_sources(
        self,
        stop_tick: int | None,
        *,
        buff_runtime: BuffRuntimeFacade | None = None,
    ) -> list[WakeupSource]:
        sources: list[WakeupSource] = [
            PlannedEventQueueWakeupSource(self.schedule_data.planned_event_queue),
            LoadMissionWakeupSource(self.load_data.load_mission_dict),
            PreloadWakeupSource(self.preload),
            CharacterResourceWakeupSource(
                self.char_data.char_obj_list,
                thresholds_by_cid=self._apl_resource_thresholds_by_cid(),
            ),
            EnemyStunWakeupSource(self.schedule_data.enemy),
            EnemySpecialStateWakeupSource(self.schedule_data.enemy),
        ]
        if buff_runtime is not None:
            sources.append(
                BuffTimeRelatedWakeupSource(
                    runtime_facade=buff_runtime,
                    enemy=self.schedule_data.enemy,
                )
            )
        if getattr(self.schedule_data, "processed_state_this_tick", False):
            sources.append(
                FixedTickWakeupSource(
                    name="processed-event-followup",
                    tick=self.tick + 1,
                )
            )
        if stop_tick is not None:
            sources.append(StopTickWakeupSource(stop_tick))
        return sources

    def _apl_resource_thresholds_by_cid(self) -> dict[int, CharacterResourceThresholds]:
        snapshot = self._apl_resource_threshold_inventory_snapshot()
        if snapshot is None:
            self._apl_resource_threshold_cache_key = None
            self._apl_resource_threshold_cache = None
            return {}

        apl_unit_inventory, cache_key = snapshot
        if (
            getattr(self, "_apl_resource_threshold_cache_key", None) == cache_key
            and getattr(self, "_apl_resource_threshold_cache", None) is not None
        ):
            return self._apl_resource_threshold_cache or {}

        thresholds = self._scan_apl_resource_thresholds_by_cid(apl_unit_inventory)
        self._apl_resource_threshold_cache_key = cache_key
        self._apl_resource_threshold_cache = thresholds
        return thresholds

    def _apl_resource_threshold_inventory_snapshot(
        self,
    ) -> tuple[object, tuple[Any, ...]] | None:
        try:
            apl = self.preload.strategy.apl_engine.apl
            apl_operator = apl.apl_operator
            if apl_operator is None:
                apl_operator = getattr(apl, "operator", None)
            apl_unit_inventory = apl_operator.apl_unit_inventory
        except AttributeError:
            return None

        if apl_operator is None or apl_unit_inventory is None:
            return None
        inventory_items = getattr(apl_unit_inventory, "items", None)
        if not callable(inventory_items):
            return None

        unit_fingerprint: list[tuple[Any, ...]] = []
        for key, apl_unit in inventory_items():
            sub_conditions = getattr(apl_unit, "sub_conditions_unit_list", ())
            builtin_conditions = getattr(apl_unit, "builtin_percond_list", ())
            unit_fingerprint.append(
                (
                    key,
                    id(apl_unit),
                    id(sub_conditions),
                    self._safe_len(sub_conditions),
                    id(builtin_conditions),
                    self._safe_len(builtin_conditions),
                )
            )
        cache_key = (
            id(apl_operator),
            id(apl_unit_inventory),
            len(unit_fingerprint),
            tuple(unit_fingerprint),
        )
        return apl_unit_inventory, cache_key

    @staticmethod
    def _safe_len(value: object) -> int | None:
        try:
            return len(value)  # type: ignore[arg-type]
        except TypeError:
            return None

    @staticmethod
    def _scan_apl_resource_thresholds_by_cid(
        apl_unit_inventory: object,
    ) -> dict[int, CharacterResourceThresholds]:
        inventory_values = getattr(apl_unit_inventory, "values", None)
        if not callable(inventory_values):
            return {}
        thresholds: dict[int, dict[str, set[float]]] = {}
        for apl_unit in inventory_values():
            condition_units = list(getattr(apl_unit, "sub_conditions_unit_list", ()))
            condition_units.extend(getattr(apl_unit, "builtin_percond_list", ()))
            for condition in condition_units:
                stat = getattr(condition, "check_stat", None)
                if stat not in {"energy", "special_resource", "adrenaline", "decibel"}:
                    continue
                try:
                    cid = int(getattr(condition, "check_target"))
                    value = float(getattr(condition, "check_value"))
                except (TypeError, ValueError):
                    continue
                by_stat = thresholds.setdefault(
                    cid,
                    {
                        "energy": set(),
                        "special_resource": set(),
                        "adrenaline": set(),
                        "decibel": set(),
                    },
                )
                by_stat[stat].add(value)

        return {
            cid: CharacterResourceThresholds(
                energy=tuple(sorted(by_stat["energy"])),
                special_resource=tuple(sorted(by_stat["special_resource"])),
                adrenaline=tuple(sorted(by_stat["adrenaline"])),
                decibel=tuple(sorted(by_stat["decibel"])),
            )
            for cid, by_stat in thresholds.items()
        }

    def _settle_skipped_time_derived_state(self, *, elapsed_ticks: int) -> None:
        if elapsed_ticks <= 0:
            return
        previous_elapsed_ticks = getattr(self, "_event_driven_elapsed_ticks", 1)
        previous_skipped_refresh = getattr(self, "_event_driven_skipped_refresh", False)
        self._event_driven_elapsed_ticks = elapsed_ticks
        self._event_driven_skipped_refresh = True
        buff_runtime_view = self.buff_runtime_state.create_read_port()
        for char in self.char_data.char_obj_list:
            sp_update_data = SPUpdateData(
                char_obj=char,
                runtime_view=buff_runtime_view,
                sim_instance=self,
            )
            char.update_sp_and_decibel(sp_update_data)
            if hasattr(char, "refresh_myself"):
                char.refresh_myself()
        self._event_driven_elapsed_ticks = previous_elapsed_ticks
        self._event_driven_skipped_refresh = previous_skipped_refresh

    def _settle_current_tick_time_derived_state(self) -> None:
        previous_elapsed_ticks = getattr(self, "_event_driven_elapsed_ticks", 1)
        previous_skipped_refresh = getattr(self, "_event_driven_skipped_refresh", False)
        self._event_driven_elapsed_ticks = 1
        self._event_driven_skipped_refresh = False
        buff_runtime_view = self.buff_runtime_state.create_read_port()
        for char in self.char_data.char_obj_list:
            sp_update_data = SPUpdateData(
                char_obj=char,
                runtime_view=buff_runtime_view,
                sim_instance=self,
            )
            char.update_sp_and_decibel(sp_update_data)
            if hasattr(char, "refresh_myself"):
                char.refresh_myself()
        self._event_driven_elapsed_ticks = previous_elapsed_ticks
        self._event_driven_skipped_refresh = previous_skipped_refresh

    def _next_main_loop_wakeup(
        self,
        *,
        current_tick: int,
        stop_tick: int | None,
        buff_runtime: BuffRuntimeFacade,
        simulation_clock: SimulationClock,
    ) -> tuple[int, tuple[str, ...]]:
        wakeup_sources = self._main_loop_wakeup_sources(
            stop_tick,
            buff_runtime=buff_runtime,
        )
        next_tick = simulation_clock.next_wakeup_tick(
            current_tick=current_tick,
            wakeup_sources=wakeup_sources,
        )
        due_sources = tuple(
            source.name
            for source in wakeup_sources
            if source.next_wakeup_tick(current_tick) == next_tick
        )
        return next_tick, due_sources

    @staticmethod
    def _requires_behavior_pipeline(due_source_names: tuple[str, ...]) -> bool:
        behavior_sources = {
            "initial",
            "planned-event-queue",
            "load-mission",
            "preload-action",
            "character-resource",
            "enemy-stun",
            "enemy-special-state",
        }
        return any(source_name in behavior_sources for source_name in due_source_names)

    def main_loop(
        self,
        stop_tick: int = 10800,
        *,
        sim_cfg: SimCfg | None = None,
        use_api: bool = False,
        use_indexed_buff_load_loop: bool | None = None,
    ):
        """
        CLI和WebUI使用此方法直接从文件读取数据，运行模拟器。
        传入的值仅为stop_tick和并行模拟配置。
        """
        self._apply_indexed_buff_load_loop_option(use_indexed_buff_load_loop)
        if not use_api:
            self.cli_init_simulator(sim_cfg)
        buff_runtime = self._create_buff_runtime_facade()
        simulation_clock = SimulationClock()
        last_processed_tick: int | None = None
        while True:
            skipped_elapsed_ticks = (
                0 if last_processed_tick is None else max(self.tick - last_processed_tick - 1, 0)
            )
            self._settle_skipped_time_derived_state(
                elapsed_ticks=skipped_elapsed_ticks,
            )
            self._event_driven_elapsed_ticks = 1
            # tick 更新
            # report_to_log(f"[更新] tick 推进到 {tick}")
            buff_runtime.update_time_related_effects(
                tick=self.tick,
                enemy=self.schedule_data.enemy,
            )

            # Preload 阶段
            self.preload.do_preload(
                self.tick,
                self.schedule_data.enemy,
                self.init_data.name_box,
                self.char_data,
            )
            preload_list = self.preload.preload_data.preload_action

            if stop_tick is None:
                if (
                    not config.apl_mode.enabled
                    and self.preload.preload_data.skills_queue.head is None
                ):
                    # 旧 Sequence 模式的兜底逻辑；当前不再兼容 APL 模式。
                    stop_tick = self.tick + 120
            elif self.tick >= stop_tick:
                break

            # Load 阶段
            if preload_list:
                SkillEventSplit(
                    preload_list,
                    self.load_data.load_mission_dict,
                    self.load_data.name_dict,
                    self.tick,
                    self.load_data.action_stack,
                )
            DamageEventJudge(
                self.tick,
                self.load_data.load_mission_dict,
                self.schedule_data.enemy,
                create_schedule_dispatch_port(schedule_data=self.schedule_data),
                self.char_data.char_obj_list,
            )
            buff_runtime.load_pending_buffs(
                time_now=self.tick,
                load_mission_dict=self.load_data.load_mission_dict,
                character_name_box=self.init_data.name_box,
                all_name_order_box=self.load_data.all_name_order_box,
                sim_instance=self,
            )
            buff_runtime.activate_pending_buffs(timenow=self.tick)

            # Load.DamageEventJudge 通过 ScheduleDispatchPort 发布计划伤害事件。
            # 计划事件处理
            sce = ScE.from_runtime_state(
                schedule_data=self.schedule_data,
                tick=self.tick,
                action_stack=self.load_data.action_stack,
                buff_runtime_state=self.buff_runtime_state,
                sim_instance=self,
            )
            sce.event_start()
            # self.tick += 1
            # if sce.data.processed_times > 0:
            # print(f"\r{self.tick}", end="")
            if self.schedule_data.processed_state_this_tick and self.tick != 0:
                minutes = self.tick // 3600
                rest_seconds = self.tick % 3600 / 60
                if rest_seconds == 60:
                    rest_seconds = 0
                    minutes += 1
                print()
                print(
                    f"▲ ▲ ▲第{self.tick}帧({minutes:.0f}分 {rest_seconds:02.0f}秒)发生的事件如上▲ ▲ ▲\n ",
                    end="",
                )
                print("---------------------------------------------")
            last_processed_tick = self.tick
            self.tick = simulation_clock.next_wakeup_tick(
                current_tick=self.tick,
                wakeup_sources=self._main_loop_wakeup_sources(
                    stop_tick,
                    buff_runtime=buff_runtime,
                ),
            )
            self.schedule_data.reset_processed_event()
        stop_report_threads()

    def __deepcopy__(self, memo):
        return self

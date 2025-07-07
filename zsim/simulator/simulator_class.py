import gc
from typing import TYPE_CHECKING, Any

from zsim.define import (
    APL_MODE,
    APL_PATH,
    ENEMY_ADJUST_ID,
    ENEMY_DIFFICULTY,
    ENEMY_INDEX_ID,
)
from zsim.sim_progress.Buff import (
    BuffLoadLoop,
    buff_add,
)
from zsim.sim_progress.Character.skill_class import Skill
from zsim.sim_progress.data_struct import ActionStack, Decibelmanager, ListenerManger
from zsim.sim_progress.Enemy import Enemy
from zsim.sim_progress.Load import DamageEventJudge, SkillEventSplit
from zsim.sim_progress.Preload import PreloadClass
from zsim.sim_progress.RandomNumberGenerator import RNG
from zsim.sim_progress.Report import start_report_threads, stop_report_threads
from zsim.sim_progress.ScheduledEvent import ScheduledEvent as ScE
from zsim.sim_progress.Update.Update_Buff import update_dynamic_bufflist
from zsim.simulator.dataclasses import (
    CharacterData,
    GlobalStats,
    InitData,
    LoadData,
    ScheduleData,
)

if TYPE_CHECKING:
    from zsim.simulator.dataclasses import SimCfg


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

    Args:
        sim_cfg (SimCfg | None): 模拟配置对象，包含模拟的详细参数。
    """

    tick: int
    crit_seed: int
    init_data: InitData
    char_data: CharacterData
    load_data: LoadData
    schedule_data: ScheduleData
    global_stats: GlobalStats
    skills: list[Skill]
    preload: PreloadClass
    game_state: dict[str, Any]
    decibel_manager: Decibelmanager
    listener_manager: ListenerManger
    rng_instance: RNG
    in_parallel_mode: bool
    sim_cfg: "SimCfg | None"

    def reset_simulator(self, sim_cfg: "SimCfg | None"):
        """重置模拟器实例为初始状态。"""
        self.reset_sim_data(sim_cfg)  # 重置所有全局变量
        start_report_threads(sim_cfg)  # 启动线程以处理日志和结果写入

    def reset_sim_data(self, sim_cfg: "SimCfg | None"):
        """重置所有全局变量为初始状态。"""
        if sim_cfg is not None:
            self.in_parallel_mode = True
            self.sim_cfg = sim_cfg
        else:
            self.in_parallel_mode = False
            self.sim_cfg = None
        self.tick = 0
        self.crit_seed = 0
        self.init_data = InitData(sim_cfg)

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
            enemy=Enemy(
                index_ID=ENEMY_INDEX_ID,
                adjust_ID=ENEMY_ADJUST_ID,
                difficulty=ENEMY_DIFFICULTY,
                sim_instance=self,
            ),
            char_obj_list=self.char_data.char_obj_list,
            sim_instance=self,
        )
        if self.schedule_data.enemy.sim_instance is None:
            self.schedule_data.enemy.sim_instance = self

        self.global_stats = GlobalStats(
            name_box=self.init_data.name_box, sim_instance=self
        )
        skills = [char.skill_object for char in self.char_data.char_obj_list]
        self.preload = PreloadClass(
            skills, load_data=self.load_data, apl_path=APL_PATH, sim_instance=self
        )

        self.game_state = {  # noqa: F841
            "tick": self.tick,
            "init_data": self.init_data,
            "char_data": self.char_data,
            "load_data": self.load_data,
            "schedule_data": self.schedule_data,
            "global_stats": self.global_stats,
            "preload": self.preload,
        }
        self.decibel_manager = Decibelmanager(self)
        self.listener_manager = ListenerManger(self)
        self.rng_instance = RNG(sim_instance=self)

        # 监听器的初始化需要整个Simulator实例，因此在这里进行初始化
        self.load_data.buff_0_manager.initialize_buff_listener()

    def main_loop(self, stop_tick: int = 10800, *, sim_cfg: "SimCfg | None" = None):
        self.reset_simulator(sim_cfg)
        while True:
            # Tick Update
            # report_to_log(f"[Update] Tick step to {tick}")
            update_dynamic_bufflist(
                self.global_stats.DYNAMIC_BUFF_DICT,
                self.tick,
                self.load_data.exist_buff_dict,
                self.schedule_data.enemy,
            )

            # Preload
            self.preload.do_preload(
                self.tick,
                self.schedule_data.enemy,
                self.init_data.name_box,
                self.char_data,
            )
            preload_list = self.preload.preload_data.preload_action

            if stop_tick is None:
                if (
                    not APL_MODE and self.preload.preload_data.skills_queue.head is None
                ):  # Old Sequence mode left, not compatible with APL mode now
                    stop_tick = self.tick + 120
            elif self.tick >= stop_tick:
                break

            # Load
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
                self.schedule_data.event_list,
                self.char_data.char_obj_list,
                dynamic_buff_dict=self.global_stats.DYNAMIC_BUFF_DICT,
            )
            BuffLoadLoop(
                self.tick,
                self.load_data.load_mission_dict,
                self.load_data.exist_buff_dict,
                self.init_data.name_box,
                self.load_data.LOADING_BUFF_DICT,
                self.load_data.all_name_order_box,
                sim_instance=self,
            )
            buff_add(
                self.tick,
                self.load_data.LOADING_BUFF_DICT,
                self.global_stats.DYNAMIC_BUFF_DICT,
                self.schedule_data.enemy,
            )
            # Load.DamageEventJudge(tick, load_data.load_mission_dict, schedule_data.enemy, schedule_data.event_list, char_data.char_obj_list)
            # ScheduledEvent
            sce = ScE(
                self.global_stats.DYNAMIC_BUFF_DICT,
                self.schedule_data,
                self.tick,
                self.load_data.exist_buff_dict,
                self.load_data.action_stack,
                sim_instance=self,
            )
            sce.event_start()
            # self.tick += 1
            # if sce.data.processed_times > 0:
            if self.schedule_data.processed_state_this_tick:
                # print(sce.data.processed_times, "events processed", end="")
                minutes = self.tick // 3600
                rest_seconds = self.tick % 3600 / 60
                # seconds = self.tick / 60
                # frames = self.tick % 60
                # print(f"\r{seconds} 秒 {frames:02d} 帧 ", end="")
                print(f"\r▶{self.tick} 帧 （{minutes:.0f}分 {rest_seconds:02.0f}秒）◀\n ", end="")
            self.tick += 1
            if self.tick % 500 == 0 and self.tick != 0:
                gc.collect()
        stop_report_threads()

    def __deepcopy__(self, memo):
        return self

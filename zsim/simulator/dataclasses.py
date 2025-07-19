from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from zsim.define import saved_char_config
from zsim.sim_progress import Buff
from zsim.sim_progress.Buff.Buff0Manager import Buff0ManagerClass, change_name_box
from zsim.sim_progress.Character import Character, character_factory
from zsim.sim_progress.data_struct import ActionStack
from zsim.sim_progress.Enemy import Enemy
from zsim.models.session.session_run import CommonCfg, CharConfig
from .config_classes import SimulationConfig as SimCfg


if TYPE_CHECKING:
    from .simulator_class import Simulator


@dataclass
class InitData:
    def __init__(
        self,
        *,
        common_cfg: CommonCfg | None = None,
        sim_cfg: SimCfg | None = None,
        sim_instance: "Simulator | None" = None,
    ):
        """
        初始化角色配置数据。

        - CLI或WebUI模式下从配置文件中加载角色配置信息
        - API模式下，通过传入的配置信息初始化角色配置
          并初始化相关数据结构。
          如果配置文件/配置信息不存在或配置信息不完整，将抛出异常。
        """
        self.sim_cfg = sim_cfg
        if common_cfg is None:
            self.__direct_read_init()
        elif isinstance(common_cfg, CommonCfg):
            self.__api_init(common_cfg)
        else:
            raise ValueError("Invalid configuration type.")
        self.sim_instance = sim_instance

    def __direct_read_init(self):
        """CLI/WebUI方法不传入常规配置，直接读取文件"""
        config: dict = saved_char_config
        if not config:
            assert False, "No character init configuration found."
        try:
            self.name_box: list[str] = config["name_box"]
            self.Judge_list_set: list[
                list[str | None]
            ] = []  # [[角色名, 武器名, 四件套, 二件套], ...]
            self.char_0 = config[self.name_box[0]]
            self.char_1 = config[self.name_box[1]]
            self.char_2 = config[self.name_box[2]]
        except KeyError as e:
            assert False, f"Missing key in character init configuration: {e}"
        self.__adjust_weapon_with_sim_cfg()
        for name in self.name_box:
            char = getattr(self, f"char_{self.name_box.index(name)}")
            self.Judge_list_set.append(
                [
                    name,
                    char["weapon"],
                    char.get("equip_set4", ""),
                    char.get("equip_set2_a", ""),
                ]
            )
        self.weapon_dict: dict[str, list[str | Literal[1, 2, 3, 4, 5] | None]] = {
            name: [
                getattr(self, f"char_{self.name_box.index(name)}")["weapon"],
                getattr(self, f"char_{self.name_box.index(name)}")["weapon_level"],
            ]
            for name in self.name_box
        }  # {角色名: [武器名, 武器精炼等级], ...}
        self.cinema_dict = {
            name: getattr(self, f"char_{self.name_box.index(name)}")["cinema"]
            for name in self.name_box
        }  # {角色名: 影画等级, ...}

    def __api_init(self, common_cfg: CommonCfg):
        """API方法传入常规配置"""
        self.name_box: list[str] = [char.name for char in common_cfg.char_config]
        assert len(self.name_box) == 3, "Character configuration must be 3."

        # 创建 char_0, char_1, char_2 属性，将 CharConfig 对象转换为字典
        for i, char_config in enumerate(common_cfg.char_config):
            char_dict = char_config.model_dump()
            setattr(self, f"char_{i}", char_dict)

        self.Judge_list_set: list[list[str | None]] = [
            [char.name, char.weapon, char.equip_set4, char.equip_set2_a]
            for char in common_cfg.char_config
        ]
        self.weapon_dict: dict[str, list[str | Literal[1, 2, 3, 4, 5] | None]] = {
            char.name: [char.weapon, char.weapon_level] for char in common_cfg.char_config
        }
        self.cinema_dict: dict[str, Literal[0, 1, 2, 3, 4, 5, 6]] = {
            char.name: char.cinema for char in common_cfg.char_config
        }
        self.__adjust_weapon_with_sim_cfg()

    def __adjust_weapon_with_sim_cfg(self):
        # 根据sim_cfg调整武器配置
        if self.sim_cfg is not None and self.sim_cfg.func == "weapon":
            adjust_char_index = (
                self.sim_cfg.adjust_char - 1
            )  # UI从1开始计数，这里需要转换为0开始的索引
            if 0 <= adjust_char_index < len(self.name_box):
                char_dict_to_adjust = getattr(self, f"char_{adjust_char_index}")

                # 更新武器名称和精炼等级
                char_dict_to_adjust["weapon"] = self.sim_cfg.weapon_name
                char_dict_to_adjust["weapon_level"] = self.sim_cfg.weapon_level


@dataclass
class CharacterData:
    char_obj_list: list[Character] = field(init=False)
    init_data: InitData
    sim_cfg: SimCfg | None
    sim_instance: "Simulator"

    def __post_init__(self):
        self.char_obj_list = []
        if self.init_data.name_box:
            i = 0
            for _ in self.init_data.name_box:
                char_dict = getattr(self.init_data, f"char_{i}")
                # 提取sim_cfg参数
                sim_cfg = None
                if self.sim_cfg is not None and self.sim_cfg.adjust_char == i + 1:
                    # UI那边不是从0开始数数的
                    sim_cfg = self.sim_cfg
                # 创建CharConfig对象
                char_config = CharConfig(**char_dict)
                char_obj: Character = character_factory(char_config, sim_cfg=sim_cfg)
                if char_obj.sim_instance is None:
                    char_obj.sim_instance = self.sim_instance
                self.char_obj_list.append(char_obj)
                i += 1
        self.char_obj_dict = {char_obj.NAME: char_obj for char_obj in self.char_obj_list}

    def find_next_char_obj(self, char_now: int, direction: int = 1) -> Character:
        """输入查找起点（CID），以及查找方向，返回下一位角色"""
        __index = 0
        for char_obj in self.char_obj_list:
            __index += 1
            if char_now != char_obj.CID:
                continue
            if direction == 1:
                """顺向查找"""
                if __index + 1 == len(self.char_obj_list):
                    return self.char_obj_list[0]
                else:
                    return self.char_obj_list[__index]
            elif direction == -1:
                """逆向查找"""
                if __index == 0:
                    return self.char_obj_list[-1]
                else:
                    return self.char_obj_list[__index - 1]
            else:
                raise ValueError("direction参数错误！")
        else:
            raise ValueError("未找到CID为%d的角色！" % char_now)

    def find_next_char_obj(self, char_now: int, direction: int = 1) -> Character:
        """输入查找起点（CID），以及查找方向，返回下一位角色"""
        __index = 0
        for char_obj in self.char_obj_list:
            __index += 1
            if char_now != char_obj.CID:
                continue
            if direction == 1:
                """顺向查找"""
                if __index + 1 == len(self.char_obj_list):
                    return self.char_obj_list[0]
                else:
                    return self.char_obj_list[__index]
            elif direction == -1:
                """逆向查找"""
                if __index == 0:
                    return self.char_obj_list[-1]
                else:
                    return self.char_obj_list[__index - 1]
            else:
                raise ValueError("direction参数错误！")
        else:
            raise ValueError("未找到CID为%d的角色！" % char_now)

    def reset_myself(self):
        for obj in self.char_obj_list:
            obj.reset_myself()

    def find_char_obj(self, CID: int = None, char_name: str = None) -> Character | None:
        if not CID and not char_name:
            raise ValueError("查找角色时，必须提供CID或是char_name中的一个！")
        for char_obj in self.char_obj_list:
            if CID == char_obj.CID or char_name == char_obj.NAME:
                return char_obj
        else:
            if CID:
                raise ValueError(f"未找到CID为{CID}的角色！")
            elif char_name:
                raise ValueError(f"未找到名称为{char_name}的角色！")


@dataclass
class LoadData:
    name_box: list
    Judge_list_set: list
    weapon_dict: dict
    action_stack: ActionStack
    cinema_dict: dict
    exist_buff_dict: dict = field(init=False)
    load_mission_dict: dict = field(default_factory=dict)
    LOADING_BUFF_DICT: dict = field(default_factory=dict)
    name_dict: dict = field(default_factory=dict)
    all_name_order_box: dict = field(default_factory=dict)
    preload_tick_stamp: dict = field(default_factory=dict)
    char_obj_dict: dict | None = None
    sim_instance: "Simulator" = None

    def __post_init__(self):
        self.buff_0_manager = Buff0ManagerClass.Buff0Manager(
            self.name_box,
            self.Judge_list_set,
            self.weapon_dict,
            self.cinema_dict,
            self.char_obj_dict,
            sim_instance=self.sim_instance,
        )
        self.exist_buff_dict = self.buff_0_manager.exist_buff_dict
        self.all_name_order_box = change_name_box(self.name_box)
        # self.all_name_order_box = Buff.Buff0Manager.change_name_box()

    def reset_exist_buff_dict(self):
        """重置buff_exist_dict"""
        for char_name, sub_exist_buff_dict in self.exist_buff_dict.items():
            for buff_name, buff in sub_exist_buff_dict.items():
                buff.reset_myself()

    def reset_myself(self, name_box, Judge_list_set, weapon_dict, cinema_dict):
        self.name_box = name_box
        self.Judge_list_set = Judge_list_set
        self.weapon_dict = weapon_dict
        self.cinema_dict = cinema_dict
        self.action_stack.reset_myself()
        self.reset_exist_buff_dict()
        self.load_mission_dict = {}
        self.LOADING_BUFF_DICT = {}
        self.name_dict = {}
        self.all_name_order_box = change_name_box(self.name_box)
        self.preload_tick_stamp = {}


@dataclass
class ScheduleData:
    enemy: Enemy
    char_obj_list: list[Character]
    event_list: list = field(default_factory=list)
    # judge_required_info_dict = {"skill_node": None}
    loading_buff: dict[str, list[Buff.Buff]] = field(default_factory=dict)
    dynamic_buff: dict[str, list[Buff.Buff]] = field(default_factory=dict)
    sim_instance: "Simulator" = None
    processed_event: bool = False
    # 记录已处理的事件次数, 给外部判断是否有事件发生, 便于前端跳过没有 event 的帧的 log
    # 实际执行时, 当 event 是 Preload.SkillNode | LoadingMission 时, 大多数情况是没有 log 输出的, 所以仍然会输出大量空帧.
    # 10800 帧的情况目前可以只打印 1500 条左右的 log. 但是打印的帧数字不规律, 可能看起来有点怪.
    processed_times: int = field(default=0)
    processe_state_update_tick: int = field(default=0)      # process_state的更新时间

    def reset_myself(self):
        """重置ScheduleData的动态数据！"""
        self.enemy.reset_myself()
        self.event_list = []
        # self.judge_required_info_dict = {"skill_node": None}
        for char_name in self.loading_buff:
            self.loading_buff[char_name] = []
            self.dynamic_buff[char_name] = []
        self.processed_times = 0

    @property
    def processed_state_this_tick(self):
        """当前tick是否有新事件发生"""
        return self.processed_event

    def change_process_state(self):
        """有新事件发生时调用，保证终端print"""
        self.processed_event = True

    def reset_processed_event(self):
        """重置processed_event"""
        self.processed_event = False


@dataclass
class GlobalStats:
    name_box: list
    DYNAMIC_BUFF_DICT: dict[str, list[Buff.Buff]] = field(default_factory=dict)
    sim_instance: "Simulator" = None

    def __post_init__(self):
        for name in self.name_box + ["enemy"]:
            self.DYNAMIC_BUFF_DICT[name] = []

    def reset_myself(self, name_box):
        for name in self.name_box + ["enemy"]:
            self.DYNAMIC_BUFF_DICT[name] = []
